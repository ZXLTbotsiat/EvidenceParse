from fastapi import Request

from evidence_parse.application import BatchApplicationService, DocumentApplicationService


def batch_service(request: Request) -> BatchApplicationService:
    return request.app.state.batch_service


def document_service(request: Request) -> DocumentApplicationService:
    return request.app.state.document_service
