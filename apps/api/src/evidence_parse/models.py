from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"


class ValueSource(str, Enum):
    EXTRACTED = "extracted"
    HUMAN_CORRECTED = "human_corrected"


class ReviewStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class BatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class BatchItemStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    source: ValueSource = ValueSource.EXTRACTED
    original_value: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class DuplicateInfo(BaseModel):
    is_duplicate: bool = False
    canonical_document_id: Optional[str] = None
    occurrences: int = Field(default=1, ge=1)


class ReviewSummary(BaseModel):
    status: ReviewStatus = ReviewStatus.NOT_REQUIRED
    revision: int = Field(default=0, ge=0)
    unresolved_fields: List[str] = Field(default_factory=list)


class InvoiceLineItem(BaseModel):
    index: int = Field(ge=1)
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


class OcrTextBlock(BaseModel):
    """One ordered OCR/text-layer block in source-document coordinates."""

    page: int = Field(description="One-based page number")
    text: str
    bbox: BoundingBox
    confidence: float = Field(ge=0, le=1)


class DocumentParseResult(BaseModel):
    document_id: str
    content_fingerprint: str
    filename: str
    content_type: str
    schema_name: str
    source_kind: SourceKind
    page_count: int
    pages: List[PageContent] = Field(default_factory=list)
    text_blocks: List[OcrTextBlock] = Field(default_factory=list)
    fields: Dict[str, ExtractedValue]
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    validations: List[ValidationResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duplicate: DuplicateInfo = Field(default_factory=DuplicateInfo)
    review: ReviewSummary = Field(default_factory=ReviewSummary)
