"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { DocumentPreview } from "../components/document-preview";
import { OcrResults } from "../components/ocr-results";
import { ReviewWorkbench } from "../components/review-workbench";
import { StructuredResults } from "../components/structured-results";
import { approveDocument, correctField, fetchReviewEvents, parseDocument } from "../lib/api";
import type { Evidence, OcrMode, OcrTextBlock, ParseResult, ReviewEvent } from "../lib/types";

const MODE_COPY = {
  generic: { title: "通用 OCR", description: "逐页文字、位置与置信度" },
  invoice: { title: "专业发票 OCR", description: "字段、明细与金额校验" },
};

const MAX_FILE_BYTES = 20 * 1024 * 1024;
const SUPPORTED_FILE = /\.(pdf|png|jpe?g)$/i;

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
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

  useEffect(() => {
    if (!file) { setFileUrl(""); return; }
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const correctionTargets = useMemo(() => result ? [
    ...Object.entries(result.fields).map(([name, field]) => ({ path: `fields.${name}`, label: name.replaceAll("_", " "), value: field.value ?? "" })),
    ...result.line_items.flatMap((item, index) =>
      (["description", "quantity", "unit_price", "tax_rate", "amount"] as const)
        .filter((name) => item[name] !== undefined)
        .map((name) => ({ path: `line_items.${index}.${name}`, label: `明细 ${item.index} · ${name.replaceAll("_", " ")}`, value: item[name]?.value ?? "" })),
    ),
  ] : [], [result]);

  function selectFile(nextFile: File) {
    if (!SUPPORTED_FILE.test(nextFile.name)) {
      setError("仅支持 PDF、JPG、JPEG 和 PNG 文件。");
      return;
    }
    if (nextFile.size > MAX_FILE_BYTES) {
      setError("文件不能超过 20 MB。");
      return;
    }
    setFile(nextFile);
    setResult(null); setSelectedBlock(null); setPage(1); setError("");
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (selected) selectFile(selected);
    event.target.value = "";
  }

  async function runOcr() {
    if (!file) return;
    setLoading(true); setError("");
    try {
      const payload = await parseDocument(file, mode, apiKey);
      setResult(payload);
      setResultTab(mode === "invoice" ? "professional" : "ocr");
      setPage(1); setSelectedBlock(null); setEvents([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "识别失败，请稍后重试。");
    } finally { setLoading(false); }
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
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={chooseFile} />
          <span>{file ? "更换文件" : "选择文件"}</span>
          <strong>{file?.name ?? "支持 PDF、JPG、PNG，最大 20 MB"}</strong>
        </label>
        <div className="mode-picker" aria-label="OCR 类型">
          {(Object.keys(MODE_COPY) as OcrMode[]).map((value) => (
            <button key={value} className={mode === value ? "active" : ""} onClick={() => setMode(value)}>
              <strong>{MODE_COPY[value].title}</strong><small>{MODE_COPY[value].description}</small>
            </button>
          ))}
        </div>
        <button className="primary-action" disabled={!file || loading} onClick={runOcr}>{loading ? "正在识别…" : "开始识别"}</button>
      </section>

      {error && <p className="error-banner">{error}</p>}

      <section className="comparison-workspace">
        <DocumentPreview file={file} fileUrl={fileUrl} page={page} pageInfo={result?.pages.find((item) => item.page === page)} selectedBlock={selectedBlock} onFileSelect={selectFile} />
        <div className="result-panel">
          <div className="panel-title result-title">
            <div><span className="kicker">识别结果</span><strong>{result ? MODE_COPY[result.schema_name].title : "等待识别"}</strong></div>
            {result && <span className="source-badge">{result.source_kind.replaceAll("_", " ")}</span>}
          </div>
          {!result ? (
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

      {result?.schema_name === "invoice" && <ReviewWorkbench result={result} events={events} targets={correctionTargets}
        correctionPath={correctionPath} correctionValue={correctionValue} reviewer={reviewer} reason={reviewReason} saving={savingReview}
        onPathChange={chooseCorrection} onValueChange={setCorrectionValue} onReviewerChange={setReviewer} onReasonChange={setReviewReason}
        onSave={saveCorrection} onApprove={approveReview} onRefreshEvents={loadEvents} />}
    </main>
  );
}
