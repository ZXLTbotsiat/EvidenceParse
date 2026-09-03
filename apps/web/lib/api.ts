import type { BatchJob, ParseResult, PreprocessingPage, ReviewEvent } from "./types";

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

export async function renderPdfPage(file: File, page: number, apiKey: string) {
  const body = new FormData();
  body.append("file", file);
  body.append("page", String(page));
  const response = await fetch(`${API_URL}/api/v1/previews/pdf-page`, {
    method: "POST", headers: headers(apiKey), body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "PDF 原文预览失败。");
  }
  return response.blob();
}

export async function renderOcrPage(
  file: File,
  recipe: PreprocessingPage,
  apiKey: string,
) {
  const body = new FormData();
  body.append("file", file);
  body.append("page", String(recipe.page));
  body.append("variant", recipe.variant);
  body.append("rotation_degrees", String(recipe.rotation_degrees));
  body.append("deskew_degrees", String(recipe.deskew_degrees));
  const response = await fetch(`${API_URL}/api/v1/previews/ocr-page`, {
    method: "POST", headers: headers(apiKey), body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "OCR input preview failed.");
  }
  return response.blob();
}

export async function createBatch(files: File[], schema: string, apiKey: string) {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  body.append("schema", schema);
  return readPayload<BatchJob>(await fetch(`${API_URL}/api/v1/batches`, {
    method: "POST", headers: headers(apiKey), body,
  }));
}

export async function fetchBatch(batchId: string, apiKey: string) {
  return readPayload<BatchJob>(await fetch(`${API_URL}/api/v1/batches/${batchId}`, {
    headers: headers(apiKey),
  }));
}

export async function fetchDocument(documentId: string, apiKey: string) {
  return readPayload<ParseResult>(await fetch(`${API_URL}/api/v1/documents/${documentId}`, {
    headers: headers(apiKey),
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
