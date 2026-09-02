import logging
import uuid
from dataclasses import dataclass
from typing import Sequence, Tuple

from evidence_parse.application.documents import DocumentApplicationService
from evidence_parse.persistence import BatchItemSeed, BatchJobRecord, BatchRepository
from evidence_parse.schemas import SchemaRegistry, UnsupportedSchemaError
from evidence_parse.service import InvalidDocumentError, UnsupportedDocumentError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchSource:
    item_id: str
    filename: str
    content_type: str
    content: bytes


class BatchApplicationService:
    """Coordinate a bounded in-process batch while persisting observable state."""

    def __init__(
        self,
        documents: DocumentApplicationService,
        repository: BatchRepository,
        schema_registry: SchemaRegistry,
    ) -> None:
        self.documents = documents
        self.repository = repository
        self.schema_registry = schema_registry

    def create(
        self,
        files: Sequence[tuple[str, str, bytes]],
        schema_name: str,
    ) -> Tuple[BatchJobRecord, Sequence[BatchSource]]:
        schema = self.schema_registry.get(schema_name)
        batch_id = str(uuid.uuid4())
        sources = [
            BatchSource(
                item_id=str(uuid.uuid4()),
                filename=filename,
                content_type=content_type,
                content=content,
            )
            for filename, content_type, content in files
        ]
        record = self.repository.create(
            batch_id,
            schema.name,
            [
                BatchItemSeed(
                    item_id=source.item_id,
                    position=position,
                    filename=source.filename,
                    content_type=source.content_type,
                )
                for position, source in enumerate(sources)
            ],
        )
        # Uploaded bytes remain transient until a retention policy is explicit;
        # only lifecycle state and extracted document references are persisted.
        return record, sources

    def process(self, batch_id: str, schema_name: str, sources: Sequence[BatchSource]) -> None:
        self.repository.mark_running(batch_id)
        for source in sources:
            self.repository.mark_item_processing(batch_id, source.item_id)
            try:
                result = self.documents.parse_and_store(
                    source.filename,
                    source.content_type,
                    source.content,
                    schema_name,
                )
            except (InvalidDocumentError, UnsupportedDocumentError, UnsupportedSchemaError) as exc:
                self.repository.mark_item_failed(batch_id, source.item_id, str(exc))
            except Exception:
                logger.exception("Unexpected batch item failure", extra={"batch_id": batch_id})
                self.repository.mark_item_failed(
                    batch_id, source.item_id, "Unexpected processing error."
                )
            else:
                self.repository.mark_item_completed(
                    batch_id, source.item_id, result.document_id
                )
        self.repository.finish(batch_id)

    def get(self, batch_id: str) -> BatchJobRecord:
        return self.repository.get(batch_id)
