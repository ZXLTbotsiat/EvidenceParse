"use client";

import { ChangeEvent, DragEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { renderOcrPage, renderPdfPage } from "../lib/api";
import { useI18n } from "../lib/i18n";
import type { MessageKey } from "../lib/i18n-catalog";
import type { OcrTextBlock, PageContent, PreprocessingCandidate, PreprocessingPage } from "../lib/types";

const VARIANT_KEYS: Record<PreprocessingPage["variant"], MessageKey> = {
  original: "preview.variant.original",
  enhanced: "preview.variant.enhanced",
  binary: "preview.variant.binary",
};

type CandidateView = PreprocessingCandidate["variant"] | "selected";

const CANDIDATE_VIEW_KEYS: Record<CandidateView, MessageKey> = {
  original: "preview.candidate.original",
  enhanced: "preview.candidate.enhanced",
  binary: "preview.candidate.binary",
  selected: "preview.candidate.selected",
};

type Props = {
  file: File | null;
  fileUrl: string;
  page: number;
  pageInfo?: PageContent;
  selectedBlock?: OcrTextBlock | null;
  pageBlocks?: OcrTextBlock[];
  preprocessing?: PreprocessingPage;
  sourceKind?: string;
  apiKey: string;
  onFilesSelect: (files: File[]) => void;
};

export function DocumentPreview({ file, fileUrl, page, pageInfo, selectedBlock, pageBlocks = [], preprocessing, sourceKind, apiKey, onFilesSelect }: Props) {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLSpanElement>(null);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [stageSize, setStageSize] = useState<{ width: number; height: number } | null>(null);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState("");
  const [pdfError, setPdfError] = useState("");
  const [ocrPreviewUrl, setOcrPreviewUrl] = useState("");
  const [ocrPreviewError, setOcrPreviewError] = useState("");
  const [previewMode, setPreviewMode] = useState<"source" | "ocr" | "textLayer">("source");
  const [candidateView, setCandidateView] = useState<CandidateView>("selected");
  const [dragActive, setDragActive] = useState(false);
  const isPdf = Boolean(file && (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")));

  const fitImage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imageSize.width || !imageSize.height) return;
    const availableWidth = Math.max(canvas.clientWidth - 32, 1);
    const availableHeight = Math.max(canvas.clientHeight - 32, 1);
    // PDF pages fit the available width and may scroll vertically. This keeps text
    // readable while allowing a selected OCR box to be brought into the viewport.
    const scale = isPdf
      ? Math.min(availableWidth / imageSize.width, 2)
      : Math.min(availableWidth / imageSize.width, availableHeight / imageSize.height);
    setStageSize({ width: imageSize.width * scale, height: imageSize.height * scale });
  }, [imageSize, isPdf]);

  useEffect(() => {
    fitImage();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const observer = new ResizeObserver(fitImage);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [fitImage]);

  useEffect(() => {
    setImageSize({ width: 0, height: 0 });
    setStageSize(null);
    setPreviewMode("source");
    setCandidateView("selected");
  }, [fileUrl, page]);

  const { candidates, selectedCandidate } = useMemo(() => {
    const fallback: PreprocessingCandidate | undefined = preprocessing ? {
      variant: preprocessing.variant,
      rotation_degrees: preprocessing.rotation_degrees,
      deskew_degrees: preprocessing.deskew_degrees,
      average_confidence: preprocessing.average_confidence,
      quality_score: preprocessing.average_confidence,
      text_region_count: pageBlocks.length,
      character_count: pageBlocks.reduce((total, block) => total + block.text.replace(/\s/g, "").length, 0),
      selected: true,
    } : undefined;
    const available = preprocessing?.candidates?.length ? preprocessing.candidates : (fallback ? [fallback] : []);
    return {
      candidates: available,
      selectedCandidate: available.find((candidate) => candidate.selected) ?? fallback,
    };
  }, [pageBlocks, preprocessing]);
  const activeCandidate = candidateView === "selected"
    ? selectedCandidate
    : candidates.find((candidate) => candidate.variant === candidateView) ?? selectedCandidate;

  useEffect(() => {
    if (!isPdf || !file) {
      setPdfPreviewUrl("");
      setPdfError("");
      return;
    }

    let cancelled = false;
    let previewUrl = "";

    async function loadPdfPage() {
      try {
        setPdfPreviewUrl("");
        setPdfError("");
        const preview = await renderPdfPage(file!, page, apiKey);
        if (cancelled) return;
        previewUrl = URL.createObjectURL(preview);
        setPdfPreviewUrl(previewUrl);
      } catch {
        if (!cancelled) setPdfError(t("preview.pdfError"));
      }
    }

    void loadPdfPage();
    return () => {
      cancelled = true;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [apiKey, file, isPdf, page, t]);

  useEffect(() => {
    if (previewMode !== "ocr" || !file || !activeCandidate) return;
    let cancelled = false;
    let previewUrl = "";

    async function loadOcrPreview() {
      try {
        setOcrPreviewUrl("");
        setOcrPreviewError("");
        const preview = await renderOcrPage(
          file!,
          { ...activeCandidate!, page: preprocessing!.page },
          apiKey,
        );
        if (cancelled) return;
        previewUrl = URL.createObjectURL(preview);
        setOcrPreviewUrl(previewUrl);
      } catch {
        if (!cancelled) setOcrPreviewError(t("preview.ocrError"));
      }
    }

    void loadOcrPreview();
    return () => {
      cancelled = true;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [activeCandidate, apiKey, file, preprocessing, previewMode, t]);

  useEffect(() => {
    if (!selectedBlock || !stageSize) return;
    const frame = requestAnimationFrame(() => {
      overlayRef.current?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    });
    return () => cancelAnimationFrame(frame);
  }, [page, selectedBlock, stageSize]);

  function acceptInput(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.currentTarget.files ?? []);
    if (selected.length) onFilesSelect(selected);
    event.currentTarget.value = "";
  }

  function acceptDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    const dropped = Array.from(event.dataTransfer.files);
    if (dropped.length) onFilesSelect(dropped);
  }

  if (!file) {
    return (
      <div
        className="preview-empty-shell"
        onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
        onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={acceptDrop}
      >
        <input
          id="source-drop-input"
          className="drop-input"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.zip"
          multiple
          onChange={acceptInput}
          aria-label={t("preview.uploadLabel")}
        />
        <div
          className={`preview-empty drop-target ${dragActive ? "drag-active" : ""}`}
          aria-hidden="true"
        >
          <span className="drop-icon">↑</span>
          <strong>{dragActive ? t("preview.release") : t("preview.drop")}</strong>
          <p>{t("preview.click")}</p>
          <small>{t("preview.private")}</small>
        </div>
      </div>
    );
  }

  if (!fileUrl) {
    return <div className="preview-empty"><strong>{t("preview.preparing")}</strong></div>;
  }

  const canOverlay = pageInfo && selectedBlock?.bbox;
  const overlay = canOverlay ? {
    left: `${(selectedBlock.bbox.x0 / pageInfo.width) * 100}%`,
    top: `${(selectedBlock.bbox.y0 / pageInfo.height) * 100}%`,
    width: `${((selectedBlock.bbox.x1 - selectedBlock.bbox.x0) / pageInfo.width) * 100}%`,
    height: `${((selectedBlock.bbox.y1 - selectedBlock.bbox.y0) / pageInfo.height) * 100}%`,
  } : undefined;
  const processingMode = preprocessing ? "ocr" : sourceKind === "digital_pdf" ? "textLayer" : null;
  const processingViewOpen = previewMode !== "source";
  const headingKey = previewMode === "ocr"
    ? "preview.ocrView"
    : previewMode === "textLayer" ? "preview.textLayerView" : "preview.original";

  return (
    <div className="document-preview">
      <div className="panel-title">
        <div><span className="kicker">{t(headingKey)}</span><strong title={file.name}>{file.name}</strong></div>
        <div className="preview-heading-actions">
          {processingMode && (
            <button
              className={`ocr-preview-toggle ${processingViewOpen ? "active" : ""}`}
              onClick={() => setPreviewMode((current) => current === "source" ? processingMode : "source")}
            >
              {processingViewOpen ? t("preview.showOriginal") : t("preview.showProcessing")}
            </button>
          )}
          <span className="page-badge">{t("preview.page", { page })}</span>
        </div>
      </div>
      {previewMode === "ocr" && preprocessing && (
        <div className="candidate-tabs" role="tablist" aria-label={t("preview.candidateTabs")}>
          {(Object.keys(CANDIDATE_VIEW_KEYS) as CandidateView[]).map((view) => {
            const candidate = view === "selected"
              ? selectedCandidate
              : candidates.find((item) => item.variant === view);
            return (
              <button
                key={view}
                role="tab"
                aria-selected={candidateView === view}
                className={candidateView === view ? "active" : ""}
                disabled={!candidate}
                onClick={() => setCandidateView(view)}
              >
                <span>{t(CANDIDATE_VIEW_KEYS[view])}</span>
                {candidate?.selected && <small>{t("preview.selectedBadge")}</small>}
              </button>
            );
          })}
        </div>
      )}
      <div className="preview-canvas" ref={canvasRef}>
        {previewMode === "ocr" ? (
          ocrPreviewError ? <div className="preview-load-state">{ocrPreviewError}</div> : (
            ocrPreviewUrl ? (
              <div className="document-stage image-stage ocr-input-stage" style={stageSize ?? undefined}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={ocrPreviewUrl}
                  alt={t("preview.ocrAlt", { page })}
                  onLoad={(event) => setImageSize({
                    width: event.currentTarget.naturalWidth,
                    height: event.currentTarget.naturalHeight,
                  })}
                />
              </div>
            ) : <span className="pdf-loading-inline">{t("preview.ocrRendering")}</span>
          )
        ) : isPdf ? (
          pdfError ? <div className="preview-load-state">{pdfError}</div> : (
            pdfPreviewUrl ? (
              <div className="document-stage image-stage" style={stageSize ?? undefined}>
                {/* The local API raster keeps scanned and digital PDFs in one auditable coordinate space. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={pdfPreviewUrl}
                  alt={t("preview.pdfAlt", { page })}
                  onLoad={(event) => setImageSize({
                    width: event.currentTarget.naturalWidth,
                    height: event.currentTarget.naturalHeight,
                  })}
                />
                {previewMode === "textLayer" && pageInfo && pageBlocks.map((block, index) => (
                  <span
                    className="text-layer-overlay"
                    key={`${block.page}-${index}-${block.text}`}
                    style={{
                      left: `${(block.bbox.x0 / pageInfo.width) * 100}%`,
                      top: `${(block.bbox.y0 / pageInfo.height) * 100}%`,
                      width: `${((block.bbox.x1 - block.bbox.x0) / pageInfo.width) * 100}%`,
                      height: `${((block.bbox.y1 - block.bbox.y0) / pageInfo.height) * 100}%`,
                    }}
                  />
                ))}
                {overlay && <span ref={overlayRef} className="evidence-overlay" style={overlay} />}
              </div>
            ) : <span className="pdf-loading-inline">{t("preview.rendering", { page })}</span>
          )
        ) : (
          <div
            className="document-stage image-stage"
            style={stageSize ?? undefined}
          >
            {/* The image and overlay share one coordinate system, keeping OCR boxes auditable. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fileUrl}
              alt={t("preview.imageAlt", { name: file.name })}
              onLoad={(event) => setImageSize({
                width: event.currentTarget.naturalWidth,
                height: event.currentTarget.naturalHeight,
              })}
            />
            {overlay && <span ref={overlayRef} className="evidence-overlay" style={overlay} />}
          </div>
        )}
      </div>
      {previewMode === "ocr" && preprocessing && (
        <div className="preprocessing-note">
          <div><span>{t("preview.ocrView")}</span><strong>{activeCandidate ? t(VARIANT_KEYS[activeCandidate.variant]) : t(VARIANT_KEYS[preprocessing.variant])}</strong></div>
          <small>{activeCandidate ? t("preview.candidateMetrics", {
            confidence: Math.round(activeCandidate.average_confidence * 100),
            score: activeCandidate.quality_score.toFixed(3),
            regions: activeCandidate.text_region_count,
            characters: activeCandidate.character_count,
          }) : t("preview.recipe", {
            rotation: preprocessing.rotation_degrees,
            deskew: preprocessing.deskew_degrees.toFixed(1),
            confidence: Math.round(preprocessing.average_confidence * 100),
          })}</small>
          {activeCandidate && <small>{t("preview.geometry", {
            rotation: activeCandidate.rotation_degrees,
            deskew: activeCandidate.deskew_degrees.toFixed(1),
          })}</small>}
        </div>
      )}
      {previewMode === "textLayer" && (
        <div className="preprocessing-note text-layer-note">
          <div><span>{t("preview.textLayerView")}</span><strong>{t("preview.textLayerDirect")}</strong></div>
          <small>{t("preview.textLayerHint", { count: pageBlocks.length })}</small>
        </div>
      )}
      {selectedBlock && (
        <div className="selected-evidence">
          <span>{t("preview.current")}</span><strong>{selectedBlock.text}</strong>
          <small>{t("preview.position", { x: Math.round(selectedBlock.bbox.x0), y: Math.round(selectedBlock.bbox.y0) })}</small>
        </div>
      )}
    </div>
  );
}
