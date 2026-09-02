from fastapi import Request

from evidence_parse.application import DocumentApplicationService


def document_service(request: Request) -> DocumentApplicationService:
    return request.app.state.document_service
