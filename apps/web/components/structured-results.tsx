import type { Evidence, ParseResult } from "../lib/types";
import { useI18n } from "../lib/i18n";
import type { MessageKey } from "../lib/i18n-catalog";

const FIELD_KEYS: Record<string, MessageKey> = {
  invoice_number: "field.invoice_number", invoice_date: "field.invoice_date", subtotal: "field.subtotal", tax: "field.tax", total: "field.total",
};

const REVIEW_STATUS_KEYS: Record<string, MessageKey> = {
  not_required: "review.status.not_required", pending: "review.status.pending", in_review: "review.status.in_review", approved: "review.status.approved",
};

export function StructuredResults({ result, onEvidenceSelect }: { result: ParseResult; onEvidenceSelect: (evidence: Evidence) => void }) {
  const { t } = useI18n();
  const reviewStatus = REVIEW_STATUS_KEYS[result.review.status] ? t(REVIEW_STATUS_KEYS[result.review.status]) : result.review.status;
  return (
    <div className="structured-results">
      <div className="review-summary">
        <span>{t("review.status", { status: reviewStatus })}</span>
        <span>{t("review.unresolved", { count: result.review.unresolved_fields.length })}</span><span>{t("review.version", { revision: result.review.revision })}</span>
      </div>
      {Object.entries(result.fields).map(([name, field]) => {
        const evidence = field.evidence[0];
        return (
          <article className="field-card" key={name}>
            <div><span className="field-label">{FIELD_KEYS[name] ? t(FIELD_KEYS[name]) : name.replaceAll("_", " ")}</span><strong>{field.value ?? t("review.notRecognized")}</strong></div>
            <span className={`status ${field.review_required ? "needs-review" : "verified"}`}>
              {field.review_required ? t("review.required") : t("review.verified")} · {Math.round(field.confidence * 100)}%
            </span>
            {evidence ? (
              <button className="evidence-link" onClick={() => onEvidenceSelect(evidence)}>{t("review.evidence", { page: evidence.page, text: evidence.text })}</button>
            ) : <p className="missing-reason">{field.review_reason ?? t("review.missing")}</p>}
          </article>
        );
      })}
      {result.line_items.length > 0 && (
        <section className="line-items"><h3>{t("review.lineItems")}</h3>{result.line_items.map((item) => (
          <div className="line-item" key={item.index}><strong>{item.description.value ?? t("review.notRecognized")}</strong><span>{t("review.quantity", { value: item.quantity?.value ?? "—" })}</span><span>{t("review.unitPrice", { value: item.unit_price?.value ?? "—" })}</span><span>{t("review.amount", { value: item.amount?.value ?? "—" })}</span></div>
        ))}</section>
      )}
      <section className="validations"><h3>{t("review.validations")}</h3>{result.validations.map((validation) => (
        <p key={validation.code}><span className={`check-dot ${validation.passed === true ? "pass" : "attention"}`}>{validation.passed === true ? "✓" : validation.passed === false ? "!" : "?"}</span>{validation.message}</p>
      ))}</section>
    </div>
  );
}
