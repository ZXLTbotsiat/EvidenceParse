import hashlib
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from evidence_parse.models import (
    DocumentParseResult,
    ExtractedValue,
    ReviewStatus,
    ValueSource,
)
from evidence_parse.persistence.repository import (
    DocumentListRecord,
    DocumentRepository,
    DuplicateDocumentRaceError,
    ReviewEventRecord,
)
from evidence_parse.schemas import SchemaRegistry
from evidence_parse.service import DocumentParser

FIELD_PATH_PATTERN = re.compile(
    r"^(?:fields\.[a-z][a-z0-9_]*|line_items\.\d+\.(?:description|quantity|unit_price|tax_rate|amount))$"
)


class InvalidFieldPathError(ValueError):
    pass


class InvalidReviewDecisionError(ValueError):
    pass


class DocumentApplicationService:
    """Coordinate idempotent ingestion, correction, and review audit history."""

    def __init__(
        self,
        parser: DocumentParser,
        repository: DocumentRepository,
        schema_registry: SchemaRegistry,
    ) -> None:
        self.parser = parser
        self.repository = repository
        self.schema_registry = schema_registry

    def parse_and_store(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        schema_name: str,
    ) -> DocumentParseResult:
        fingerprint = hashlib.sha256(content).hexdigest()
        schema = self.schema_registry.get(schema_name)
        existing = self.repository.find_by_fingerprint(fingerprint, schema.name)
        if existing is not None:
            return self._record_duplicate(existing, filename, content_type)

        result = self.parser.parse(filename, content_type, content, schema.name)
        try:
            return self.repository.create(result)
        except DuplicateDocumentRaceError:
            existing = self.repository.find_by_fingerprint(fingerprint, schema.name)
            if existing is None:
                raise
            return self._record_duplicate(existing, filename, content_type)

    def get(self, document_id: str) -> DocumentParseResult:
        return self.repository.get(document_id)

    def list(
        self,
        review_status: Optional[ReviewStatus],
        limit: int,
        offset: int,
    ) -> Tuple[List[DocumentListRecord], int]:
        return self.repository.list(review_status, limit, offset)

    def correct_field(
        self,
        document_id: str,
        field_path: str,
        value: Optional[str],
        reason: str,
        reviewer: str,
        expected_revision: int,
    ) -> DocumentParseResult:
        result = self.repository.get(document_id)
        target = self._field_at_path(result, field_path)
        previous_value = target.value
        if target.source is ValueSource.EXTRACTED:
            target.original_value = previous_value
        target.value = value
        target.confidence = 1.0
        target.review_required = False
        target.review_reason = f"Human reviewed: {reason}"
        target.source = ValueSource.HUMAN_CORRECTED
        target.reviewed_by = reviewer
        target.reviewed_at = datetime.now(timezone.utc)

        schema = self.schema_registry.get(result.schema_name)
        result.validations = schema.validate(result.fields, result.line_items)
        return self.repository.update_with_event(
            result=result,
            expected_revision=expected_revision,
            event_type="field_corrected",
            field_path=field_path,
            previous_value=previous_value,
            new_value=value,
            reason=reason,
            reviewer=reviewer,
            review_status=ReviewStatus.IN_REVIEW,
        )

    def decide_review(
        self,
        document_id: str,
        status: ReviewStatus,
        note: str,
        reviewer: str,
        expected_revision: int,
    ) -> DocumentParseResult:
        if status not in {ReviewStatus.PENDING, ReviewStatus.APPROVED}:
            raise InvalidReviewDecisionError("A review decision must be pending or approved.")
        result = self.repository.get(document_id)
        if status is ReviewStatus.APPROVED and result.review.unresolved_fields:
            unresolved = ", ".join(result.review.unresolved_fields)
            raise InvalidReviewDecisionError(
                f"Resolve or explicitly confirm these fields before approval: {unresolved}."
            )
        return self.repository.update_with_event(
            result=result,
            expected_revision=expected_revision,
            event_type="review_decided",
            field_path=None,
            previous_value=result.review.status.value,
            new_value=status.value,
            reason=note,
            reviewer=reviewer,
            review_status=status,
        )

    def review_events(self, document_id: str) -> List[ReviewEventRecord]:
        return self.repository.review_events(document_id)

    def _record_duplicate(
        self,
        existing: DocumentParseResult,
        filename: str,
        content_type: str,
    ) -> DocumentParseResult:
        """Record an upload while keeping the canonical extraction unchanged."""

        duplicate = self.repository.record_duplicate_upload(
            existing.document_id, filename, content_type
        )
        # The response describes this upload; persisted canonical metadata still
        # describes the first document that produced the extraction.
        duplicate.filename = filename
        duplicate.content_type = content_type
        return duplicate

    @staticmethod
    def _field_at_path(result: DocumentParseResult, field_path: str) -> ExtractedValue:
        if not FIELD_PATH_PATTERN.fullmatch(field_path):
            raise InvalidFieldPathError(field_path)
        segments = field_path.split(".")
        if segments[0] == "fields":
            try:
                return result.fields[segments[1]]
            except KeyError as exc:
                raise InvalidFieldPathError(field_path) from exc

        item_index = int(segments[1])
        field_name = segments[2]
        try:
            item = result.line_items[item_index]
        except IndexError as exc:
            raise InvalidFieldPathError(field_path) from exc
        target = getattr(item, field_name)
        if target is None:
            target = ExtractedValue(
                confidence=0,
                review_required=True,
                review_reason=f"{field_path} was not extracted.",
            )
            setattr(item, field_name, target)
        return target
