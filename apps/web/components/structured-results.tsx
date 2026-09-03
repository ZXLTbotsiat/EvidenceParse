import type { Evidence, ParseResult } from "../lib/types";

const FIELD_LABELS: Record<string, string> = {
  invoice_number: "发票号码", invoice_date: "日期", subtotal: "小计", tax: "税额", total: "合计",
};

const STATUS_LABELS: Record<string, string> = {
  not_required: "无需复核", pending: "待复核", in_review: "复核中", approved: "已批准",
};

export function StructuredResults({ result, onEvidenceSelect }: { result: ParseResult; onEvidenceSelect: (evidence: Evidence) => void }) {
  return (
    <div className="structured-results">
      <div className="review-summary">
        <span>状态：{STATUS_LABELS[result.review.status] ?? result.review.status}</span>
        <span>{result.review.unresolved_fields.length} 项待复核</span><span>版本 {result.review.revision}</span>
      </div>
      {Object.entries(result.fields).map(([name, field]) => {
        const evidence = field.evidence[0];
        return (
          <article className="field-card" key={name}>
            <div><span className="field-label">{FIELD_LABELS[name] ?? name.replaceAll("_", " ")}</span><strong>{field.value ?? "未识别"}</strong></div>
            <span className={`status ${field.review_required ? "needs-review" : "verified"}`}>
              {field.review_required ? "待复核" : "已验证"} · {Math.round(field.confidence * 100)}%
            </span>
            {evidence ? (
              <button className="evidence-link" onClick={() => onEvidenceSelect(evidence)}>第 {evidence.page} 页 · {evidence.text}</button>
            ) : <p className="missing-reason">{field.review_reason ?? "原文中未找到对应内容"}</p>}
          </article>
        );
      })}
      {result.line_items.length > 0 && (
        <section className="line-items"><h3>明细行</h3>{result.line_items.map((item) => (
          <div className="line-item" key={item.index}><strong>{item.description.value ?? "未识别"}</strong><span>数量 {item.quantity?.value ?? "—"}</span><span>单价 {item.unit_price?.value ?? "—"}</span><span>金额 {item.amount?.value ?? "—"}</span></div>
        ))}</section>
      )}
      <section className="validations"><h3>专业校验</h3>{result.validations.map((validation) => (
        <p key={validation.code}><span className={`check-dot ${validation.passed === true ? "pass" : "attention"}`}>{validation.passed === true ? "✓" : validation.passed === false ? "!" : "?"}</span>{validation.message}</p>
      ))}</section>
    </div>
  );
}
