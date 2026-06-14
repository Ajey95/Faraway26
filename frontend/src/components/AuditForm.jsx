import { useState } from 'react';

const AUDIT_MODES = [
  { id: 'quick', title: 'Quick Scan', eyebrow: 'Demo fast-path', description: 'Prioritizes metadata, high-signal claims, and top repository files.' },
  { id: 'deep', title: 'Deep Audit', eyebrow: 'Recommended', description: 'Balances breadth and evidence quality across claims, code, and report output.' },
  { id: 'full', title: 'Full Reproduction', eyebrow: 'Research-grade', description: 'Reserved for exhaustive verification workflows as backend depth expands.' },
];

export function AuditModeCard({ mode, selected, onSelect }) {
  return (
    <button className={`mode-card ${selected ? 'selected' : ''}`} type="button" onClick={() => onSelect(mode.id)}>
      <span>{mode.eyebrow}</span>
      <strong>{mode.title}</strong>
      <small>{mode.description}</small>
    </button>
  );
}

export function AuditForm({ onSubmit, isRunning = false }) {
  const [paperUrl, setPaperUrl] = useState('arxiv:1706.03762');
  const [repoUrl, setRepoUrl] = useState('https://github.com/tensorflow/tensor2tensor');
  const [mode, setMode] = useState('deep');

  return (
    <section className="hero-panel glass-panel">
      <div className="hero-copy">
        <p className="eyebrow">Autonomous reproducibility audit</p>
        <h1>Autonomous Scientific Reproducibility Auditor</h1>
        <p className="hero-subtitle">
          Submit a paper and repository. Repro-Agent extracts scientific claims, maps them to code,
          verifies implementation evidence, and generates an auditable reproducibility report.
        </p>
      </div>

      <form className="audit-form" onSubmit={(event) => { event.preventDefault(); onSubmit({ paper_url: paperUrl, repo_url: repoUrl }); }}>
        <div className="field-grid">
          <label>
            <span>Paper URL or arXiv ID</span>
            <input value={paperUrl} onChange={(event) => setPaperUrl(event.target.value)} placeholder="arxiv:1706.03762" />
          </label>
          <label>
            <span>GitHub repository URL</span>
            <input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repo" />
          </label>
        </div>

        <div className="mode-grid" aria-label="Audit mode">
          {AUDIT_MODES.map((item) => <AuditModeCard key={item.id} mode={item} selected={mode === item.id} onSelect={setMode} />)}
        </div>

        <div className="launch-row">
          <button className="primary-button" type="submit" disabled={isRunning}>
            {isRunning ? 'Audit running…' : 'Start Autonomous Audit'}
          </button>
          <span className="launch-note">Mode selection is visual for now; backend execution uses the existing audit API.</span>
        </div>
      </form>
    </section>
  );
}
