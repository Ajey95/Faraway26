import { reportUrl } from '../api';

export function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{status.replace('-', ' ')}</span>;
}

export function ScoreCard({ label, value, hint }) {
  return <div className="score-card"><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>;
}

function verdictFor(audit, isRunning) {
  if (!audit) return 'idle';
  if (audit.current_node === 'failed' || audit.status === 'failed') return 'not-reproducible';
  if (isRunning || audit.status === 'running') return 'audit-running';
  const score = audit.reproducibility_score ?? 0;
  if (score >= 0.8) return 'reproducible';
  if (score >= 0.45) return 'partially-reproducible';
  return 'not-reproducible';
}

export function ReportViewer({ audit, events = [], isRunning = false }) {
  const verdict = verdictFor(audit, isRunning);
  const claims = audit?.claims?.length ?? events.find((event) => event.step === 'claims_extracted')?.count ?? 0;
  const files = events.find((event) => event.step === 'repo_mapped')?.files ?? '—';
  const matches = events.find((event) => event.step === 'code_audited')?.evidence ?? 0;
  const missing = audit?.score_breakdown?.not_found ?? '—';
  const score = Math.round((audit?.reproducibility_score ?? 0) * 100);

  return (
    <aside className="report-panel glass-panel">
      <div className="section-heading">
        <p className="eyebrow">Audit report</p>
        <h2>Reproducibility summary</h2>
      </div>
      {!audit ? (
        <div className="empty-state"><StatusBadge status="idle" /><p>Ready to audit. Submit a paper and repository to start the graph.</p></div>
      ) : (
        <>
          <div className="score-hero">
            <div className="score-ring"><span>{score}%</span></div>
            <div>
              <StatusBadge status={verdict} />
              <p>Current node: <code>{audit.current_node}</code></p>
            </div>
          </div>
          <div className="score-grid">
            <ScoreCard label="Claims extracted" value={claims} hint="Paper assertions" />
            <ScoreCard label="Repo files scanned" value={files} hint="Relevant files" />
            <ScoreCard label="Evidence matches" value={matches} hint="AST-linked artifacts" />
            <ScoreCard label="Missing artifacts" value={missing} hint="Needs review" />
          </div>
          <a className="secondary-button full-width" href={reportUrl(audit.audit_id)} target="_blank" rel="noreferrer">Open HTML Report</a>
        </>
      )}
    </aside>
  );
}
