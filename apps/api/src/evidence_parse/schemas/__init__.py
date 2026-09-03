"""Document schema registry and built-in schemas."""

from evidence_parse.schemas.base import (
    DocumentSchema,
    SchemaExtraction,
    SchemaRegistry,
    UnsupportedSchemaError,
)
from evidence_parse.schemas.generic import GenericOcrSchema
from evidence_parse.schemas.invoice import InvoiceSchema

__all__ = [
    "DocumentSchema",
    "GenericOcrSchema",
    "InvoiceSchema",
    "SchemaExtraction",
    "SchemaRegistry",
    "UnsupportedSchemaError",
]
