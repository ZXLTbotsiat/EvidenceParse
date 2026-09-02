"use client";

import { ChangeEvent, useState } from "react";

type Evidence = {
  page: number;
  text: string;
  bbox?: { x0: number; y0: number; x1: number; y1: number } | null;
};

type FieldResult = {
  value?: string | null;
  confidence: number;
  evidence: Evidence[];
  review_required: boolean;
  review_reason?: string | null;
  source: "extracted" | "human_corrected";
  original_value?: string | null;
  reviewed_by?: string | null;
};

type LineItem = {
  index: number;
  description: FieldResult;
  quantity?: FieldResult | null;
  unit_price?: FieldResult | null;
  tax_rate?: FieldResult | null;
  amount?: FieldResult | null;
};

type ParseResult = {
  document_id: string;
  filename: string;
  schema_name: string;
  source_kind: string;
  page_count: number;
  fields: Record<string, FieldResult>;
  line_items: LineItem[];
  validations: { code: string; passed?: boolean | null; message: string }[];
  warnings: string[];
  duplicate: {
    is_duplicate: boolean;
    canonical_document_id?: string | null;
    occurrences: number;
  };
  review: {
    status: "not_required" | "pending" | "in_review" | "approved";
    revision: number;
    unresolved_fields: string[];
  };
};

type ReviewEvent = {
  event_id: string;
  revision: number;
  event_type: string;
  field_path?: string | null;
  previous_value?: unknown;
  new_value?: unknown;
  reason: string;
  reviewer: string;
};

type CorrectionTarget = { path: string; label: string; value: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [correctionPath, setCorrectionPath] = useState("");
  const [correctionValue, setCorrectionValue] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [savingReview, setSavingReview] = useState(false);

  const correctionTargets: CorrectionTarget[] = result
    ? [
        ...Object.entries(result.fields).map(([name, field]) => ({
          path: `fields.${name}`,
          label: name.replaceAll("_", " "),
          value: field.value ?? "",
        })),
        ...result.line_items.flatMap((item, index) =>
          (["description", "quantity", "unit_price", "tax_rate", "amount"] as const)
            .filter((name) => item[name] !== undefined)
            .map((name) => ({
              path: `line_items.${index}.${name}`,
              label: `item ${item.index} · ${name.replaceAll("_", " ")}`,
              value: item[name]?.value ?? "",
            })),
        ),
      ]
    : [];

  async function parseDocument() {
    if (!file) return;
    setLoading(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API_URL}/api/v1/documents/parse`, {
        method: "POST",
        body,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Unable to parse document");
      setResult(payload);
      setEvents([]);
      setCorrectionPath("");
      setCorrectionValue("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to parse document");
    } finally {
      setLoading(false);
    }
  }

  function chooseCorrection(path: string) {
    setCorrectionPath(path);
    setCorrectionValue(correctionTargets.find((target) => target.path === path)?.value ?? "");
  }

  async function loadEvents(documentId: string) {
    const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/review-events`);
    if (response.ok) setEvents(await response.json());
  }

  async function saveCorrection() {
    if (!result || !correctionPath || !reviewer || reviewReason.length < 3) return;
    setSavingReview(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/api/v1/documents/${result.document_id}/corrections`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            field_path: correctionPath,
            value: correctionValue || null,
            reason: reviewReason,
            reviewer,
            expected_revision: result.review.revision,
          }),
        },
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Unable to save correction");
      setResult(payload);
      setReviewReason("");
      await loadEvents(payload.document_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save correction");
    } finally {
      setSavingReview(false);
    }
  }

  async function approveReview() {
    if (!result || !reviewer || reviewReason.length < 3) return;
    setSavingReview(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/v1/documents/${result.document_id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "approved",
          note: reviewReason,
          reviewer,
          expected_revision: result.review.revision,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Unable to approve review");
      setResult(payload);
      setReviewReason("");
      await loadEvents(payload.document_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to approve review");
    } finally {
      setSavingReview(false);
    }
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setError("");
  }

  return (
    <main>
      <header>
        <div className="eyebrow">EVIDENCE-FIRST DOCUMENT AI</div>
        <h1>Extract facts.<br />Keep the proof.</h1>
        <p className="lede">
          EvidenceParse turns invoices into structured data while preserving the page,
          source text, confidence, and review boundary behind every value.
        </p>
      </header>

      <section className="workspace">
        <div className="upload-panel">
          <span className="step">01 / INGEST</span>
          <label className="drop-zone">
            <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={chooseFile} />
            <span className="drop-icon">↗</span>
            <strong>{file ? file.name : "Choose a document"}</strong>
            <small>PDF, JPG or PNG · up to 20 MB</small>
          </label>
          <button disabled={!file || loading} onClick={parseDocument}>
            {loading ? "Reading evidence…" : "Parse document"}
          </button>
          {error && <p className="error">{error}</p>}
          <div className="principle">
            <span>NO SILENT GUESSES</span>
            Missing or uncertain fields are routed to review instead of being invented.
          </div>
        </div>

        <div className="result-panel">
          <div className="result-heading">
            <span className="step">02 / VERIFY</span>
            {result && <span className="source-kind">{result.source_kind.replaceAll("_", " ")}</span>}
          </div>

          {!result ? (
            <div className="empty-state">
              <div className="scan-line" />
              <p>Upload an invoice to see extracted values and their source evidence.</p>
            </div>
          ) : (
            <div className="results">
              <div className="document-meta">
                <strong>{result.filename}</strong>
                <span>{result.schema_name} · {result.page_count} page{result.page_count === 1 ? "" : "s"}</span>
              </div>
              <div className="review-summary">
                <span>Review: {result.review.status.replaceAll("_", " ")}</span>
                <span>Revision {result.review.revision}</span>
                <span>{result.review.unresolved_fields.length} unresolved</span>
              </div>
              {result.duplicate.is_duplicate && (
                <p className="duplicate-note">
                  Exact duplicate detected · canonical document reused · {result.duplicate.occurrences} uploads
                </p>
              )}
              {Object.entries(result.fields).map(([name, field]) => (
                <article className="field" key={name}>
                  <div>
                    <span className="field-name">{name.replaceAll("_", " ")}</span>
                    <strong>{field.value ?? "Unable to verify"}</strong>
                  </div>
                  <div className="field-status">
                    <span className={field.review_required ? "review" : "verified"}>
                      {field.review_required ? "Review" : "Verified"}
                    </span>
                    <span>{Math.round(field.confidence * 100)}%</span>
                  </div>
                  {field.source === "human_corrected" && (
                    <p className="human-correction">
                      Human corrected{field.original_value !== null ? ` · original: ${field.original_value ?? "empty"}` : ""}
                    </p>
                  )}
                  {field.evidence[0] && (
                    <p className="evidence">Page {field.evidence[0].page} · “{field.evidence[0].text}”</p>
                  )}
                  {!field.evidence[0] && field.review_reason && (
                    <p className="evidence muted">{field.review_reason}</p>
                  )}
                </article>
              ))}
              {result.line_items.length > 0 && (
                <section className="line-items">
                  <span className="field-name">LINE ITEMS</span>
                  {result.line_items.map((item) => (
                    <article key={item.index} className="line-item">
                      <strong>{item.description.value ?? "Unable to verify"}</strong>
                      <span>Qty {item.quantity?.value ?? "—"}</span>
                      <span>Unit {item.unit_price?.value ?? "—"}</span>
                      <span>Amount {item.amount?.value ?? "—"}</span>
                      <span className={item.description.review_required ? "review" : "verified"}>
                        {item.description.review_required ? "Review" : "Verified"}
                      </span>
                    </article>
                  ))}
                </section>
              )}
              <div className="validations">
                {result.validations.map((validation) => (
                  <p key={validation.code}>
                    <span>{validation.passed === true ? "✓" : validation.passed === false ? "!" : "?"}</span>
                    {validation.message}
                  </p>
                ))}
              </div>
              <section className="review-workbench">
                <div>
                  <span className="field-name">HUMAN REVIEW</span>
                  <h2>Correct with an audit trail</h2>
                </div>
                <label>
                  Field
                  <select value={correctionPath} onChange={(event) => chooseCorrection(event.target.value)}>
                    <option value="">Choose a field</option>
                    {correctionTargets.map((target) => (
                      <option key={target.path} value={target.path}>{target.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Correct value
                  <input value={correctionValue} onChange={(event) => setCorrectionValue(event.target.value)} />
                </label>
                <label>
                  Reviewer
                  <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="Your name" />
                </label>
                <label>
                  Reason or review note
                  <textarea value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} placeholder="Why is this change correct?" />
                </label>
                <div className="review-actions">
                  <button disabled={savingReview || !correctionPath || !reviewer || reviewReason.length < 3} onClick={saveCorrection}>
                    Save correction
                  </button>
                  <button className="secondary" disabled={savingReview || !reviewer || reviewReason.length < 3 || result.review.unresolved_fields.length > 0} onClick={approveReview}>
                    Approve review
                  </button>
                </div>
                <button className="audit-toggle" onClick={() => loadEvents(result.document_id)}>
                  Refresh audit history
                </button>
                {events.length > 0 && (
                  <div className="audit-events">
                    {events.map((event) => (
                      <p key={event.event_id}>
                        <strong>r{event.revision} · {event.event_type.replaceAll("_", " ")}</strong>
                        <span>{event.field_path ?? "review"} · {event.reviewer}</span>
                        <span>{event.reason}</span>
                      </p>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
