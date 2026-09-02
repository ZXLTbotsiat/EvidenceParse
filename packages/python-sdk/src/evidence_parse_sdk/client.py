import mimetypes
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import httpx

JsonObject = Dict[str, Any]
BatchFile = Tuple[str, bytes, str]


class EvidenceParseError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"EvidenceParse returned HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class EvidenceParseClient:
    """Synchronous client with explicit lifecycle and no credential persistence."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> "EvidenceParseClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def health_ready(self) -> JsonObject:
        return self._request_object("GET", "/health/ready")

    def parse_document(self, path: Union[Path, str], schema: str = "invoice") -> JsonObject:
        source = Path(path)
        content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        return self.parse_bytes(source.name, source.read_bytes(), content_type, schema)

    def parse_bytes(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        schema: str = "invoice",
    ) -> JsonObject:
        return self._request_object(
            "POST",
            "/api/v1/documents/parse",
            data={"schema": schema},
            files={"file": (filename, content, content_type)},
        )

    def create_batch(
        self,
        files: Sequence[BatchFile],
        schema: str = "invoice",
    ) -> JsonObject:
        multipart = [("files", item) for item in files]
        return self._request_object(
            "POST",
            "/api/v1/batches",
            data={"schema": schema},
            files=multipart,
        )

    def get_batch(self, batch_id: str) -> JsonObject:
        return self._request_object("GET", f"/api/v1/batches/{batch_id}")

    def list_documents(
        self,
        review_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> JsonObject:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if review_status:
            params["review_status"] = review_status
        return self._request_object("GET", "/api/v1/documents", params=params)

    def get_document(self, document_id: str) -> JsonObject:
        return self._request_object("GET", f"/api/v1/documents/{document_id}")

    def correct_field(
        self,
        document_id: str,
        field_path: str,
        value: Optional[str],
        reason: str,
        reviewer: str,
        expected_revision: int,
    ) -> JsonObject:
        return self._request_object(
            "POST",
            f"/api/v1/documents/{document_id}/corrections",
            json={
                "field_path": field_path,
                "value": value,
                "reason": reason,
                "reviewer": reviewer,
                "expected_revision": expected_revision,
            },
        )

    def decide_review(
        self,
        document_id: str,
        status: str,
        note: str,
        reviewer: str,
        expected_revision: int,
    ) -> JsonObject:
        return self._request_object(
            "POST",
            f"/api/v1/documents/{document_id}/review",
            json={
                "status": status,
                "note": note,
                "reviewer": reviewer,
                "expected_revision": expected_revision,
            },
        )

    def review_events(self, document_id: str) -> List[JsonObject]:
        return self._request_list("GET", f"/api/v1/documents/{document_id}/review-events")

    def _request_object(self, method: str, path: str, **kwargs: Any) -> JsonObject:
        payload = self._request_json(method, path, **kwargs)
        if not isinstance(payload, dict):
            raise EvidenceParseError(200, "The response was not a JSON object.")
        return payload

    def _request_list(self, method: str, path: str, **kwargs: Any) -> List[JsonObject]:
        payload = self._request_json(method, path, **kwargs)
        is_object_list = isinstance(payload, list) and all(
            isinstance(item, dict) for item in payload
        )
        if not is_object_list:
            raise EvidenceParseError(200, "The response was not a JSON object list.")
        return payload

    def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise EvidenceParseError(response.status_code, str(detail))
        try:
            return response.json()
        except ValueError as exc:
            raise EvidenceParseError(
                response.status_code, "The response was not valid JSON."
            ) from exc
