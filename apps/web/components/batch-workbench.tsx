import type { BatchItem, BatchJob } from "../lib/types";

const STATUS_COPY = {
  queued: "等待执行",
  running: "正在识别",
  completed: "已完成",
  partial_failure: "部分完成",
  failed: "执行失败",
  pending: "等待",
  processing: "识别中",
};

type SourceProps = {
  selectedFiles: File[];
  batch: BatchJob | null;
};

export function BatchSourcePreview({ selectedFiles, batch }: SourceProps) {
  const isArchive = selectedFiles.length === 1 && selectedFiles[0].name.toLowerCase().endsWith(".zip");
  const names = batch?.items.map((item) => item.filename) ?? selectedFiles.map((file) => file.name);

  return (
    <div className="batch-source-preview">
      <div className="panel-title">
        <div><span className="kicker">{isArchive ? "ZIP 压缩包" : "批量文件"}</span><strong>{selectedFiles[0]?.name}</strong></div>
        <span className="page-badge">{batch ? `${batch.total_items} 个文档` : `${selectedFiles.length} 个文件`}</span>
      </div>
      <div className="batch-source-body">
        <div className="archive-mark">{isArchive ? "ZIP" : names.length}</div>
        <strong>{batch ? "已安全读取批次内容" : "文件已在本地就绪"}</strong>
        <p>{isArchive ? "压缩包只在内存中展开，不写入临时目录。" : "开始后将按文件顺序逐一识别。"}</p>
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
        <div><span className="kicker">批次进度</span><strong>{batch ? STATUS_COPY[batch.status] : "等待开始"}</strong></div>
        <span>{batch ? `${finished} / ${batch.total_items}` : `${selectedFiles.length} 个上传项`}</span>
      </div>
      <div className="batch-progress" aria-label={`批次进度 ${percentage}%`}><span style={{ width: `${percentage}%` }} /></div>
      <div className="batch-items">
        {items.map((item) => (
          <article className="batch-item" key={item.item_id}>
            <span className={`batch-index ${item.status}`}>{item.position + 1}</span>
            <div><strong title={item.filename}>{item.filename}</strong><small>{item.error ?? STATUS_COPY[item.status]}</small></div>
            {item.status === "completed" && item.document_id && (
              <button disabled={openingItemId === item.item_id} onClick={() => onOpen(item)}>
                {openingItemId === item.item_id ? "打开中…" : "查看结果"}
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
