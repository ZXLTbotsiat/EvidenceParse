import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from starlette.concurrency import run_in_threadpool

from evidence_parse.api.dependencies import batch_service, document_service
from evidence_parse.api.models import (
    BatchJobResponse,
    DocumentListItem,
    DocumentListResponse,
    FieldCorrectionRequest,
    ReviewDecisionRequest,
    ReviewEvent,
)
from evidence_parse.api.security import require_api_key
from evidence_parse.application import (
    BatchApplicationService,
    DocumentApplicationService,
    InvalidFieldPathError,
    InvalidReviewDecisionError,
)
from evidence_parse.models import DocumentParseResult, ReviewStatus
from evidence_parse.persistence import (
    BatchNotFoundError,
    DocumentNotFoundError,
    RevisionConflictError,
)
from evidence_parse.schemas import UnsupportedSchemaError
from evidence_parse.service import InvalidDocumentError, UnsupportedDocumentError

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


@router.post("/batches", response_model=BatchJobResponse, status_code=202)
async def create_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    schema_name: str = Form("invoice", alias="schema"),
    service: BatchApplicationService = Depends(batch_service),
) -> BatchJobResponse:
    max_files = int(os.getenv("EVIDENCE_PARSE_MAX_BATCH_FILES", "20"))
    max_file_bytes = int(os.getenv("EVIDENCE_PARSE_MAX_UPLOAD_MB", "20")) * 1024 * 1024
    max_batch_bytes = int(os.getenv("EVIDENCE_PARSE_MAX_BATCH_MB", "100")) * 1024 * 1024
    if len(files) > max_files:
        raise HTTPException(
            status_code=413,
            detail=f"A batch can contain at most {max_files} files.",
        )

    buffered_files = []
    total_bytes = 0
    for file in files:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"{file.filename or 'A file'} is empty.")
        if len(content) > max_file_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{file.filename or 'A file'} exceeds the per-file size limit.",
            )
        total_bytes += len(content)
        buffered_files.append(
            (
                file.filename or "document",
                file.content_type or "application/octet-stream",
                content,
            )
        )
    if total_bytes > max_batch_bytes:
        raise HTTPException(status_code=413, detail="The batch exceeds the total size limit.")

    try:
        record, sources = await run_in_threadpool(service.create, buffered_files, schema_name)
    except UnsupportedSchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(service.process, record.batch_id, record.schema_name, sources)
    return BatchJobResponse.model_validate(record)


@router.get("/batches/{batch_id}", response_model=BatchJobResponse)
async def get_batch(
    batch_id: str,
    service: BatchApplicationService = Depends(batch_service),
) -> BatchJobResponse:
    try:
        record = await run_in_threadpool(service.get, batch_id)
        return BatchJobResponse.model_validate(record)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Batch not found.") from exc


@router.post("/documents/parse", response_model=DocumentParseResult)
async def parse_document(
    file: UploadFile = File(...),
    schema_name: str = Form("invoice", alias="schema"),
    service: DocumentApplicationService = Depends(document_service),
) -> DocumentParseResult:
    content = await file.read()
    max_bytes = int(os.getenv("EVIDENCE_PARSE_MAX_UPLOAD_MB", "20")) * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the size limit.")

    try:
        return await run_in_threadpool(
            service.parse_and_store,
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            schema_name=schema_name,
        )
    except UnsupportedSchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except InvalidDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    review_status: Optional[ReviewStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: DocumentApplicationService = Depends(document_service),
) -> DocumentListResponse:
    records, total = await run_in_threadpool(
        service.list, review_status=review_status, limit=limit, offset=offset
    )
    return DocumentListResponse(
        items=[DocumentListItem.model_validate(record.__dict__) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentParseResult)
async def get_document(
    document_id: str,
    service: DocumentApplicationService = Depends(document_service),
) -> DocumentParseResult:
    try:
        return await run_in_threadpool(service.get, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc


@router.post("/documents/{document_id}/corrections", response_model=DocumentParseResult)
async def correct_field(
    document_id: str,
    request: FieldCorrectionRequest,
    service: DocumentApplicationService = Depends(document_service),
) -> DocumentParseResult:
    try:
        return await run_in_threadpool(
            service.correct_field,
            document_id=document_id,
            field_path=request.field_path,
            value=request.value,
            reason=request.reason,
            reviewer=request.reviewer,
            expected_revision=request.expected_revision,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    except InvalidFieldPathError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid field path: {exc}.") from exc
    except RevisionConflictError as exc:
        raise HTTPException(
            status_code=409, detail="The document was changed by another review."
        ) from exc


@router.post("/documents/{document_id}/review", response_model=DocumentParseResult)
async def decide_review(
    document_id: str,
    request: ReviewDecisionRequest,
    service: DocumentApplicationService = Depends(document_service),
) -> DocumentParseResult:
    try:
        return await run_in_threadpool(
            service.decide_review,
            document_id=document_id,
            status=request.status,
            note=request.note,
            reviewer=request.reviewer,
            expected_revision=request.expected_revision,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    except InvalidReviewDecisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RevisionConflictError as exc:
        raise HTTPException(
            status_code=409, detail="The document was changed by another review."
        ) from exc


@router.get("/documents/{document_id}/review-events", response_model=List[ReviewEvent])
async def review_events(
    document_id: str,
    service: DocumentApplicationService = Depends(document_service),
) -> List[ReviewEvent]:
    try:
        records = await run_in_threadpool(service.review_events, document_id)
        return [ReviewEvent.model_validate(record.__dict__) for record in records]
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
