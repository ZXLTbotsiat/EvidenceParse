import type { ParseResult, ReviewEvent } from "../lib/types";
import { useI18n } from "../lib/i18n";

type Target = { path: string; label: string; value: string };
type Props = {
  result: ParseResult; events: ReviewEvent[]; targets: Target[];
  correctionPath: string; correctionValue: string; reviewer: string; reason: string; saving: boolean;
  onPathChange: (path: string) => void; onValueChange: (value: string) => void;
  onReviewerChange: (value: string) => void; onReasonChange: (value: string) => void;
  onSave: () => void; onApprove: () => void; onRefreshEvents: () => void;
};

export function ReviewWorkbench(props: Props) {
  const { t } = useI18n();
  const canSubmit = props.reviewer.trim().length > 0 && props.reason.trim().length >= 3;
  return (
    <section className="review-workbench">
      <div className="section-heading"><span className="kicker">{t("workbench.kicker")}</span><h2>{t("workbench.title")}</h2></div>
      <div className="review-form-grid">
        <label>{t("workbench.field")}<select value={props.correctionPath} onChange={(event) => props.onPathChange(event.target.value)}>
          <option value="">{t("workbench.selectField")}</option>
          {props.targets.map((target) => <option key={target.path} value={target.path}>{target.label}</option>)}
        </select></label>
        <label>{t("workbench.correctValue")}<input value={props.correctionValue} onChange={(event) => props.onValueChange(event.target.value)} /></label>
        <label>{t("workbench.reviewer")}<input value={props.reviewer} onChange={(event) => props.onReviewerChange(event.target.value)} placeholder={t("workbench.reviewerPlaceholder")} /></label>
        <label className="full-row">{t("workbench.reason")}<textarea value={props.reason} onChange={(event) => props.onReasonChange(event.target.value)} placeholder={t("workbench.reasonPlaceholder")} /></label>
      </div>
      <div className="review-actions">
        <button disabled={props.saving || !props.correctionPath || !canSubmit} onClick={props.onSave}>{t("workbench.save")}</button>
        <button className="secondary" disabled={props.saving || !canSubmit || props.result.review.unresolved_fields.length > 0} onClick={props.onApprove}>{t("workbench.approve")}</button>
        <button className="ghost" onClick={props.onRefreshEvents}>{t("workbench.refresh")}</button>
      </div>
      {props.events.length > 0 && <div className="audit-events">{props.events.map((event) => (
        <p key={event.event_id}><strong>{t("workbench.event", { revision: event.revision, type: event.event_type.replaceAll("_", " ") })}</strong><span>{event.reviewer} · {event.reason}</span></p>
      ))}</div>}
    </section>
  );
}
