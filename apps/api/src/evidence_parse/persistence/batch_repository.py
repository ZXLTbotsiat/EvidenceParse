from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from evidence_parse.models import BatchItemStatus, BatchStatus
from evidence_parse.persistence.tables import BatchItemRow, BatchJobRow, utc_now


class BatchNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class BatchItemSeed:
    item_id: str
    position: int
    filename: str
    content_type: str


@dataclass(frozen=True)
class BatchItemRecord:
    item_id: str
    position: int
    filename: str
    content_type: str
    status: BatchItemStatus
    document_id: Optional[str]
    error: Optional[str]


@dataclass(frozen=True)
class BatchJobRecord:
    batch_id: str
    schema_name: str
    status: BatchStatus
    total_items: int
    completed_items: int
    failed_items: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    items: List[BatchItemRecord]


class BatchRepository:
    """Persist batch lifecycle separately from document extraction concerns."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(
        self,
        batch_id: str,
        schema_name: str,
        items: Sequence[BatchItemSeed],
    ) -> BatchJobRecord:
        with Session(self.engine) as session, session.begin():
            session.add(
                BatchJobRow(
                    id=batch_id,
                    schema_name=schema_name,
                    status=BatchStatus.QUEUED.value,
                    items=[
                        BatchItemRow(
                            id=item.item_id,
                            position=item.position,
                            filename=item.filename,
                            content_type=item.content_type,
                            status=BatchItemStatus.PENDING.value,
                        )
                        for item in items
                    ],
                )
            )
        return self.get(batch_id)

    def get(self, batch_id: str) -> BatchJobRecord:
        with Session(self.engine) as session:
            row = session.scalar(
                select(BatchJobRow)
                .options(selectinload(BatchJobRow.items))
                .where(BatchJobRow.id == batch_id)
            )
            if row is None:
                raise BatchNotFoundError(batch_id)
            return self._to_record(row)

    def mark_running(self, batch_id: str) -> None:
        self._update_job(
            batch_id,
            status=BatchStatus.RUNNING.value,
            started_at=utc_now(),
        )

    def mark_item_processing(self, batch_id: str, item_id: str) -> None:
        self._update_item(batch_id, item_id, status=BatchItemStatus.PROCESSING.value)

    def mark_item_completed(self, batch_id: str, item_id: str, document_id: str) -> None:
        self._update_item(
            batch_id,
            item_id,
            status=BatchItemStatus.COMPLETED.value,
            document_id=document_id,
            error=None,
        )

    def mark_item_failed(self, batch_id: str, item_id: str, error: str) -> None:
        self._update_item(
            batch_id,
            item_id,
            status=BatchItemStatus.FAILED.value,
            error=error,
        )

    def finish(self, batch_id: str) -> BatchJobRecord:
        with Session(self.engine) as session, session.begin():
            counts = dict(
                session.execute(
                    select(BatchItemRow.status, func.count())
                    .where(BatchItemRow.batch_id == batch_id)
                    .group_by(BatchItemRow.status)
                ).all()
            )
            completed = counts.get(BatchItemStatus.COMPLETED.value, 0)
            failed = counts.get(BatchItemStatus.FAILED.value, 0)
            if completed and failed:
                final_status = BatchStatus.PARTIAL_FAILURE
            elif failed:
                final_status = BatchStatus.FAILED
            else:
                final_status = BatchStatus.COMPLETED
            update_result = session.execute(
                update(BatchJobRow)
                .where(BatchJobRow.id == batch_id)
                .values(status=final_status.value, completed_at=utc_now())
            )
            if update_result.rowcount != 1:
                raise BatchNotFoundError(batch_id)
        return self.get(batch_id)

    def _update_job(self, batch_id: str, **values: object) -> None:
        with Session(self.engine) as session, session.begin():
            update_result = session.execute(
                update(BatchJobRow).where(BatchJobRow.id == batch_id).values(**values)
            )
            if update_result.rowcount != 1:
                raise BatchNotFoundError(batch_id)

    def _update_item(self, batch_id: str, item_id: str, **values: object) -> None:
        with Session(self.engine) as session, session.begin():
            update_result = session.execute(
                update(BatchItemRow)
                .where(BatchItemRow.batch_id == batch_id, BatchItemRow.id == item_id)
                .values(**values)
            )
            if update_result.rowcount != 1:
                raise BatchNotFoundError(f"{batch_id}/{item_id}")

    @staticmethod
    def _to_record(row: BatchJobRow) -> BatchJobRecord:
        items = [
            BatchItemRecord(
                item_id=item.id,
                position=item.position,
                filename=item.filename,
                content_type=item.content_type,
                status=BatchItemStatus(item.status),
                document_id=item.document_id,
                error=item.error,
            )
            for item in row.items
        ]
        return BatchJobRecord(
            batch_id=row.id,
            schema_name=row.schema_name,
            status=BatchStatus(row.status),
            total_items=len(items),
            completed_items=sum(item.status is BatchItemStatus.COMPLETED for item in items),
            failed_items=sum(item.status is BatchItemStatus.FAILED for item in items),
            created_at=row.created_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            items=items,
        )
