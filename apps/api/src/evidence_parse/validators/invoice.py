from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from evidence_parse.models import ExtractedValue, InvoiceLineItem, ValidationResult

AMOUNT_TOLERANCE = Decimal("0.02")


class InvoiceValidator:
    """Validate invoice totals without filling or correcting extracted values."""

    def validate(
        self,
        fields: Dict[str, ExtractedValue],
        line_items: List[InvoiceLineItem],
    ) -> List[ValidationResult]:
        results = [self._validate_document_total(fields)]
        results.extend(self._validate_line_item(item) for item in line_items)
        results.append(self._validate_line_item_sum(fields, line_items))
        return results

    def _validate_document_total(self, fields: Dict[str, ExtractedValue]) -> ValidationResult:
        subtotal = _as_decimal(fields["subtotal"].value)
        tax = _as_decimal(fields["tax"].value)
        total = _as_decimal(fields["total"].value)
        if subtotal is None or tax is None or total is None:
            return ValidationResult(
                code="invoice.total_arithmetic",
                passed=None,
                message="Unable to verify subtotal + tax because one or more values are missing.",
                fields=["subtotal", "tax", "total"],
            )

        difference = abs((subtotal + tax) - total)
        return ValidationResult(
            code="invoice.total_arithmetic",
            passed=difference <= AMOUNT_TOLERANCE,
            message=(
                "Subtotal and tax reconcile with total."
                if difference <= AMOUNT_TOLERANCE
                else f"Subtotal + tax differs from total by {difference}."
            ),
            fields=["subtotal", "tax", "total"],
        )

    def _validate_line_item(self, item: InvoiceLineItem) -> ValidationResult:
        quantity = _value_decimal(item.quantity)
        unit_price = _value_decimal(item.unit_price)
        amount = _value_decimal(item.amount)
        fields = [
            f"line_items.{item.index - 1}.quantity",
            f"line_items.{item.index - 1}.unit_price",
            f"line_items.{item.index - 1}.amount",
        ]
        if quantity is None or unit_price is None or amount is None:
            return ValidationResult(
                code=f"invoice.line_item.{item.index}.arithmetic",
                passed=None,
                message=f"Unable to verify line item {item.index} arithmetic.",
                fields=fields,
            )

        difference = abs((quantity * unit_price) - amount)
        return ValidationResult(
            code=f"invoice.line_item.{item.index}.arithmetic",
            passed=difference <= AMOUNT_TOLERANCE,
            message=(
                f"Line item {item.index} quantity and unit price reconcile with amount."
                if difference <= AMOUNT_TOLERANCE
                else f"Line item {item.index} differs from amount by {difference}."
            ),
            fields=fields,
        )

    def _validate_line_item_sum(
        self,
        fields: Dict[str, ExtractedValue],
        line_items: List[InvoiceLineItem],
    ) -> ValidationResult:
        subtotal = _as_decimal(fields["subtotal"].value)
        amounts = [_value_decimal(item.amount) for item in line_items]
        if subtotal is None or not amounts or any(amount is None for amount in amounts):
            return ValidationResult(
                code="invoice.line_items_subtotal",
                passed=None,
                message="Unable to verify line item sum against subtotal.",
                fields=["line_items", "subtotal"],
            )

        line_total = sum((amount for amount in amounts if amount is not None), Decimal("0"))
        difference = abs(line_total - subtotal)
        return ValidationResult(
            code="invoice.line_items_subtotal",
            passed=difference <= AMOUNT_TOLERANCE,
            message=(
                "Line item amounts reconcile with subtotal."
                if difference <= AMOUNT_TOLERANCE
                else f"Line item sum differs from subtotal by {difference}."
            ),
            fields=["line_items", "subtotal"],
        )


def _value_decimal(value: Optional[ExtractedValue]) -> Optional[Decimal]:
    return _as_decimal(value.value) if value is not None else None


def _as_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None
