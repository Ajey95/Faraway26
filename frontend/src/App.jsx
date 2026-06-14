import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createAudit, reportUrl } from './api';
import { AuditForm } from './components/AuditForm';
import { LivePipeline, ToolAllowlistCard } from './components/LivePipeline';
import { ReportViewer, StatusBadge } from './components/ReportViewer';
import { useSSE } from './hooks/useSSE';
import './style.css';

function getAppStatus(audit, events, connectionState) {
  if (!audit) return 'idle';
  if (events.some((event) => event.step === 'failed') || audit.current_node === 'failed') return 'failed';
  if (events.some((event) => event.step === 'report_written') || audit.current_node === 'write_report') return 'completed';
  if (connectionState === 'disconnected') return 'disconnected';
  return 'running';
}

function AppHeader({ audit, status, reportReady }) {
  return (
    <header className="app-header">
      <div className="brand-lockup">
        <div className="logo-mark">RA</div>
        <div><strong>Repro-Agent</strong><span>Scientific reproducibility auditor</span></div>
      </div>
      <div className="header-actions">
        <span className="hackathon-badge">FAR AWAY 2026 · Agentic & Autonomous Systems</span>
        <StatusBadge status={status} />
        <a className="ghost-button" href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
        {audit && reportReady ? <a className="secondary-button" href={reportUrl(audit.audit_id)} target="_blank" rel="noreferrer">Report</a> : null}
      </div>
    </header>
  );
}

function StateBanner({ status }) {
  const copy = {
    idle: ['Ready to audit', 'Submit a paper and repository to start the autonomous graph.'],
    running: ['Audit running', 'Graph nodes are executing. Watch the control room for live evidence.'],
    completed: ['Audit completed', 'The reproducibility report is ready for review.'],
    failed: ['Audit failed', 'Review the trace payload for the backend error and retry.'],
    disconnected: ['SSE disconnected', 'The audit may still be running. Refresh or retry if events stop updating.'],
  }[status] ?? ['Ready', 'Awaiting audit input.'];
  return <div className={`state-banner ${status}`}><strong>{copy[0]}</strong><span>{copy[1]}</span></div>;
}

function App() {
  const [audit, setAudit] = useState(null);
  const [submitError, setSubmitError] = useState('');
  const { events, connectionState } = useSSE(audit?.audit_id);
  const status = getAppStatus(audit, events, connectionState);
  const isRunning = status === 'running';
  const reportReady = status === 'completed';

  async function start(payload) {
    setSubmitError('');
    try {
      setAudit(await createAudit(payload));
    } catch (error) {
      setSubmitError(error.message);
    }
  }

  return (
    <div className="app-shell">
      <AppHeader audit={audit} status={status} reportReady={reportReady} />
      <main>
        <StateBanner status={status} />
        {submitError ? <div className="state-banner failed"><strong>Launch failed</strong><span>{submitError}</span></div> : null}
        <AuditForm onSubmit={start} isRunning={isRunning} />
        <div className="dashboard-grid">
          <LivePipeline events={events} audit={audit} connectionState={connectionState} />
          <div className="side-stack">
            <ReportViewer audit={audit} events={events} isRunning={isRunning} />
            <ToolAllowlistCard />
          </div>
        </div>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
