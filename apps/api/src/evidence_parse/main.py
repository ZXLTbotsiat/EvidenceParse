import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from evidence_parse import __version__
from evidence_parse.api.routes import router
from evidence_parse.application import BatchApplicationService, DocumentApplicationService
from evidence_parse.persistence import BatchRepository, Database, DocumentRepository
from evidence_parse.schemas import InvoiceSchema, SchemaRegistry
from evidence_parse.service import DocumentParser
from evidence_parse.settings import Settings


def create_app(
    database_url: Optional[str] = None,
    auto_create_schema: Optional[bool] = None,
) -> FastAPI:
    settings = Settings.from_environment()
    database = Database(database_url or settings.database_url)
    should_create_schema = (
        settings.auto_create_schema if auto_create_schema is None else auto_create_schema
    )
    schemas = SchemaRegistry([InvoiceSchema()])
    parser = DocumentParser(schema_registry=schemas)
    repository = DocumentRepository(database.engine)
    service = DocumentApplicationService(parser, repository, schemas)
    batch_service = BatchApplicationService(service, BatchRepository(database.engine), schemas)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if should_create_schema:
            await run_in_threadpool(database.create_schema)
        yield
        database.dispose()

    application = FastAPI(
        title="EvidenceParse API",
        version=__version__,
        description="Evidence-first document extraction with explicit human-review boundaries.",
        lifespan=lifespan,
    )
    application.state.database = database
    application.state.document_service = service
    application.state.batch_service = batch_service
    application.state.settings = settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(router)

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "evidence-parse-api", "version": __version__}

    @application.get("/health/live")
    def liveness() -> dict:
        return {"status": "ok"}

    @application.get("/health/ready")
    async def readiness() -> dict:
        try:
            await run_in_threadpool(database.ping)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
        return {"status": "ready"}

    return application


app = create_app()
