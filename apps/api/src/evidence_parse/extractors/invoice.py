import re
from typing import Dict, Iterable, List, Pattern

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.extractors.values import extracted_value, missing_value
from evidence_parse.models import ExtractedValue, PageContent

FIELD_PATTERNS: Dict[str, List[Pattern[str]]] = {
    "invoice_number": [
        re.compile(
            r"(?:invoice|bill)\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]+)",
            re.I,
        ),
    ],
    "invoice_date": [
        re.compile(r"(?:invoice\s*)?date\s*[:\-]?\s*(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})", re.I),
    ],
    "subtotal": [
        re.compile(
            r"(?:sub\s*total|taxable\s+amount)\s*[:\-]?\s*(?:[$₹€£]\s*)?([\d,]+\.\d{2})",
            re.I,
        ),
    ],
    "tax": [
        re.compile(r"(?:tax|gst|vat)(?:\s+amount)?\s*[:\-]?\s*(?:[$₹€£]\s*)?([\d,]+\.\d{2})", re.I),
    ],
    "total": [
        re.compile(r"(?<!sub)(?:grand\s+)?total\s*[:\-]?\s*(?:[$₹€£]\s*)?([\d,]+\.\d{2})", re.I),
    ],
}


class InvoiceExtractor:
    """Extract invoice header and summary fields from normalized page text."""

    def extract(
        self, pages: Iterable[PageContent], spans: List[TextSpan]
    ) -> Dict[str, ExtractedValue]:
        combined_text = "\n".join(page.text for page in pages)
        return {
            name: self._extract_field(name, patterns, combined_text, spans)
            for name, patterns in FIELD_PATTERNS.items()
        }

    def _extract_field(
        self,
        name: str,
        patterns: List[Pattern[str]],
        text: str,
        spans: List[TextSpan],
    ) -> ExtractedValue:
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            value = match.group(1).strip()
            return extracted_value(value, match.group(0), spans)

        return missing_value(name)
