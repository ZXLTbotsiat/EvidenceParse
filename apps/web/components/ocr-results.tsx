import type { OcrTextBlock, PageContent } from "../lib/types";

type Props = {
  pages: PageContent[];
  blocks: OcrTextBlock[];
  page: number;
  selectedBlock: OcrTextBlock | null;
  onPageChange: (page: number) => void;
  onBlockSelect: (block: OcrTextBlock) => void;
};

export function OcrResults({ pages, blocks, page, selectedBlock, onPageChange, onBlockSelect }: Props) {
  const pageBlocks = blocks.filter((block) => block.page === page);
  return (
    <section className="ocr-results">
      <div className="page-tabs" aria-label="OCR 页码">
        {pages.map((item) => (
          <button key={item.page} className={item.page === page ? "active" : ""} onClick={() => onPageChange(item.page)}>
            第 {item.page} 页
          </button>
        ))}
      </div>
      <div className="ocr-page-summary">
        <strong>识别到 {pageBlocks.length} 个文本区域</strong>
        <span>点击文字区域，可与左侧原文定位对照</span>
      </div>
      <div className="text-blocks">
        {pageBlocks.map((block, index) => (
          <button
            className={`text-block ${selectedBlock === block ? "selected" : ""}`}
            key={`${block.page}-${block.bbox.x0}-${block.bbox.y0}-${index}`}
            onClick={() => onBlockSelect(block)}
          >
            <span>{block.text}</span><small>{Math.round(block.confidence * 100)}%</small>
          </button>
        ))}
        {pageBlocks.length === 0 && <p className="quiet-state">这一页没有识别到文字。</p>}
      </div>
    </section>
  );
}
