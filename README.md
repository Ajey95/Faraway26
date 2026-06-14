# Repro-Agent

Autonomous scientific reproducibility auditor for the FAR AWAY 2026 Agentic & Autonomous Systems track.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add OPENAI_API_KEY plus GITHUB_TOKEN
uvicorn backend.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```mermaid
flowchart TD
    A([START]) --> B[fetch_paper\nNode 1]
    B --> C[extract_claims\nNode 2]
    C -->|claims > 0| D[map_repo\nNode 3]
    C -->|claims == 0 and attempts < 2| C
    C -->|attempts >= 2| D
    D --> E[audit_code\nNode 4]
    E --> F[verify_claims\nNode 5]
    F --> G[write_report\nNode 6]
    G --> H([END])
```

## Frontend UI and UX

The frontend is a premium dark-mode React + Vite single-page app designed to make the autonomous audit pipeline feel observable, trustworthy, and research-grade:

### Screen layout

1. **Hero / product context**
   - The page opens with a polished Repro-Agent header, FAR AWAY 2026 badge, status pill, GitHub placeholder, and report CTA when an audit completes.
   - The copy frames the experience as an autonomous pipeline that runs after the user submits a paper and repository pair.

2. **Audit form**
   - The first interactive section asks for two inputs:
     - a paper URL or arXiv ID, prefilled with `arxiv:1706.03762`
     - a GitHub repository URL, prefilled with `https://github.com/tensorflow/tensor2tensor`
   - The prefilled values are chosen to support a fast demo path: users can click **Start audit** without hunting for sample data.
   - The form includes Quick Scan, Deep Audit, and Full Reproduction modes; the selected mode is submitted to the backend and controls repository scan breadth.

3. **Report summary panel**
   - After an audit starts, the UI shows the current node, verdict badge, reproducibility score ring, and mini cards for claims, scanned files, evidence matches, and missing artifacts.
   - A report link opens the backend-generated HTML report in a new tab, separating the live monitoring workflow from the final shareable artifact.

4. **Live pipeline timeline**
   - The UI subscribes to the backend SSE stream for the active audit.
   - Each pipeline event is rendered as a readable trace item with a tool label, timestamp, summary, and expandable raw JSON payload.
   - The pipeline control room shows all six graph nodes with pending/running/completed states, making autonomous decisions visible step by step.

### Component map

- `frontend/src/App.jsx` owns top-level page state, starts audits, wires the SSE hook, and composes the form, report panel, and live pipeline timeline.
- `frontend/src/components/AuditForm.jsx` contains the paper/repository input form and demo-friendly defaults.
- `frontend/src/components/ReportViewer.jsx` displays verdict state, score ring, mini metrics, current node, and report link.
- `frontend/src/components/LivePipeline.jsx` renders the six-step graph tracker, readable trace timeline, and allowed-tools panel.
- `frontend/src/hooks/useSSE.js` manages the EventSource connection, timestamps events, and reports connection state.
- `frontend/src/api.js` centralizes backend API URLs and request helpers.

### Visual design direction

- The styling uses a deep navy/black scientific grid background, glassmorphism cards, subtle gradients, and thin borders.
- The interface uses clean sans-serif typography for product copy and monospace styling for trace/tool outputs.
- High-contrast CTAs, status pills, animated running indicators, and responsive cards make the app demo-ready on desktop and projector screens.

### Remaining product polish

- Add claim-level expandable cards inside the frontend once the backend exposes richer claim/evidence snippets in the summary API.
- Add curated PASS/FAIL demo presets once cached demo audit fixtures are available.

## Merge-ready scope

This implementation is ready to merge as a hackathon-grade MVP. It includes:

- A runnable FastAPI audit API with asynchronous graph execution and SSE streaming.
- A six-node LangGraph pipeline with paper fetching, claim extraction, repository mapping, AST auditing, claim verification, and HTML report generation.
- OpenAI-powered claim extraction with regex fallback for offline demos.
- Audit modes (`quick`, `deep`, `full`) that control repository scan breadth.
- Deterministic verifier coverage for numeric hyperparameters and best-effort formula equivalence, with transparent `partial` verdicts where exact proof is unavailable.
- A premium React/Vite dashboard for launching audits, observing pipeline progress, reviewing trace events, and opening the final report.
- Unit tests for verifier behavior and math equivalence helpers.

## Current implementation status

This repository now contains a runnable hackathon MVP implementation of the PRD:

- FastAPI backend with audit creation, polling, SSE streaming, and HTML report endpoints.
- LangGraph pipeline with the six PRD nodes and retry routing for claim extraction.
- AST-first Python source scanning for functions and constants.
- GitHub repository mapping through PyGithub.
- React/Vite frontend for launching audits and watching pipeline events.

The verifier now combines deterministic checks for numeric hyperparameters, best-effort symbolic equivalence, and conservative semantic evidence matching. Claims without linked evidence remain `not_found`, and ambiguous matches are marked `partial` for reviewer transparency.
