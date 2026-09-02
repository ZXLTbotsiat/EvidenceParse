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
};

type ParseResult = {
  filename: string;
  source_kind: string;
  page_count: number;
  fields: Record<string, FieldResult>;
  validations: { code: string; passed?: boolean | null; message: string }[];
  warnings: string[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to parse document");
    } finally {
      setLoading(false);
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
                <span>{result.page_count} page{result.page_count === 1 ? "" : "s"}</span>
              </div>
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
                  {field.evidence[0] && (
                    <p className="evidence">Page {field.evidence[0].page} · “{field.evidence[0].text}”</p>
                  )}
                  {!field.evidence[0] && field.review_reason && (
                    <p className="evidence muted">{field.review_reason}</p>
                  )}
                </article>
              ))}
              <div className="validations">
                {result.validations.map((validation) => (
                  <p key={validation.code}>
                    <span>{validation.passed === true ? "✓" : validation.passed === false ? "!" : "?"}</span>
                    {validation.message}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

