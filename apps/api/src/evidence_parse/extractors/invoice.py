import re
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Pattern, Tuple

from evidence_parse.extractors.pdf import TextSpan, locate_text
from evidence_parse.models import Evidence, ExtractedValue, PageContent, ValidationResult

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
AUTO_ACCEPT_CONFIDENCE = 0.8
TEXT_PATTERN_CONFIDENCE = 0.92
UNLOCATED_PATTERN_CONFIDENCE = 0.75


class InvoiceExtractor:
    def extract(
        self, pages: Iterable[PageContent], spans: List[TextSpan]
    ) -> Tuple[Dict[str, ExtractedValue], List[ValidationResult]]:
        combined_text = "\n".join(page.text for page in pages)
        fields = {
            name: self._extract_field(name, patterns, combined_text, spans)
            for name, patterns in FIELD_PATTERNS.items()
        }
        return fields, self._validate_totals(fields)

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
            evidence: List[Evidence] = []
            confidence = UNLOCATED_PATTERN_CONFIDENCE
            try:
                source_span = locate_text(match.group(0), spans)
                evidence.append(
                    Evidence(
                        page=source_span.page,
                        text=source_span.text,
                        bbox=source_span.bbox,
                    )
                )
                confidence = round(TEXT_PATTERN_CONFIDENCE * source_span.confidence, 4)
            except LookupError:
                pass
            review_required = not evidence or confidence < AUTO_ACCEPT_CONFIDENCE
            if not evidence:
                review_reason = "Value matched but source coordinates were not found."
            elif review_required:
                review_reason = "Value confidence is below the automatic acceptance threshold."
            else:
                review_reason = None
            return ExtractedValue(
                value=value,
                confidence=confidence,
                evidence=evidence,
                review_required=review_required,
                review_reason=review_reason,
            )

        return ExtractedValue(
            confidence=0,
            review_required=True,
            review_reason=f"{name} was not found in the document text.",
        )

    def _validate_totals(self, fields: Dict[str, ExtractedValue]) -> List[ValidationResult]:
        subtotal = _as_decimal(fields["subtotal"].value)
        tax = _as_decimal(fields["tax"].value)
        total = _as_decimal(fields["total"].value)
        if subtotal is None or tax is None or total is None:
            return [
                ValidationResult(
                    code="invoice.total_arithmetic",
                    passed=None,
                    message=(
                        "Unable to verify subtotal + tax because one or more values are missing."
                    ),
                    fields=["subtotal", "tax", "total"],
                )
            ]

        difference = abs((subtotal + tax) - total)
        passed = difference <= Decimal("0.02")
        return [
            ValidationResult(
                code="invoice.total_arithmetic",
                passed=passed,
                message=(
                    "Subtotal and tax reconcile with total."
                    if passed
                    else f"Subtotal + tax differs from total by {difference}."
                ),
                fields=["subtotal", "tax", "total"],
            )
        ]


def _as_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None
