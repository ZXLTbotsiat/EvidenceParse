from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Evidence(BaseModel):
    page: int = Field(description="One-based page number")
    text: str
    bbox: Optional[BoundingBox] = None


class ExtractedValue(BaseModel):
    value: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    evidence: List[Evidence] = Field(default_factory=list)
    review_required: bool = False
    review_reason: Optional[str] = None


class InvoiceLineItem(BaseModel):
    description: ExtractedValue
    quantity: Optional[ExtractedValue] = None
    unit_price: Optional[ExtractedValue] = None
    tax_rate: Optional[ExtractedValue] = None
    amount: Optional[ExtractedValue] = None


class ValidationResult(BaseModel):
    code: str
    passed: Optional[bool] = None
    message: str
    fields: List[str] = Field(default_factory=list)


class PageContent(BaseModel):
    page: int
    width: float
    height: float
    text: str


class DocumentParseResult(BaseModel):
    document_id: str
    content_fingerprint: str
    filename: str
    content_type: str
    source_kind: SourceKind
    page_count: int
    fields: Dict[str, ExtractedValue]
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    validations: List[ValidationResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

