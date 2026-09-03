"use client";

import { ChangeEvent, DragEvent, useCallback, useEffect, useRef, useState } from "react";
import type { OcrTextBlock, PageContent } from "../lib/types";

type Props = {
  file: File | null;
  fileUrl: string;
  page: number;
  pageInfo?: PageContent;
  selectedBlock?: OcrTextBlock | null;
  onFilesSelect: (files: File[]) => void;
};

export function DocumentPreview({ file, fileUrl, page, pageInfo, selectedBlock, onFilesSelect }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [stageSize, setStageSize] = useState<{ width: number; height: number } | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const fitImage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imageSize.width || !imageSize.height) return;
    const availableWidth = Math.max(canvas.clientWidth - 32, 1);
    const availableHeight = Math.max(canvas.clientHeight - 32, 1);
    const scale = Math.min(availableWidth / imageSize.width, availableHeight / imageSize.height);
    setStageSize({ width: imageSize.width * scale, height: imageSize.height * scale });
  }, [imageSize]);

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
  }, [fileUrl]);

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
          aria-label="拖拽或点击上传文件"
        />
        <div
          className={`preview-empty drop-target ${dragActive ? "drag-active" : ""}`}
          aria-hidden="true"
        >
          <span className="drop-icon">↑</span>
          <strong>{dragActive ? "松开即可预览" : "拖拽文件到这里"}</strong>
          <p>也可以点击选择多个文档或 ZIP 压缩包</p>
          <small>文件先在本地预览，开始识别后才会发送到本机 OCR 服务。</small>
        </div>
      </div>
    );
  }

  if (!fileUrl) {
    return <div className="preview-empty"><strong>正在准备原文预览</strong></div>;
  }

  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  const canOverlay = !isPdf && pageInfo && selectedBlock?.bbox;
  const overlay = canOverlay ? {
    left: `${(selectedBlock.bbox.x0 / pageInfo.width) * 100}%`,
    top: `${(selectedBlock.bbox.y0 / pageInfo.height) * 100}%`,
    width: `${((selectedBlock.bbox.x1 - selectedBlock.bbox.x0) / pageInfo.width) * 100}%`,
    height: `${((selectedBlock.bbox.y1 - selectedBlock.bbox.y0) / pageInfo.height) * 100}%`,
  } : undefined;

  return (
    <div className="document-preview">
      <div className="panel-title">
        <div><span className="kicker">原始文件</span><strong title={file.name}>{file.name}</strong></div>
        <span className="page-badge">第 {page} 页</span>
      </div>
      <div className="preview-canvas" ref={canvasRef}>
        {isPdf ? (
          <iframe title="上传文件原文" src={`${fileUrl}#page=${page}&view=FitH`} />
        ) : (
          <div
            className="image-stage"
            style={stageSize ?? undefined}
          >
            {/* The image and overlay share one coordinate system, keeping OCR boxes auditable. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fileUrl}
              alt={`上传文件 ${file.name}`}
              onLoad={(event) => setImageSize({
                width: event.currentTarget.naturalWidth,
                height: event.currentTarget.naturalHeight,
              })}
            />
            {overlay && <span className="evidence-overlay" style={overlay} />}
          </div>
        )}
      </div>
      {selectedBlock && (
        <div className="selected-evidence">
          <span>当前对照</span><strong>{selectedBlock.text}</strong>
          <small>位置 {Math.round(selectedBlock.bbox.x0)}, {Math.round(selectedBlock.bbox.y0)}</small>
        </div>
      )}
    </div>
  );
}
