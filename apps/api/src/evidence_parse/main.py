import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from evidence_parse import __version__
from evidence_parse.models import DocumentParseResult
from evidence_parse.schemas import UnsupportedSchemaError
from evidence_parse.service import DocumentParser, UnsupportedDocumentError

app = FastAPI(
    title="EvidenceParse API",
    version=__version__,
    description="Evidence-first document extraction with explicit human-review boundaries.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
parser = DocumentParser()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "evidence-parse-api", "version": __version__}


@app.post("/api/v1/documents/parse", response_model=DocumentParseResult)
async def parse_document(
    file: UploadFile = File(...), schema_name: str = Form("invoice", alias="schema")
) -> DocumentParseResult:
    content = await file.read()
    max_bytes = int(os.getenv("EVIDENCE_PARSE_MAX_UPLOAD_MB", "20")) * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the size limit.")

    try:
        return await run_in_threadpool(
            parser.parse,
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            schema_name=schema_name,
        )
    except UnsupportedSchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="The document could not be parsed.") from exc
