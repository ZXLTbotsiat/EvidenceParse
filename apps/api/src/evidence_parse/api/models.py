from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from evidence_parse.models import ReviewStatus


class FieldCorrectionRequest(BaseModel):
    field_path: str = Field(min_length=3, max_length=256)
    value: Optional[str]
    reason: str = Field(min_length=3, max_length=1000)
    reviewer: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)


class ReviewDecisionRequest(BaseModel):
    status: ReviewStatus
    note: str = Field(min_length=3, max_length=1000)
    reviewer: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    source_kind: str
    schema_name: str
    review_status: ReviewStatus
    revision: int
    occurrences: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: List[DocumentListItem]
    total: int
    limit: int
    offset: int


class ReviewEvent(BaseModel):
    event_id: str
    document_id: str
    revision: int
    event_type: str
    field_path: Optional[str]
    previous_value: Optional[Any]
    new_value: Optional[Any]
    reason: str
    reviewer: str
    created_at: datetime
