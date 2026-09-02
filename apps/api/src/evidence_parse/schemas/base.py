from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Protocol

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import ExtractedValue, InvoiceLineItem, PageContent, ValidationResult


@dataclass(frozen=True)
class SchemaExtraction:
    fields: Dict[str, ExtractedValue]
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DocumentSchema(Protocol):
    name: str

    def extract(self, pages: List[PageContent], spans: List[TextSpan]) -> SchemaExtraction: ...

    def validate(
        self, fields: Dict[str, ExtractedValue], line_items: List[InvoiceLineItem]
    ) -> List[ValidationResult]: ...


class UnsupportedSchemaError(ValueError):
    pass


class SchemaRegistry:
    """Resolve document schemas by stable public names."""

    def __init__(self, schemas: Iterable[DocumentSchema]) -> None:
        self._schemas: Dict[str, DocumentSchema] = {}
        for schema in schemas:
            name = schema.name.casefold().strip()
            if not name:
                raise ValueError("Document schema names cannot be empty.")
            if name in self._schemas:
                raise ValueError(f"Document schema '{name}' is registered more than once.")
            self._schemas[name] = schema
        if not self._schemas:
            raise ValueError("At least one document schema must be registered.")

    def get(self, name: str) -> DocumentSchema:
        normalized = name.casefold().strip()
        try:
            return self._schemas[normalized]
        except KeyError as exc:
            supported = ", ".join(sorted(self._schemas))
            raise UnsupportedSchemaError(
                f"Unknown schema '{name}'. Supported schemas: {supported}."
            ) from exc

    @property
    def names(self) -> List[str]:
        return sorted(self._schemas)
