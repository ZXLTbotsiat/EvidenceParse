from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI
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
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(router)

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "evidence-parse-api", "version": __version__}

    return application


app = create_app()
