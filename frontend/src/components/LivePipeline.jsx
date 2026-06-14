const STEPS = [
  { key: 'fetch_paper', event: 'paper_fetched', label: 'Fetch Paper', description: 'Retrieves paper metadata and source' },
  { key: 'extract_claims', event: 'claims_extracted', label: 'Extract Claims', description: 'Identifies reproducibility-critical claims' },
  { key: 'map_repo', event: 'repo_mapped', label: 'Map Repository', description: 'Scans repo structure and files' },
  { key: 'audit_code', event: 'code_audited', label: 'Audit Code', description: 'Inspects functions, constants, and implementation artifacts' },
  { key: 'verify_claims', event: 'claims_verified', label: 'Verify Claims', description: 'Compares paper claims against code evidence' },
  { key: 'write_report', event: 'report_written', label: 'Write Report', description: 'Generates final reproducibility report' },
];

const TOOL_LABELS = {
  paper_fetched: 'paper_fetcher',
  claims_extracted: 'claim_extractor',
  repo_mapped: 'repo_mapper',
  code_audited: 'ast_auditor',
  claims_verified: 'verifier',
  report_written: 'report_writer',
  failed: 'graph_runtime',
};

export function pipelineStatus(step, events, audit) {
  const failed = events.find((event) => event.step === 'failed');
  if (failed) return step.event === 'failed' ? 'failed' : 'pending';
  if (events.some((event) => event.step === step.event)) return 'completed';
  if (audit?.current_node === step.key) return 'running';
  const activeIndex = STEPS.findIndex((item) => item.key === audit?.current_node);
  const stepIndex = STEPS.findIndex((item) => item.key === step.key);
  if (activeIndex > stepIndex) return 'completed';
  return 'pending';
}

export function PipelineStep({ step, status, event }) {
  return (
    <div className={`pipeline-step ${status}`}>
      <div className="step-icon" aria-hidden="true" />
      <div>
        <div className="step-title-row"><strong>{step.label}</strong><span>{status}</span></div>
        <p>{step.description}</p>
        <small>{event?.time ?? event?.timestamp ?? (event ? 'just now' : 'waiting for event')}</small>
      </div>
    </div>
  );
}

function summarize(event) {
  if (event.step === 'paper_fetched') return `Fetched ${event.title ?? 'paper'} · ${event.chars ?? 0} chars`;
  if (event.step === 'claims_extracted') return `Extracted ${event.count ?? 0} claims on attempt ${event.attempt ?? 1}`;
  if (event.step === 'repo_mapped') return `Mapped ${event.files ?? 0} relevant repository files`;
  if (event.step === 'code_audited') return `Audited ${event.functions ?? 0} functions · ${event.evidence ?? 0} evidence matches`;
  if (event.step === 'claims_verified') return `Produced ${event.verdicts ?? 0} claim verdicts`;
  if (event.step === 'report_written') return `Generated report with ${Math.round((event.score ?? 0) * 100)}% score`;
  if (event.step === 'failed') return event.error ?? 'Audit failed';
  return 'Pipeline event received';
}

export function TraceEvent({ event }) {
  return (
    <details className="trace-event">
      <summary>
        <span className="tool-chip">{TOOL_LABELS[event.step] ?? 'agent_node'}</span>
        <strong>{summarize(event)}</strong>
        <time>{event.time ?? event.timestamp ?? 'live'}</time>
      </summary>
      <pre>{JSON.stringify(event, null, 2)}</pre>
    </details>
  );
}

export function ToolAllowlistCard() {
  const tools = ['fetch_paper', 'extract_claims', 'map_repo', 'audit_code', 'verify_claims', 'write_report', 'generate_html_report'];
  return (
    <section className="allowlist-card glass-panel">
      <div className="section-heading"><p className="eyebrow">Agentic safety</p><h2>Allowed tools only</h2></div>
      <p>Repro-Agent does not execute arbitrary shell commands. All actions pass through predefined graph nodes and controlled backend tools.</p>
      <div className="tool-grid">{tools.map((tool) => <span key={tool}>{tool}</span>)}</div>
    </section>
  );
}

export function LivePipeline({ events = [], audit, connectionState = 'idle' }) {
  return (
    <section className="control-room glass-panel">
      <div className="section-heading"><p className="eyebrow">Pipeline control room</p><h2>Autonomous graph trace</h2></div>
      <div className="pipeline-grid">
        {STEPS.map((step) => <PipelineStep key={step.key} step={step} status={pipelineStatus(step, events, audit)} event={events.find((event) => event.step === step.event)} />)}
      </div>
      <div className="timeline-header">
        <h3>Live agent timeline</h3>
        <span className={`connection-pill ${connectionState}`}>SSE {connectionState}</span>
      </div>
      {events.length === 0 ? <div className="empty-state">Ready to audit. Trace events will appear here as each graph node completes.</div> : <div className="trace-list">{events.map((event, index) => <TraceEvent key={`${event.step}-${index}`} event={event} />)}</div>}
    </section>
  );
}
