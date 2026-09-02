from typing import Dict, List

from evidence_parse.extractors.invoice import InvoiceExtractor
from evidence_parse.extractors.line_items import InvoiceLineItemExtractor
from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import ExtractedValue, InvoiceLineItem, PageContent, ValidationResult
from evidence_parse.schemas.base import SchemaExtraction
from evidence_parse.validators import InvoiceValidator


class InvoiceSchema:
    """Compose invoice fields, layout strategies, and deterministic validation."""

    name = "invoice"

    def __init__(self) -> None:
        self.field_extractor = InvoiceExtractor()
        self.line_item_extractor = InvoiceLineItemExtractor()
        self.validator = InvoiceValidator()

    def extract(self, pages: List[PageContent], spans: List[TextSpan]) -> SchemaExtraction:
        fields = self.field_extractor.extract(pages, spans)
        line_items = self.line_item_extractor.extract(pages, spans)
        warnings = [] if line_items else ["No invoice line items were detected."]
        return SchemaExtraction(
            fields=fields,
            line_items=line_items,
            validations=self.validate(fields, line_items),
            warnings=warnings,
        )

    def validate(
        self,
        fields: Dict[str, ExtractedValue],
        line_items: List[InvoiceLineItem],
    ) -> List[ValidationResult]:
        return self.validator.validate(fields, line_items)
