import uuid
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from evidence_parse.models import DocumentParseResult, ReviewStatus
from evidence_parse.persistence.tables import DocumentRow, ReviewEventRow, UploadRow


class DocumentNotFoundError(LookupError):
    pass


class RevisionConflictError(RuntimeError):
    pass


class DuplicateDocumentRaceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentListRecord:
    document_id: str
    filename: str
    source_kind: str
    schema_name: str
    review_status: str
    revision: int
    occurrences: int
    created_at: Any


@dataclass(frozen=True)
class ReviewEventRecord:
    event_id: str
    document_id: str
    revision: int
    event_type: str
    field_path: Optional[str]
    previous_value: Optional[Any]
    new_value: Optional[Any]
    reason: str
    reviewer: str
    created_at: Any


class DocumentRepository:
    """Persistence boundary for canonical documents, uploads, and review audit events."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def find_by_fingerprint(
        self, fingerprint: str, schema_name: str
    ) -> Optional[DocumentParseResult]:
        with Session(self.engine) as session:
            row = session.scalar(
                select(DocumentRow).where(
                    DocumentRow.content_fingerprint == fingerprint,
                    DocumentRow.schema_name == schema_name,
                )
            )
            return self._to_result(session, row, is_duplicate=True) if row else None

    def get(self, document_id: str) -> DocumentParseResult:
        with Session(self.engine) as session:
            row = session.get(DocumentRow, document_id)
            if row is None:
                raise DocumentNotFoundError(document_id)
            return self._to_result(session, row, is_duplicate=False)

    def create(self, result: DocumentParseResult) -> DocumentParseResult:
        status = _initial_review_status(result)
        row = DocumentRow(
            id=result.document_id,
            content_fingerprint=result.content_fingerprint,
            filename=result.filename,
            content_type=result.content_type,
            source_kind=result.source_kind.value,
            schema_name=result.schema_name,
            page_count=result.page_count,
            result_json=result.model_dump(mode="json"),
            review_status=status.value,
            revision=0,
        )
        try:
            with Session(self.engine) as session, session.begin():
                session.add(row)
                session.add(_upload_row(result.document_id, result.filename, result.content_type))
        except IntegrityError as exc:
            raise DuplicateDocumentRaceError(result.content_fingerprint) from exc
        return self.get(result.document_id)

    def record_duplicate_upload(
        self, document_id: str, filename: str, content_type: str
    ) -> DocumentParseResult:
        with Session(self.engine) as session, session.begin():
            row = session.get(DocumentRow, document_id)
            if row is None:
                raise DocumentNotFoundError(document_id)
            session.add(_upload_row(document_id, filename, content_type))
        with Session(self.engine) as session:
            row = session.get(DocumentRow, document_id)
            return self._to_result(session, row, is_duplicate=True)

    def list(
        self,
        review_status: Optional[ReviewStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DocumentListRecord], int]:
        count_subquery = (
            select(func.count(UploadRow.id))
            .where(UploadRow.document_id == DocumentRow.id)
            .correlate(DocumentRow)
            .scalar_subquery()
        )
        statement = select(DocumentRow, count_subquery.label("occurrences"))
        if review_status is not None:
            statement = statement.where(DocumentRow.review_status == review_status.value)
        statement = statement.order_by(DocumentRow.created_at.desc()).limit(limit).offset(offset)
        with Session(self.engine) as session:
            rows = session.execute(statement).all()
            total_statement = select(func.count()).select_from(DocumentRow)
            if review_status is not None:
                total_statement = total_statement.where(
                    DocumentRow.review_status == review_status.value
                )
            total = session.scalar(total_statement) or 0
            records = [
                DocumentListRecord(
                    document_id=row.id,
                    filename=row.filename,
                    source_kind=row.source_kind,
                    schema_name=row.schema_name,
                    review_status=row.review_status,
                    revision=row.revision,
                    occurrences=occurrences,
                    created_at=row.created_at,
                )
                for row, occurrences in rows
            ]
            return records, total

    def update_with_event(
        self,
        result: DocumentParseResult,
        expected_revision: int,
        event_type: str,
        field_path: Optional[str],
        previous_value: Optional[Any],
        new_value: Optional[Any],
        reason: str,
        reviewer: str,
        review_status: ReviewStatus,
    ) -> DocumentParseResult:
        next_revision = expected_revision + 1
        stored_result = result.model_copy(deep=True)
        stored_result.review.revision = next_revision
        stored_result.review.status = review_status
        statement = (
            update(DocumentRow)
            .where(
                DocumentRow.id == result.document_id,
                DocumentRow.revision == expected_revision,
            )
            .values(
                result_json=stored_result.model_dump(mode="json"),
                review_status=review_status.value,
                revision=next_revision,
            )
        )
        with Session(self.engine) as session, session.begin():
            update_result = session.execute(statement)
            if update_result.rowcount != 1:
                exists = session.scalar(
                    select(func.count())
                    .select_from(DocumentRow)
                    .where(DocumentRow.id == result.document_id)
                )
                if not exists:
                    raise DocumentNotFoundError(result.document_id)
                raise RevisionConflictError(result.document_id)
            session.add(
                ReviewEventRow(
                    id=str(uuid.uuid4()),
                    document_id=result.document_id,
                    revision=next_revision,
                    event_type=event_type,
                    field_path=field_path,
                    previous_value=previous_value,
                    new_value=new_value,
                    reason=reason,
                    reviewer=reviewer,
                )
            )
        return self.get(result.document_id)

    def review_events(self, document_id: str) -> List[ReviewEventRecord]:
        with Session(self.engine) as session:
            if session.get(DocumentRow, document_id) is None:
                raise DocumentNotFoundError(document_id)
            rows = session.scalars(
                select(ReviewEventRow)
                .where(ReviewEventRow.document_id == document_id)
                .order_by(ReviewEventRow.revision, ReviewEventRow.created_at)
            ).all()
            return [
                ReviewEventRecord(
                    event_id=row.id,
                    document_id=row.document_id,
                    revision=row.revision,
                    event_type=row.event_type,
                    field_path=row.field_path,
                    previous_value=row.previous_value,
                    new_value=row.new_value,
                    reason=row.reason,
                    reviewer=row.reviewer,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @staticmethod
    def _to_result(session: Session, row: DocumentRow, is_duplicate: bool) -> DocumentParseResult:
        result = DocumentParseResult.model_validate(row.result_json)
        occurrences = session.scalar(
            select(func.count(UploadRow.id)).where(UploadRow.document_id == row.id)
        )
        result.duplicate.is_duplicate = is_duplicate
        result.duplicate.canonical_document_id = row.id if is_duplicate else None
        result.duplicate.occurrences = occurrences or 1
        result.review.status = ReviewStatus(row.review_status)
        result.review.revision = row.revision
        result.review.unresolved_fields = _unresolved_fields(result)
        return result


def _upload_row(document_id: str, filename: str, content_type: str) -> UploadRow:
    return UploadRow(
        id=str(uuid.uuid4()),
        document_id=document_id,
        filename=filename,
        content_type=content_type,
    )


def _initial_review_status(result: DocumentParseResult) -> ReviewStatus:
    return ReviewStatus.PENDING if _unresolved_fields(result) else ReviewStatus.NOT_REQUIRED


def _unresolved_fields(result: DocumentParseResult) -> List[str]:
    unresolved = [
        f"fields.{name}" for name, value in result.fields.items() if value.review_required
    ]
    for item_index, item in enumerate(result.line_items):
        for name in ("description", "quantity", "unit_price", "tax_rate", "amount"):
            value = getattr(item, name)
            if value is not None and value.review_required:
                unresolved.append(f"line_items.{item_index}.{name}")

    # High-confidence extraction can still violate a deterministic rule. Route
    # the concrete fields behind a failed validation into the same review queue.
    for validation in result.validations:
        if validation.passed is not False:
            continue
        for field_path in validation.fields:
            normalized_path = (
                f"fields.{field_path}" if field_path in result.fields else field_path
            )
            if normalized_path not in unresolved and _is_correctable_path(normalized_path):
                unresolved.append(normalized_path)
    return unresolved


def _is_correctable_path(field_path: str) -> bool:
    if field_path.startswith("fields."):
        return True
    segments = field_path.split(".")
    return len(segments) == 3 and segments[0] == "line_items" and segments[1].isdigit()
