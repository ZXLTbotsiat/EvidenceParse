import type { ParseResult, ReviewEvent } from "../lib/types";

type Target = { path: string; label: string; value: string };
type Props = {
  result: ParseResult; events: ReviewEvent[]; targets: Target[];
  correctionPath: string; correctionValue: string; reviewer: string; reason: string; saving: boolean;
  onPathChange: (path: string) => void; onValueChange: (value: string) => void;
  onReviewerChange: (value: string) => void; onReasonChange: (value: string) => void;
  onSave: () => void; onApprove: () => void; onRefreshEvents: () => void;
};

export function ReviewWorkbench(props: Props) {
  const canSubmit = props.reviewer.trim().length > 0 && props.reason.trim().length >= 3;
  return (
    <section className="review-workbench">
      <div className="section-heading"><span className="kicker">人工复核</span><h2>更正并保留审计记录</h2></div>
      <div className="review-form-grid">
        <label>字段<select value={props.correctionPath} onChange={(event) => props.onPathChange(event.target.value)}>
          <option value="">选择一个字段</option>
          {props.targets.map((target) => <option key={target.path} value={target.path}>{target.label}</option>)}
        </select></label>
        <label>正确值<input value={props.correctionValue} onChange={(event) => props.onValueChange(event.target.value)} /></label>
        <label>复核人<input value={props.reviewer} onChange={(event) => props.onReviewerChange(event.target.value)} placeholder="输入姓名" /></label>
        <label className="full-row">更正原因或复核说明<textarea value={props.reason} onChange={(event) => props.onReasonChange(event.target.value)} placeholder="说明判断依据，至少 3 个字符" /></label>
      </div>
      <div className="review-actions">
        <button disabled={props.saving || !props.correctionPath || !canSubmit} onClick={props.onSave}>保存更正</button>
        <button className="secondary" disabled={props.saving || !canSubmit || props.result.review.unresolved_fields.length > 0} onClick={props.onApprove}>批准复核</button>
        <button className="ghost" onClick={props.onRefreshEvents}>刷新审计记录</button>
      </div>
      {props.events.length > 0 && <div className="audit-events">{props.events.map((event) => (
        <p key={event.event_id}><strong>版本 {event.revision} · {event.event_type.replaceAll("_", " ")}</strong><span>{event.reviewer} · {event.reason}</span></p>
      ))}</div>}
    </section>
  );
}
