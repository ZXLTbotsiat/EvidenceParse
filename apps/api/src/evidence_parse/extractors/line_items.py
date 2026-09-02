import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Protocol, Sequence

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.extractors.values import extracted_value
from evidence_parse.models import ExtractedValue, InvoiceLineItem, PageContent

SUMMARY_PATTERN = re.compile(r"^(?:sub\s*total|tax|gst|vat|grand\s+total|total)\b", re.I)
LABELED_DESCRIPTION = re.compile(r"^(?:description|item)\s*[:.\-]?\s*(.+)$", re.I)
LABELED_VALUES = {
    "quantity": re.compile(r"^(?:quantity|qty)\s*[:.\-]?\s*([\d,.]+)$", re.I),
    "unit_price": re.compile(
        r"^(?:unit\s+price|unit\s+rate|price)\s*[:.\-]?\s*(?:[$₹€£]\s*)?([\d,]+\.\d{2})$",
        re.I,
    ),
    "tax_rate": re.compile(r"^(?:tax\s+rate|vat\s+rate)\s*[:.\-]?\s*([\d.]+%?)$", re.I),
    "amount": re.compile(
        r"^(?:line\s+amount|amount)\s*[:.\-]?\s*(?:[$₹€£]\s*)?([\d,]+\.\d{2})$",
        re.I,
    ),
}


@dataclass(frozen=True)
class LineItemCandidate:
    page: int
    description: str
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    tax_rate: Optional[str] = None
    amount: Optional[str] = None
    sources: Dict[str, str] = field(default_factory=dict)


class LineItemLayout(Protocol):
    """A layout strategy that discovers raw line-item candidates on one page."""

    def find(self, page: PageContent) -> List[LineItemCandidate]: ...


class LabeledBlockLayout:
    """Read vertical key-value blocks such as Description/Quantity/Unit Price."""

    def find(self, page: PageContent) -> List[LineItemCandidate]:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        candidates: List[LineItemCandidate] = []
        for index, line in enumerate(lines):
            description_match = LABELED_DESCRIPTION.match(line)
            if not description_match:
                continue

            values: Dict[str, str] = {}
            sources = {"description": line}
            for following in lines[index + 1 :]:
                if LABELED_DESCRIPTION.match(following) or SUMMARY_PATTERN.match(following):
                    break
                matched = False
                for name, pattern in LABELED_VALUES.items():
                    value_match = pattern.match(following)
                    if value_match:
                        values[name] = value_match.group(1)
                        sources[name] = following
                        matched = True
                        break
                if not matched and values:
                    break

            if values:
                candidates.append(
                    LineItemCandidate(
                        page=page.page,
                        description=description_match.group(1).strip(),
                        sources=sources,
                        **values,
                    )
                )
        return candidates


class ColumnTableLayout:
    """Read pipe-delimited or whitespace-aligned invoice tables."""

    def find(self, page: PageContent) -> List[LineItemCandidate]:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for header_index, header_line in enumerate(lines):
            delimiter = "pipe" if "|" in header_line else "spaces"
            header = self._split(header_line, delimiter)
            columns = [self._column_name(value) for value in header]
            if "description" not in columns or "amount" not in columns:
                continue

            candidates: List[LineItemCandidate] = []
            for line in lines[header_index + 1 :]:
                if SUMMARY_PATTERN.match(line):
                    break
                values = self._split(line, delimiter)
                if len(values) != len(columns):
                    if candidates:
                        break
                    continue
                row = {name: value for name, value in zip(columns, values) if name}
                if row.get("description") and row.get("amount"):
                    candidates.append(
                        LineItemCandidate(
                            page=page.page,
                            description=row["description"],
                            quantity=row.get("quantity"),
                            unit_price=row.get("unit_price"),
                            tax_rate=row.get("tax_rate"),
                            amount=row.get("amount"),
                            sources={name: line for name in row},
                        )
                    )
            if candidates:
                return candidates
        return []

    @staticmethod
    def _split(line: str, delimiter: str) -> List[str]:
        values = line.split("|") if delimiter == "pipe" else re.split(r"\s{2,}", line)
        return [value.strip() for value in values if value.strip()]

    @staticmethod
    def _column_name(value: str) -> Optional[str]:
        normalized = re.sub(r"[^a-z%]+", " ", value.casefold()).strip()
        if normalized in {"description", "item", "product", "service"}:
            return "description"
        if normalized in {"quantity", "qty"}:
            return "quantity"
        if normalized in {"unit price", "unit rate", "price", "rate"}:
            return "unit_price"
        if normalized in {"tax rate", "vat rate", "tax %", "vat %"}:
            return "tax_rate"
        if normalized in {"amount", "line amount", "line total"}:
            return "amount"
        return None


class InvoiceLineItemExtractor:
    def __init__(self, layouts: Optional[Sequence[LineItemLayout]] = None) -> None:
        self.layouts = list(layouts or (ColumnTableLayout(), LabeledBlockLayout()))

    def extract(self, pages: Iterable[PageContent], spans: List[TextSpan]) -> List[InvoiceLineItem]:
        candidates: List[LineItemCandidate] = []
        for page in pages:
            for layout in self.layouts:
                page_candidates = layout.find(page)
                if page_candidates:
                    candidates.extend(page_candidates)
                    break

        return [
            self._to_line_item(index, candidate, spans)
            for index, candidate in enumerate(candidates, 1)
        ]

    @staticmethod
    def _to_line_item(
        index: int, candidate: LineItemCandidate, spans: List[TextSpan]
    ) -> InvoiceLineItem:
        def optional_value(field_name: str, value: Optional[str]) -> Optional[ExtractedValue]:
            if value is None:
                return None
            source_text = candidate.sources.get(field_name, candidate.sources["description"])
            return extracted_value(value, source_text, spans, candidate.page)

        return InvoiceLineItem(
            index=index,
            description=extracted_value(
                candidate.description,
                candidate.sources["description"],
                spans,
                candidate.page,
            ),
            quantity=optional_value("quantity", candidate.quantity),
            unit_price=optional_value("unit_price", candidate.unit_price),
            tax_rate=optional_value("tax_rate", candidate.tax_rate),
            amount=optional_value("amount", candidate.amount),
        )
