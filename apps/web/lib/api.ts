import type { ParseResult, ReviewEvent } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readPayload<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail ?? "请求处理失败，请稍后重试。");
  return payload as T;
}

function headers(apiKey: string, extra: Record<string, string> = {}) {
  return apiKey ? { ...extra, "X-API-Key": apiKey } : extra;
}

export async function parseDocument(file: File, schema: string, apiKey: string) {
  const body = new FormData();
  body.append("file", file);
  body.append("schema", schema);
  return readPayload<ParseResult>(await fetch(`${API_URL}/api/v1/documents/parse`, {
    method: "POST", headers: headers(apiKey), body,
  }));
}

export async function fetchReviewEvents(documentId: string, apiKey: string) {
  return readPayload<ReviewEvent[]>(await fetch(`${API_URL}/api/v1/documents/${documentId}/review-events`, {
    headers: headers(apiKey),
  }));
}

export async function correctField(
  documentId: string,
  apiKey: string,
  input: { field_path: string; value: string | null; reason: string; reviewer: string; expected_revision: number },
) {
  return readPayload<ParseResult>(await fetch(`${API_URL}/api/v1/documents/${documentId}/corrections`, {
    method: "POST",
    headers: headers(apiKey, { "Content-Type": "application/json" }),
    body: JSON.stringify(input),
  }));
}

export async function approveDocument(
  documentId: string,
  apiKey: string,
  reviewer: string,
  note: string,
  expectedRevision: number,
) {
  return readPayload<ParseResult>(await fetch(`${API_URL}/api/v1/documents/${documentId}/review`, {
    method: "POST",
    headers: headers(apiKey, { "Content-Type": "application/json" }),
    body: JSON.stringify({ status: "approved", note, reviewer, expected_revision: expectedRevision }),
  }));
}
