"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { BatchResults, BatchSourcePreview } from "../components/batch-workbench";
import { DocumentPreview } from "../components/document-preview";
import { OcrResults } from "../components/ocr-results";
import { ReviewWorkbench } from "../components/review-workbench";
import { StructuredResults } from "../components/structured-results";
import { approveDocument, correctField, createBatch, fetchBatch, fetchDocument, fetchReviewEvents, parseDocument } from "../lib/api";
import { extractArchiveMember } from "../lib/archive";
import { useI18n } from "../lib/i18n";
import type { Language, MessageKey } from "../lib/i18n-catalog";
import type { BatchItem, BatchJob, Evidence, OcrMode, OcrTextBlock, ParseResult, ReviewEvent } from "../lib/types";

const MAX_FILE_BYTES = 20 * 1024 * 1024;
const MAX_BATCH_BYTES = 100 * 1024 * 1024;
const MAX_BATCH_FILES = 20;
const SUPPORTED_FILE = /\.(pdf|png|jpe?g|zip)$/i;
const TERMINAL_BATCH_STATUSES = new Set(["completed", "partial_failure", "failed"]);
const FIELD_KEYS: Record<string, MessageKey> = {
  invoice_number: "field.invoice_number", invoice_date: "field.invoice_date", subtotal: "field.subtotal", tax: "field.tax", total: "field.total",
};
const LINE_ITEM_FIELD_KEYS = {
  description: "field.description", quantity: "field.quantity", unit_price: "field.unit_price", tax_rate: "field.tax_rate", amount: "field.amount",
} as const satisfies Record<string, MessageKey>;

export default function Home() {
  const { language, languages, setLanguage, t } = useI18n();
  const modeCopy = {
    generic: { title: t("mode.generic"), description: t("mode.genericDescription") },
    invoice: { title: t("mode.invoice"), description: t("mode.invoiceDescription") },
  };
  const [file, setFile] = useState<File | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileUrl, setFileUrl] = useState("");
  const [mode, setMode] = useState<OcrMode>("generic");
  const [result, setResult] = useState<ParseResult | null>(null);
  const [resultTab, setResultTab] = useState<"ocr" | "professional">("ocr");
  const [page, setPage] = useState(1);
  const [selectedBlock, setSelectedBlock] = useState<OcrTextBlock | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [correctionPath, setCorrectionPath] = useState("");
  const [correctionValue, setCorrectionValue] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [batch, setBatch] = useState<BatchJob | null>(null);
  const [viewingBatchItem, setViewingBatchItem] = useState(false);
  const [openingItemId, setOpeningItemId] = useState("");
  const [mobilePane, setMobilePane] = useState<"source" | "results">("source");

  useEffect(() => {
    if (!file) { setFileUrl(""); return; }
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    const batchId = batch?.batch_id;
    if (!batchId || (batch && TERMINAL_BATCH_STATUSES.has(batch.status))) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const latest = await fetchBatch(batchId!, apiKey);
        if (cancelled) return;
        setBatch(latest);
        if (!TERMINAL_BATCH_STATUSES.has(latest.status)) timer = setTimeout(poll, 700);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : t("error.batchFetch"));
      }
    }

    timer = setTimeout(poll, 500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [batch?.batch_id, apiKey, t]);

  const correctionTargets = useMemo(() => result ? [
    ...Object.entries(result.fields).map(([name, field]) => ({ path: `fields.${name}`, label: FIELD_KEYS[name] ? t(FIELD_KEYS[name]) : name.replaceAll("_", " "), value: field.value ?? "" })),
    ...result.line_items.flatMap((item, index) =>
      (["description", "quantity", "unit_price", "tax_rate", "amount"] as const)
        .filter((name) => item[name] !== undefined)
        .map((name) => ({ path: `line_items.${index}.${name}`, label: t("field.lineItem", { index: item.index, field: t(LINE_ITEM_FIELD_KEYS[name]) }), value: item[name]?.value ?? "" })),
    ),
  ] : [], [result, t]);

  const isBatchSelection = selectedFiles.length > 1 || Boolean(selectedFiles[0]?.name.toLowerCase().endsWith(".zip"));
  const batchRunning = batch?.status === "queued" || batch?.status === "running";

  function selectFiles(nextFiles: File[]) {
    if (!nextFiles.length) return;
    if (nextFiles.length > MAX_BATCH_FILES) {
      setError(t("error.tooMany", { count: MAX_BATCH_FILES }));
      return;
    }
    const archives = nextFiles.filter((item) => item.name.toLowerCase().endsWith(".zip"));
    if (archives.length && nextFiles.length > 1) {
      setError(t("error.archiveSingle"));
      return;
    }
    const unsupported = nextFiles.find((item) => !SUPPORTED_FILE.test(item.name));
    if (unsupported) {
      setError(t("error.unsupported", { name: unsupported.name }));
      return;
    }
    const oversized = nextFiles.find((item) => item.size > (item.name.toLowerCase().endsWith(".zip") ? MAX_BATCH_BYTES : MAX_FILE_BYTES));
    if (oversized) {
      setError(t("error.tooLarge", { name: oversized.name }));
      return;
    }
    if (nextFiles.reduce((total, item) => total + item.size, 0) > MAX_BATCH_BYTES) {
      setError(t("error.batchTooLarge"));
      return;
    }
    const previewFile = nextFiles.length === 1 && !archives.length ? nextFiles[0] : null;
    setSelectedFiles(nextFiles);
    setFile(previewFile);
    setBatch(null); setViewingBatchItem(false); setOpeningItemId("");
    setResult(null); setSelectedBlock(null); setPage(1); setError("");
    setMobilePane("source");
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    if (selected.length) selectFiles(selected);
    event.target.value = "";
  }

  async function runOcr() {
    if (!selectedFiles.length) return;
    setLoading(true); setError("");
    try {
      if (isBatchSelection) {
        const payload = await createBatch(selectedFiles, mode, apiKey);
        setBatch(payload); setViewingBatchItem(false); setResult(null);
        setMobilePane("results");
      } else if (file) {
        const payload = await parseDocument(file, mode, apiKey);
        setResult(payload);
        setResultTab(mode === "invoice" ? "professional" : "ocr");
        setPage(1); setSelectedBlock(null); setEvents([]);
        setMobilePane("results");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("error.ocr"));
    } finally { setLoading(false); }
  }

  async function openBatchItem(item: BatchItem) {
    if (!item.document_id) return;
    setOpeningItemId(item.item_id); setError("");
    try {
      const payload = await fetchDocument(item.document_id, apiKey);
      let previewFile = selectedFiles.find((candidate) => candidate.name === item.filename) ?? null;
      const archive = selectedFiles.length === 1 && selectedFiles[0].name.toLowerCase().endsWith(".zip") ? selectedFiles[0] : null;
      if (!previewFile && archive) previewFile = await extractArchiveMember(archive, item.filename);
      setResult(payload); setViewingBatchItem(true);
      setResultTab(payload.schema_name === "invoice" ? "professional" : "ocr");
      setFile(previewFile);
      setPage(1); setSelectedBlock(null); setEvents([]);
      setMobilePane("results");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("error.openBatch"));
    } finally { setOpeningItemId(""); }
  }

  function selectEvidence(evidence: Evidence) {
    if (!result || !evidence.bbox) return;
    const matching = result.text_blocks.find((block) => block.page === evidence.page && block.text.includes(evidence.text));
    setPage(evidence.page);
    setSelectedBlock(matching ?? { ...evidence, bbox: evidence.bbox, confidence: 1 });
    setResultTab("ocr");
    setMobilePane("source");
  }

  function chooseCorrection(path: string) {
    setCorrectionPath(path);
    setCorrectionValue(correctionTargets.find((target) => target.path === path)?.value ?? "");
  }

  async function loadEvents() {
    if (result) setEvents(await fetchReviewEvents(result.document_id, apiKey));
  }

  async function saveCorrection() {
    if (!result || !correctionPath) return;
    setSavingReview(true);
    try {
      const payload = await correctField(result.document_id, apiKey, {
        field_path: correctionPath, value: correctionValue || null, reason: reviewReason,
        reviewer, expected_revision: result.review.revision,
      });
      setResult(payload); setReviewReason("");
      setEvents(await fetchReviewEvents(payload.document_id, apiKey));
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("error.save")); }
    finally { setSavingReview(false); }
  }

  async function approveReview() {
    if (!result) return;
    setSavingReview(true);
    try {
      const payload = await approveDocument(result.document_id, apiKey, reviewer, reviewReason, result.review.revision);
      setResult(payload); setReviewReason("");
      setEvents(await fetchReviewEvents(payload.document_id, apiKey));
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("error.approve")); }
    finally { setSavingReview(false); }
  }

  return (
    <main>
      <header className="app-header">
        <div className="brand-mark">EP</div>
        <div><h1>EvidenceParse</h1><p>{t("app.tagline")}</p></div>
        <div className="header-actions">
          <label className="language-picker">
            <span>{t("language.label")}</span>
            <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
              {languages.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
            </select>
          </label>
          <details className="api-key"><summary>API Key</summary><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" placeholder={t("api.placeholder")} /></details>
          <span className="local-badge">{t("app.localBadge")}</span>
        </div>
      </header>

      <section className="control-bar">
        <label className="file-picker">
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.zip" multiple disabled={batchRunning} onChange={chooseFile} />
          <span>{selectedFiles.length ? t("file.change") : t("file.select")}</span>
          <strong>{selectedFiles.length > 1 ? t("file.selected", { count: selectedFiles.length }) : selectedFiles[0]?.name ?? t("file.support")}</strong>
        </label>
        <div className="mode-picker" aria-label={t("mode.label")}>
          {(Object.keys(modeCopy) as OcrMode[]).map((value) => (
            <button key={value} className={mode === value ? "active" : ""} disabled={batchRunning} onClick={() => setMode(value)}>
              <strong>{modeCopy[value].title}</strong><small>{modeCopy[value].description}</small>
            </button>
          ))}
        </div>
        <button className="primary-action" disabled={!selectedFiles.length || loading || batchRunning} onClick={runOcr}>{loading ? t("action.creating") : batchRunning ? t("action.batchRunning") : isBatchSelection ? t("action.batch") : t("action.start")}</button>
      </section>

      {error && <p className="error-banner" role="alert">{error}</p>}

      <nav className="mobile-pane-switcher" aria-label={t("view.label")}>
        <button className={mobilePane === "source" ? "active" : ""} onClick={() => setMobilePane("source")}>{t("view.source")}</button>
        <button className={mobilePane === "results" ? "active" : ""} onClick={() => setMobilePane("results")}>{t("view.results")}{result && <span aria-hidden="true" />}</button>
      </nav>

      <section className={`comparison-workspace mobile-pane-${mobilePane}`}>
        {isBatchSelection && (!viewingBatchItem || !file) ? (
          <BatchSourcePreview selectedFiles={selectedFiles} batch={batch} />
        ) : (
          <DocumentPreview file={file} fileUrl={fileUrl} page={page} pageInfo={result?.pages.find((item) => item.page === page)} selectedBlock={selectedBlock} preprocessing={result?.preprocessing.find((item) => item.page === page)} apiKey={apiKey} onFilesSelect={selectFiles} />
        )}
        <div className="result-panel">
          <div className="panel-title result-title">
            <div><span className="kicker">{t("result.title")}</span><strong>{isBatchSelection && !viewingBatchItem ? t("result.batch") : result ? modeCopy[result.schema_name].title : t("result.waiting")}</strong></div>
            <div className="result-heading-actions">
              {isBatchSelection && viewingBatchItem && <button className="batch-back" onClick={() => { setViewingBatchItem(false); setMobilePane("results"); }}>{t("result.back")}</button>}
              {result && (!isBatchSelection || viewingBatchItem) && <span className="source-badge">{result.source_kind.replaceAll("_", " ")}</span>}
            </div>
          </div>
          {isBatchSelection && !viewingBatchItem ? (
            <BatchResults selectedFiles={selectedFiles} batch={batch} openingItemId={openingItemId} onOpen={openBatchItem} />
          ) : !result ? (
            <div className="result-empty"><span>01</span><p>{t("empty.first")}</p><span>02</span><p>{t("empty.second")}</p></div>
          ) : (
            <>
              {result.schema_name === "invoice" && <div className="result-tabs">
                <button className={resultTab === "ocr" ? "active" : ""} onClick={() => setResultTab("ocr")}>{t("result.ocrText")}</button>
                <button className={resultTab === "professional" ? "active" : ""} onClick={() => setResultTab("professional")}>{t("result.fields")}</button>
              </div>}
              {resultTab === "ocr" ? (
                <OcrResults pages={result.pages} blocks={result.text_blocks} page={page} selectedBlock={selectedBlock}
                  onPageChange={(nextPage) => { setPage(nextPage); setSelectedBlock(null); }}
                  onBlockSelect={(block) => { setPage(block.page); setSelectedBlock(block); setMobilePane("source"); }} />
              ) : <StructuredResults result={result} onEvidenceSelect={selectEvidence} />}
            </>
          )}
        </div>
      </section>

      {result?.schema_name === "invoice" && (!isBatchSelection || viewingBatchItem) && <ReviewWorkbench result={result} events={events} targets={correctionTargets}
        correctionPath={correctionPath} correctionValue={correctionValue} reviewer={reviewer} reason={reviewReason} saving={savingReview}
        onPathChange={chooseCorrection} onValueChange={setCorrectionValue} onReviewerChange={setReviewer} onReasonChange={setReviewReason}
        onSave={saveCorrection} onApprove={approveReview} onRefreshEvents={loadEvents} />}
    </main>
  );
}
