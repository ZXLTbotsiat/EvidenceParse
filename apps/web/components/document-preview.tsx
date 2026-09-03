import type { OcrTextBlock, PageContent } from "../lib/types";

type Props = {
  file: File | null;
  fileUrl: string;
  page: number;
  pageInfo?: PageContent;
  selectedBlock?: OcrTextBlock | null;
};

export function DocumentPreview({ file, fileUrl, page, pageInfo, selectedBlock }: Props) {
  if (!file) {
    return (
      <div className="preview-empty">
        <span>原文预览</span>
        <strong>选择文件后，原文会先显示在这里</strong>
        <p>文件只在当前浏览器中预览，不会因为预览额外上传。</p>
      </div>
    );
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
      <div className="preview-canvas">
        {isPdf ? (
          <iframe title="上传文件原文" src={`${fileUrl}#page=${page}&view=FitH`} />
        ) : (
          <div className="image-stage">
            {/* The image and overlay share one coordinate system, keeping OCR boxes auditable. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fileUrl} alt={`上传文件 ${file.name}`} />
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
