"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { BatchResults, BatchSourcePreview } from "../components/batch-workbench";
import { DocumentPreview } from "../components/document-preview";
import { OcrResults } from "../components/ocr-results";
import { ReviewWorkbench } from "../components/review-workbench";
import { StructuredResults } from "../components/structured-results";
import { approveDocument, correctField, createBatch, fetchBatch, fetchDocument, fetchReviewEvents, parseDocument } from "../lib/api";
import { extractArchiveMember } from "../lib/archive";
import type { BatchItem, BatchJob, Evidence, OcrMode, OcrTextBlock, ParseResult, ReviewEvent } from "../lib/types";

const MODE_COPY = {
  generic: { title: "通用 OCR", description: "逐页文字、位置与置信度" },
  invoice: { title: "专业发票 OCR", description: "字段、明细与金额校验" },
};

const MAX_FILE_BYTES = 20 * 1024 * 1024;
const MAX_BATCH_BYTES = 100 * 1024 * 1024;
const MAX_BATCH_FILES = 20;
const SUPPORTED_FILE = /\.(pdf|png|jpe?g|zip)$/i;
const TERMINAL_BATCH_STATUSES = new Set(["completed", "partial_failure", "failed"]);

export default function Home() {
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
        if (!cancelled) setError(caught instanceof Error ? caught.message : "批次状态查询失败。");
      }
    }

    timer = setTimeout(poll, 500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [batch?.batch_id, apiKey]);

  const correctionTargets = useMemo(() => result ? [
    ...Object.entries(result.fields).map(([name, field]) => ({ path: `fields.${name}`, label: name.replaceAll("_", " "), value: field.value ?? "" })),
    ...result.line_items.flatMap((item, index) =>
      (["description", "quantity", "unit_price", "tax_rate", "amount"] as const)
        .filter((name) => item[name] !== undefined)
        .map((name) => ({ path: `line_items.${index}.${name}`, label: `明细 ${item.index} · ${name.replaceAll("_", " ")}`, value: item[name]?.value ?? "" })),
    ),
  ] : [], [result]);

  const isBatchSelection = selectedFiles.length > 1 || Boolean(selectedFiles[0]?.name.toLowerCase().endsWith(".zip"));
  const batchRunning = batch?.status === "queued" || batch?.status === "running";

  function selectFiles(nextFiles: File[]) {
    if (!nextFiles.length) return;
    if (nextFiles.length > MAX_BATCH_FILES) {
      setError(`一次最多选择 ${MAX_BATCH_FILES} 个文件。`);
      return;
    }
    const archives = nextFiles.filter((item) => item.name.toLowerCase().endsWith(".zip"));
    if (archives.length && nextFiles.length > 1) {
      setError("ZIP 压缩包请单独上传，普通文档可以一次选择多个。");
      return;
    }
    const unsupported = nextFiles.find((item) => !SUPPORTED_FILE.test(item.name));
    if (unsupported) {
      setError(`${unsupported.name} 不受支持，仅支持 PDF、JPG、PNG 和 ZIP。`);
      return;
    }
    const oversized = nextFiles.find((item) => item.size > (item.name.toLowerCase().endsWith(".zip") ? MAX_BATCH_BYTES : MAX_FILE_BYTES));
    if (oversized) {
      setError(`${oversized.name} 超过大小限制。单个文档最大 20 MB，ZIP 最大 100 MB。`);
      return;
    }
    if (nextFiles.reduce((total, item) => total + item.size, 0) > MAX_BATCH_BYTES) {
      setError("本批文件总大小不能超过 100 MB。");
      return;
    }
    const previewFile = nextFiles.length === 1 && !archives.length ? nextFiles[0] : null;
    setSelectedFiles(nextFiles);
    setFile(previewFile);
    setBatch(null); setViewingBatchItem(false); setOpeningItemId("");
    setResult(null); setSelectedBlock(null); setPage(1); setError("");
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
      } else if (file) {
        const payload = await parseDocument(file, mode, apiKey);
        setResult(payload);
        setResultTab(mode === "invoice" ? "professional" : "ocr");
        setPage(1); setSelectedBlock(null); setEvents([]);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "识别失败，请稍后重试。");
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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法打开批次结果。");
    } finally { setOpeningItemId(""); }
  }

  function selectEvidence(evidence: Evidence) {
    if (!result || !evidence.bbox) return;
    const matching = result.text_blocks.find((block) => block.page === evidence.page && block.text.includes(evidence.text));
    setPage(evidence.page);
    setSelectedBlock(matching ?? { ...evidence, bbox: evidence.bbox, confidence: 1 });
    setResultTab("ocr");
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
    } catch (caught) { setError(caught instanceof Error ? caught.message : "保存更正失败。"); }
    finally { setSavingReview(false); }
  }

  async function approveReview() {
    if (!result) return;
    setSavingReview(true);
    try {
      const payload = await approveDocument(result.document_id, apiKey, reviewer, reviewReason, result.review.revision);
      setResult(payload); setReviewReason("");
      setEvents(await fetchReviewEvents(payload.document_id, apiKey));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "批准复核失败。"); }
    finally { setSavingReview(false); }
  }

  return (
    <main>
      <header className="app-header">
        <div className="brand-mark">EP</div>
        <div><h1>EvidenceParse</h1><p>让每一项识别结果，都能回到原文核对。</p></div>
        <div className="header-actions">
          <details className="api-key"><summary>API Key</summary><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" placeholder="本地模式可不填" /></details>
          <span className="local-badge">本地 OCR · 文件不外传</span>
        </div>
      </header>

      <section className="control-bar">
        <label className="file-picker">
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.zip" multiple disabled={batchRunning} onChange={chooseFile} />
          <span>{selectedFiles.length ? "更换文件" : "选择文件"}</span>
          <strong>{selectedFiles.length > 1 ? `已选择 ${selectedFiles.length} 个文件` : selectedFiles[0]?.name ?? "支持多选文档或单个 ZIP"}</strong>
        </label>
        <div className="mode-picker" aria-label="OCR 类型">
          {(Object.keys(MODE_COPY) as OcrMode[]).map((value) => (
            <button key={value} className={mode === value ? "active" : ""} disabled={batchRunning} onClick={() => setMode(value)}>
              <strong>{MODE_COPY[value].title}</strong><small>{MODE_COPY[value].description}</small>
            </button>
          ))}
        </div>
        <button className="primary-action" disabled={!selectedFiles.length || loading || batchRunning} onClick={runOcr}>{loading ? "正在创建…" : batchRunning ? "批量识别中…" : isBatchSelection ? "批量识别" : "开始识别"}</button>
      </section>

      {error && <p className="error-banner">{error}</p>}

      <section className="comparison-workspace">
        {isBatchSelection && (!viewingBatchItem || !file) ? (
          <BatchSourcePreview selectedFiles={selectedFiles} batch={batch} />
        ) : (
          <DocumentPreview file={file} fileUrl={fileUrl} page={page} pageInfo={result?.pages.find((item) => item.page === page)} selectedBlock={selectedBlock} onFilesSelect={selectFiles} />
        )}
        <div className="result-panel">
          <div className="panel-title result-title">
            <div><span className="kicker">识别结果</span><strong>{isBatchSelection && !viewingBatchItem ? "批量任务" : result ? MODE_COPY[result.schema_name].title : "等待识别"}</strong></div>
            <div className="result-heading-actions">
              {isBatchSelection && viewingBatchItem && <button className="batch-back" onClick={() => setViewingBatchItem(false)}>返回批次</button>}
              {result && (!isBatchSelection || viewingBatchItem) && <span className="source-badge">{result.source_kind.replaceAll("_", " ")}</span>}
            </div>
          </div>
          {isBatchSelection && !viewingBatchItem ? (
            <BatchResults selectedFiles={selectedFiles} batch={batch} openingItemId={openingItemId} onOpen={openBatchItem} />
          ) : !result ? (
            <div className="result-empty"><span>01</span><p>先在左侧确认文件内容，再选择通用或专业 OCR。</p><span>02</span><p>识别后点击任意文字区域，即可与原文定位对照。</p></div>
          ) : (
            <>
              {result.schema_name === "invoice" && <div className="result-tabs">
                <button className={resultTab === "ocr" ? "active" : ""} onClick={() => setResultTab("ocr")}>OCR 全文</button>
                <button className={resultTab === "professional" ? "active" : ""} onClick={() => setResultTab("professional")}>专业字段</button>
              </div>}
              {resultTab === "ocr" ? (
                <OcrResults pages={result.pages} blocks={result.text_blocks} page={page} selectedBlock={selectedBlock}
                  onPageChange={(nextPage) => { setPage(nextPage); setSelectedBlock(null); }}
                  onBlockSelect={(block) => { setPage(block.page); setSelectedBlock(block); }} />
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
