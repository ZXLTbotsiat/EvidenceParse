export type BoundingBox = { x0: number; y0: number; x1: number; y1: number };

export type Evidence = { page: number; text: string; bbox?: BoundingBox | null };

export type OcrTextBlock = {
  page: number;
  text: string;
  bbox: BoundingBox;
  confidence: number;
};

export type PageContent = { page: number; width: number; height: number; text: string };

export type FieldResult = {
  value?: string | null;
  confidence: number;
  evidence: Evidence[];
  review_required: boolean;
  review_reason?: string | null;
  source: "extracted" | "human_corrected";
  original_value?: string | null;
};

export type LineItem = {
  index: number;
  description: FieldResult;
  quantity?: FieldResult | null;
  unit_price?: FieldResult | null;
  tax_rate?: FieldResult | null;
  amount?: FieldResult | null;
};

export type ParseResult = {
  document_id: string;
  filename: string;
  schema_name: "generic" | "invoice";
  source_kind: string;
  page_count: number;
  pages: PageContent[];
  text_blocks: OcrTextBlock[];
  fields: Record<string, FieldResult>;
  line_items: LineItem[];
  validations: { code: string; passed?: boolean | null; message: string }[];
  warnings: string[];
  duplicate: { is_duplicate: boolean; occurrences: number };
  review: {
    status: "not_required" | "pending" | "in_review" | "approved";
    revision: number;
    unresolved_fields: string[];
  };
};

export type ReviewEvent = {
  event_id: string;
  revision: number;
  event_type: string;
  field_path?: string | null;
  reason: string;
  reviewer: string;
};

export type OcrMode = "generic" | "invoice";

export type BatchItemStatus = "pending" | "processing" | "completed" | "failed";
export type BatchStatus = "queued" | "running" | "completed" | "partial_failure" | "failed";

export type BatchItem = {
  item_id: string;
  position: number;
  filename: string;
  content_type: string;
  status: BatchItemStatus;
  document_id?: string | null;
  error?: string | null;
};

export type BatchJob = {
  batch_id: string;
  schema_name: OcrMode;
  status: BatchStatus;
  total_items: number;
  completed_items: number;
  failed_items: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  items: BatchItem[];
};
