from typing import Dict, List

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import ExtractedValue, InvoiceLineItem, PageContent, ValidationResult
from evidence_parse.schemas.base import SchemaExtraction


class GenericOcrSchema:
    """Expose document text without imposing a business-document schema."""

    name = "generic"

    def extract(self, pages: List[PageContent], spans: List[TextSpan]) -> SchemaExtraction:
        return SchemaExtraction(fields={})

    def validate(
        self, fields: Dict[str, ExtractedValue], line_items: List[InvoiceLineItem]
    ) -> List[ValidationResult]:
        return []
