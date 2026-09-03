import type { BatchItem, BatchJob } from "../lib/types";
import { useI18n } from "../lib/i18n";
import type { MessageKey } from "../lib/i18n-catalog";

const STATUS_KEYS: Record<string, MessageKey> = {
  queued: "status.queued", running: "status.running", completed: "status.completed",
  partial_failure: "status.partial_failure", failed: "status.failed", pending: "status.pending", processing: "status.processing",
};

type SourceProps = {
  selectedFiles: File[];
  batch: BatchJob | null;
};

export function BatchSourcePreview({ selectedFiles, batch }: SourceProps) {
  const { t } = useI18n();
  const isArchive = selectedFiles.length === 1 && selectedFiles[0].name.toLowerCase().endsWith(".zip");
  const names = batch?.items.map((item) => item.filename) ?? selectedFiles.map((file) => file.name);

  return (
    <div className="batch-source-preview">
      <div className="panel-title">
        <div><span className="kicker">{isArchive ? t("batch.archive") : t("batch.files")}</span><strong>{selectedFiles[0]?.name}</strong></div>
        <span className="page-badge">{batch ? t("batch.documents", { count: batch.total_items }) : t("batch.fileCount", { count: selectedFiles.length })}</span>
      </div>
      <div className="batch-source-body">
        <div className="archive-mark">{isArchive ? "ZIP" : names.length}</div>
        <strong>{batch ? t("batch.safe") : t("batch.ready")}</strong>
        <p>{isArchive ? t("batch.archiveHint") : t("batch.filesHint")}</p>
        <div className="batch-source-list">
          {names.map((name, index) => <span key={`${name}-${index}`} title={name}>{index + 1}. {name}</span>)}
        </div>
      </div>
    </div>
  );
}

type ResultsProps = {
  selectedFiles: File[];
  batch: BatchJob | null;
  openingItemId: string;
  onOpen: (item: BatchItem) => void;
};

export function BatchResults({ selectedFiles, batch, openingItemId, onOpen }: ResultsProps) {
  const { t } = useI18n();
  const finished = batch ? batch.completed_items + batch.failed_items : 0;
  const percentage = batch ? Math.round((finished / Math.max(batch.total_items, 1)) * 100) : 0;
  const pendingItems: BatchItem[] = selectedFiles.map((file, index) => ({
    item_id: `local-${index}`,
    position: index,
    filename: file.name,
    content_type: file.type,
    status: "pending",
  }));
  const items = batch?.items ?? pendingItems;

  return (
    <div className="batch-results">
      <div className="batch-summary">
        <div><span className="kicker">{t("batch.progress")}</span><strong>{batch ? t(STATUS_KEYS[batch.status] ?? "status.pending") : t("batch.waitingStart")}</strong></div>
        <span>{batch ? `${finished} / ${batch.total_items}` : t("batch.uploadItems", { count: selectedFiles.length })}</span>
      </div>
      <div className="batch-progress" aria-label={t("batch.progressAria", { percent: percentage })}><span style={{ width: `${percentage}%` }} /></div>
      <div className="batch-items">
        {items.map((item) => (
          <article className="batch-item" key={item.item_id}>
            <span className={`batch-index ${item.status}`}>{item.position + 1}</span>
            <div><strong title={item.filename}>{item.filename}</strong><small>{item.error ?? t(STATUS_KEYS[item.status] ?? "status.pending")}</small></div>
            {item.status === "completed" && item.document_id && (
              <button disabled={openingItemId === item.item_id} onClick={() => onOpen(item)}>
                {openingItemId === item.item_id ? t("batch.opening") : t("batch.open")}
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
