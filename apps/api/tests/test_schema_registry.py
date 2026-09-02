import pytest

from evidence_parse.schemas import InvoiceSchema, SchemaRegistry, UnsupportedSchemaError


def test_registry_resolves_schema_names_case_insensitively() -> None:
    registry = SchemaRegistry([InvoiceSchema()])

    assert registry.get(" Invoice ").name == "invoice"
    assert registry.names == ["invoice"]


def test_registry_reports_supported_names_for_unknown_schema() -> None:
    registry = SchemaRegistry([InvoiceSchema()])

    with pytest.raises(UnsupportedSchemaError, match="Supported schemas: invoice"):
        registry.get("receipt")


def test_registry_rejects_duplicate_schema_names() -> None:
    with pytest.raises(ValueError, match="registered more than once"):
        SchemaRegistry([InvoiceSchema(), InvoiceSchema()])
