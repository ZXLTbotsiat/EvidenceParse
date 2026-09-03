import type { OcrTextBlock, PageContent } from "../lib/types";
import { useI18n } from "../lib/i18n";

type Props = {
  pages: PageContent[];
  blocks: OcrTextBlock[];
  page: number;
  selectedBlock: OcrTextBlock | null;
  onPageChange: (page: number) => void;
  onBlockSelect: (block: OcrTextBlock) => void;
};

export function OcrResults({ pages, blocks, page, selectedBlock, onPageChange, onBlockSelect }: Props) {
  const { t } = useI18n();
  const pageBlocks = blocks.filter((block) => block.page === page);
  return (
    <section className="ocr-results">
      <div className="page-tabs" aria-label={t("ocr.pages")}>
        {pages.map((item) => (
          <button key={item.page} className={item.page === page ? "active" : ""} onClick={() => onPageChange(item.page)}>
            {t("ocr.page", { page: item.page })}
          </button>
        ))}
      </div>
      <div className="ocr-page-summary">
        <strong>{t("ocr.summary", { count: pageBlocks.length })}</strong>
        <span>{t("ocr.hint")}</span>
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
        {pageBlocks.length === 0 && <p className="quiet-state">{t("ocr.empty")}</p>}
      </div>
    </section>
  );
}
