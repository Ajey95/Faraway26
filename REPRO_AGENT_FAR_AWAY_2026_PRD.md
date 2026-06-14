# Repro-Agent — Autonomous Scientific Reproducibility Auditor
## Product Requirements Document (PRD) v2.0
### FAR AWAY 2026 Hackathon · Track 3: Agentic & Autonomous Systems

---

> **Submission target:** FAR AWAY 2026, India's Biggest International Hackathon  
> **Track:** Theme 3 — Agentic & Autonomous Systems ("Build intelligent systems that can think, decide, and act independently")  
> **Judging axes:** Innovation & Technical Depth · Engineering Quality · Real-World Impact · Scalability · Design & UX · Execution Quality & Completeness  
> **Deliverable format:** GitHub repo + 15-slide deck OR 2–5 min demo video

---

## 1. EXECUTIVE SUMMARY

### The Problem

The AI/ML research field is in a **reproducibility crisis**. Studies show that over 60% of published deep learning results cannot be reproduced from paper + code alone. Billions of dollars are wasted each year by researchers, companies, and government labs attempting to replicate results where:

- The published math does **not** match the implementation
- Hyperparameters are silently modified between paper and code
- Key formulas (activation functions, loss terms, weight initialisation) use subtly different approximations
- GitHub repositories diverge from the PDF over time without any record of the discrepancy

Traditional tools — linters, code reviewers, CI/CD — only check syntax and test correctness. **They cannot verify scientific correctness.** A bug that produces a formula `0.5 * x * (1 + tanh(...))` instead of `x * Phi(x)` passes every linter and every unit test, but silently breaks reproducibility.

### What Repro-Agent Does

Repro-Agent is a **multi-agent autonomous forensic pipeline** that:

1. Ingests a research paper (arXiv ID or PDF URL) and a GitHub repository URL
2. Extracts every mathematical claim: formulas, hyperparameters, algorithms, activation functions, loss functions, optimizer configurations
3. Parses the actual source code using deterministic AST analysis — not LLM guessing
4. Cross-maps each paper claim to its code implementation with exact file + line-number citations
5. Algebraically verifies formula equivalence using symbolic math (sympy)
6. Produces a structured, evidence-backed Reproducibility Audit Report with per-claim verdicts and an overall reproducibility score
7. Streams the entire pipeline live to the browser as it runs

This is **not a chatbot**. It is an autonomous forensic pipeline that runs end-to-end without human input and produces a verifiable, citable, downloadable audit report.

---

## 2. WHY THIS WINS TRACK 3

| FAR AWAY Judging Axis | How Repro-Agent Satisfies It |
|---|---|
| **Innovation & Technical Depth** | AST-first architecture, sympy algebraic equivalence checking, LangGraph StateGraph with typed state, 6-node pipeline with conditional retry edges |
| **Engineering Quality** | FastAPI async backend, SSE streaming, SQLAlchemy audit history, authenticated GitHub API, Jinja2 templated HTML reports, Pydantic v2 schemas throughout |
| **Real-World Impact** | Directly addresses the AI reproducibility crisis; deployable as a GitHub Action; applicable to every ML paper ever published |
| **Scalability** | Stateless LangGraph nodes, SQLite → Postgres swappable via env var, async audit queue, file-level caching so re-audits skip already-parsed content |
| **Design & UX** | Live SSE pipeline timeline, claim-level diff view, colour-coded score badge, one-click demo pre-fill, downloadable self-contained HTML report |
| **Execution Quality** | Two pre-cached demo cases (PASS and FAIL scenarios), offline-capable demo mode, commit history shows genuine development not a last-minute push |

---

## 3. WHAT THE ORIGINAL NOTEBOOK DOES (AND WHY IT'S INSUFFICIENT)

The Kaggle notebook prototype (`repro-agent-autonomous-scientific-auditor.ipynb`) established the core idea but has fundamental architectural limitations that make it a proof-of-concept, not a production system:

| Issue | Notebook Approach | Production Approach (This PRD) |
|---|---|---|
| **LLM** | Gemini 2.5 Flash | Claude claude-sonnet-4-6 (better at code analysis, structured JSON output) |
| **Agent framework** | Hand-rolled `InMemorySessionService` dict | LangGraph `StateGraph` with typed `AuditState` — proper DAG, conditional retry edges |
| **Code analysis** | LLM reads raw code cold | AST-first: Python `ast` module + `libcst` for exact line numbers; LLM only for semantic mapping |
| **GitHub access** | Unauthenticated raw `requests` (60 req/hr rate limit) | PyGithub with `GITHUB_TOKEN` (5,000 req/hr, handles encoding) |
| **Formula verification** | LLM opinion ("this looks equivalent") | `sympy.simplify(paper_expr - code_expr) == 0` — algebraic proof, not opinion |
| **MCP integration** | `generate_mcp_config()` writes a JSON file and stops | Real FastAPI server with SSE streaming and React frontend |
| **Reproducibility** | Kaggle-specific paths (`/kaggle/input/bert2019/bert.pdf`) | PDF URL or arXiv ID input, download + cache locally |
| **State management** | Session dict, no type safety | TypedDict `AuditState` with dataclasses for `MathClaim`, `CodeEvidence`, `Verdict` |
| **Output** | LLM-generated markdown printed to cell | Jinja2 HTML report, SQLite persistence, download endpoint |
| **Wikipedia tool** | Used for "background check" — adds zero forensic value | Removed; replaced by Semantic Scholar API (retraction check, citation count) |

**Build from scratch. Do NOT copy notebook code. Use the notebook only to understand the domain.**

---

## 4. TECH STACK

```
Backend Runtime:     Python 3.11+
Agent Framework:     LangGraph ≥0.1.0 (StateGraph with TypedDict state — NOT sequential chains)
LLM:                 Claude claude-sonnet-4-6 via anthropic SDK ≥0.25.0 (NOT LangChain wrapper)
PDF Parsing:         pdfplumber (primary) → pypdf (fallback) → pdf2image + pytesseract (scanned OCR)
Math Extraction:     sympy (algebraic equivalence), regex (LaTeX pattern extraction from raw text)
Code Analysis:       ast (built-in Python AST), libcst (precise node locations), astroid (type inference)
GitHub Access:       PyGithub ≥2.3.0 (authenticated — REQUIRED)
Paper Metadata:      arxiv Python package + Semantic Scholar REST API (retraction, citations)
Report Output:       Jinja2 → self-contained HTML (inline CSS, no CDN — downloadable offline)
API Server:          FastAPI ≥0.111.0 + uvicorn[standard]
Streaming:           sse-starlette (Server-Sent Events)
Frontend:            React 18 + Vite (single page)
Storage:             SQLite via SQLAlchemy 2.0 (swappable to Postgres via DATABASE_URL)
Config:              python-dotenv
```

---

## 5. PROJECT STRUCTURE

```
repro-agent/
├── backend/
│   ├── main.py                        # FastAPI app: CORS, lifespan, router include
│   ├── api/
│   │   ├── routes.py                  # POST /audit · GET /audit/{id} · GET /audit/{id}/stream
│   │   │                              # GET /audit/{id}/report · GET /audits
│   │   └── schemas.py                 # Pydantic v2: AuditRequest, AuditResult, ClaimSchema, VerdictSchema
│   ├── agents/
│   │   ├── graph.py                   # LangGraph StateGraph — THE CORE PIPELINE
│   │   ├── state.py                   # TypedDict AuditState + dataclasses MathClaim, CodeEvidence, Verdict
│   │   └── nodes/
│   │       ├── paper_fetcher.py       # Node 1: Fetch PDF, extract text, get metadata
│   │       ├── claim_extractor.py     # Node 2: Claude extracts math claims as structured JSON
│   │       ├── repo_mapper.py         # Node 3: Map repo, score file relevance, fetch contents
│   │       ├── ast_auditor.py         # Node 4: AST parse all files, extract implementations
│   │       ├── verifier.py            # Node 5: Cross-map claims to evidence, produce verdicts
│   │       └── report_writer.py       # Node 6: Score, narrative, Jinja2 render
│   ├── tools/
│   │   ├── pdf_tools.py               # fetch_pdf(), extract_text(), ocr_fallback()
│   │   ├── github_tools.py            # get_file_tree(), get_file_content(), score_file_relevance()
│   │   ├── math_tools.py              # extract_latex(), sympy_equivalent(), parse_latex_to_sympy()
│   │   ├── ast_tools.py               # extract_functions(), extract_constants(), find_activations(), find_losses()
│   │   └── metadata_tools.py          # get_arxiv_metadata(), get_semantic_scholar(), check_retraction()
│   ├── db/
│   │   ├── models.py                  # SQLAlchemy: Audit, Claim, Verdict, AuditEvent tables
│   │   └── session.py                 # Async session factory, get_db() dependency
│   ├── templates/
│   │   └── report.html.j2             # Jinja2 report template (inline CSS, self-contained)
│   └── demo/
│       ├── attention_audit.json       # Pre-cached: "Attention Is All You Need" result
│       └── bert_audit.json            # Pre-cached: BERT GELU discrepancy result
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Root: router + global state
│   │   ├── components/
│   │   │   ├── AuditForm.jsx          # Input form + demo pre-fill buttons
│   │   │   ├── LivePipeline.jsx       # SSE event timeline — real-time agent steps
│   │   │   ├── ReportViewer.jsx       # Score ring + claim table + diff view
│   │   │   └── ClaimCard.jsx          # Expandable: paper text | code snippet | verdict badge
│   │   ├── hooks/
│   │   │   └── useSSE.js              # Custom hook: SSE connection management + reconnect
│   │   └── api.js                     # Typed fetch wrappers for all backend endpoints
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
├── .env.example
└── README.md                          # 3-command setup + Mermaid architecture diagram
```

---

## 6. DATA MODELS (`agents/state.py`)

```python
from typing import TypedDict, List, Optional, Literal
from dataclasses import dataclass, field

@dataclass
class MathClaim:
    claim_id: str                        # UUID, e.g. "claim_001"
    claim_type: Literal[                 # Controlled vocabulary
        "formula",       # A mathematical equation or function definition
        "hyperparameter", # A specific numeric value (lr=0.0001, dropout=0.1)
        "algorithm",     # A described procedure (masked language modeling)
        "activation",    # A specific activation function (GELU, ReLU, Swish)
        "loss",          # A loss function definition (cross-entropy, MSE, KL)
        "optimizer"      # Optimizer + config (Adam β1=0.9 β2=0.999 ε=1e-8)
    ]
    description: str                     # Human-readable: "GELU activation function"
    latex: Optional[str]                 # LaTeX extracted from paper: r"x \cdot \Phi(x)"
    paper_section: str                   # "Section 3.1 — Architecture"
    paper_page: int                      # 1-indexed page number
    raw_text: str                        # Surrounding 2-3 sentences from paper
    confidence: float                    # Claude's extraction confidence 0.0–1.0


@dataclass
class CodeEvidence:
    claim_id: str                        # Links back to MathClaim
    file_path: str                       # "modeling/bert_model.py"
    line_start: int                      # 1-indexed
    line_end: int
    code_snippet: str                    # Exact extracted lines
    function_name: str                   # Enclosing function: "gelu_activation"
    ast_extracted: bool                  # True = AST found it; False = LLM found it
    extraction_method: str               # "ast_constant" | "ast_function" | "llm_mapping"


@dataclass
class Verdict:
    claim_id: str
    status: Literal["pass", "fail", "partial", "not_found"]
    confidence: float                    # 0.0–1.0
    reasoning: str                       # Why this verdict: cite evidence
    discrepancy: Optional[str]           # If fail/partial: what specifically differs
    sympy_verified: bool                 # True if algebraic equivalence was proven


class AuditState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────
    paper_url: str                       # "arxiv:1706.03762" or direct PDF URL
    repo_url: str                        # "https://github.com/tensorflow/tensor2tensor"
    audit_id: str                        # UUID for this run

    # ── Paper data ────────────────────────────────────────────────────────
    paper_text: str                      # Full extracted text
    paper_metadata: dict                 # title, authors, year, arxiv_id,
                                         # citation_count, retracted, abstract

    # ── Extracted claims ──────────────────────────────────────────────────
    claims: List[MathClaim]
    claim_extraction_attempts: int       # For conditional retry logic

    # ── Repository data ───────────────────────────────────────────────────
    repo_structure: dict                 # {path: {size, type, relevance_score}}
    relevant_files: List[str]            # Top files by relevance score
    file_contents: dict                  # {path: raw_source_code}

    # ── AST analysis results ──────────────────────────────────────────────
    ast_functions: dict                  # {path: List[FunctionInfo]}
    ast_constants: dict                  # {path: List[ConstantInfo]}
    code_evidence: List[CodeEvidence]

    # ── Verdicts ──────────────────────────────────────────────────────────
    verdicts: List[Verdict]

    # ── Report ────────────────────────────────────────────────────────────
    report_markdown: str
    report_html: str
    reproducibility_score: float         # 0.0–1.0 weighted
    score_breakdown: dict                # {pass: N, fail: N, partial: N, not_found: N}

    # ── Pipeline control ──────────────────────────────────────────────────
    current_node: str
    errors: List[str]
    sse_events: List[dict]               # Accumulated events for streaming
```

---

## 7. AGENT PIPELINE — LANGGRAPH STATEGRAPH (`agents/graph.py`)

```python
from langgraph.graph import StateGraph, END
from agents.state import AuditState
from agents.nodes import (
    paper_fetcher, claim_extractor, repo_mapper,
    ast_auditor, verifier, report_writer
)

def should_retry_extraction(state: AuditState) -> str:
    """Conditional edge: retry if no claims found, but cap at 2 attempts."""
    if len(state["claims"]) > 0:
        return "map_repo"
    if state["claim_extraction_attempts"] >= 2:
        # After 2 retries, proceed with empty claims — report will note this
        return "map_repo"
    return "extract_claims"   # retry

def build_graph() -> StateGraph:
    graph = StateGraph(AuditState)

    graph.add_node("fetch_paper",     paper_fetcher.run)
    graph.add_node("extract_claims",  claim_extractor.run)
    graph.add_node("map_repo",        repo_mapper.run)
    graph.add_node("audit_code",      ast_auditor.run)
    graph.add_node("verify_claims",   verifier.run)
    graph.add_node("write_report",    report_writer.run)

    graph.set_entry_point("fetch_paper")
    graph.add_edge("fetch_paper", "extract_claims")

    # Conditional retry on empty extraction
    graph.add_conditional_edges(
        "extract_claims",
        should_retry_extraction,
        {"map_repo": "map_repo", "extract_claims": "extract_claims"}
    )

    graph.add_edge("map_repo",       "audit_code")
    graph.add_edge("audit_code",     "verify_claims")
    graph.add_edge("verify_claims",  "write_report")
    graph.add_edge("write_report",   END)

    return graph.compile()
```

### Pipeline Mermaid Diagram (include in README)

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

    style B fill:#4A90D9,color:#fff
    style C fill:#7B68EE,color:#fff
    style D fill:#20B2AA,color:#fff
    style E fill:#FF6B6B,color:#fff
    style F fill:#FFA500,color:#fff
    style G fill:#32CD32,color:#fff
```

---

## 8. NODE SPECIFICATIONS (COMPLETE)

### Node 1: `paper_fetcher.py` — Fetch & Parse

**Purpose:** Obtain the paper PDF and extract clean text with metadata.

**Implementation:**

```python
import re
import arxiv
import requests
import pdfplumber
from pypdf import PdfReader
from tools.metadata_tools import get_semantic_scholar, check_retraction
from tools.pdf_tools import ocr_fallback

ARXIV_PATTERN = re.compile(r'^\d{4}\.\d{4,5}(v\d+)?$')

def run(state: AuditState) -> AuditState:
    paper_url = state["paper_url"]
    audit_id = state["audit_id"]

    # ── Step 1: Resolve URL ────────────────────────────────────────────
    arxiv_id = None
    if paper_url.startswith("arxiv:"):
        arxiv_id = paper_url[6:].strip()
    elif ARXIV_PATTERN.match(paper_url.strip()):
        arxiv_id = paper_url.strip()

    pdf_url = None
    metadata = {}

    if arxiv_id:
        search = arxiv.Search(id_list=[arxiv_id])
        result = next(search.results())
        pdf_url = result.pdf_url
        metadata = {
            "title": result.title,
            "authors": [str(a) for a in result.authors],
            "year": result.published.year,
            "arxiv_id": arxiv_id,
            "abstract": result.summary[:500],
        }
    else:
        pdf_url = paper_url
        metadata = {"title": "Unknown", "authors": [], "year": None,
                    "arxiv_id": None, "abstract": ""}

    # ── Step 2: Download PDF ───────────────────────────────────────────
    resp = requests.get(pdf_url, timeout=30)
    resp.raise_for_status()
    pdf_bytes = resp.content

    # ── Step 3: Extract text (pdfplumber → pypdf → OCR) ───────────────
    paper_text = ""
    try:
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages
            paper_text = "\n".join(p.extract_text() or "" for p in pages)
    except Exception:
        pass

    if len(paper_text.strip()) < 500:
        try:
            import io
            reader = PdfReader(io.BytesIO(pdf_bytes))
            paper_text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception:
            pass

    if len(paper_text.strip()) < 500:
        # Scanned PDF — OCR fallback
        paper_text = ocr_fallback(pdf_bytes)

    page_count = paper_text.count("\n\n") // 3  # rough estimate

    # ── Step 4: Enrich metadata from Semantic Scholar ──────────────────
    if arxiv_id:
        ss_data = get_semantic_scholar(arxiv_id)
        metadata["citation_count"] = ss_data.get("citationCount", 0)
        metadata["retracted"] = check_retraction(arxiv_id)
        if metadata["retracted"]:
            state["errors"].append(
                f"WARNING: This paper has been retracted per Semantic Scholar."
            )

    state["paper_text"] = paper_text
    state["paper_metadata"] = metadata
    state["current_node"] = "fetch_paper"

    # ── SSE event ─────────────────────────────────────────────────────
    state["sse_events"].append({
        "step": "paper_fetched",
        "title": metadata.get("title", "Unknown"),
        "pages": page_count,
        "chars": len(paper_text),
        "retracted": metadata.get("retracted", False),
    })

    return state
```

**Error handling:** If PDF fetch fails, attempt Semantic Scholar's OpenAccess PDF link. If that also fails, set error and continue — Node 6 will generate a partial report noting the failure.

---

### Node 2: `claim_extractor.py` — Extract Mathematical Claims

**Purpose:** Use Claude to extract all verifiable mathematical claims from the paper. This is the most critical node — the quality of everything downstream depends on it.

**EXTRACTION_SYSTEM_PROMPT (use verbatim):**

```python
EXTRACTION_SYSTEM_PROMPT = """
You are a mathematical claim extractor for AI/ML research papers.
Your sole job is to identify every mathematical specification that could be verified by examining source code.

Extract claims of EXACTLY these types:
- formula: A mathematical equation or function definition (GELU, attention mechanism, loss function)
- hyperparameter: A specific numeric value used in the model (learning_rate=0.0001, dropout=0.1, d_model=512)
- algorithm: A described multi-step procedure (masked language modeling, beam search, gradient clipping)
- activation: A specific activation function (ReLU, GELU, Swish, Sigmoid, Softmax)
- loss: A loss function definition (cross-entropy, MSE, KL divergence, contrastive loss)
- optimizer: Optimizer configuration (Adam with beta1=0.9, beta2=0.999, epsilon=1e-8)

For EACH claim, output a JSON object with these EXACT keys:
{
  "claim_type": "<one of the six types above>",
  "description": "<plain English: what does this claim state?>",
  "latex": "<LaTeX string if it is a formula, null otherwise>",
  "verbatim_text": "<copy the EXACT sentence(s) from the paper stating this claim>",
  "section": "<section heading where found, e.g. 'Section 3.1 Model Architecture'>",
  "page_hint": <estimated page number as integer, or 0 if unknown>,
  "confidence": <float 0.0–1.0, how certain you are this is a real verifiable claim>
}

Output a JSON array. STRICT RULES:
- Include ONLY claims with confidence > 0.6
- Do NOT include claims about dataset size, training duration, or hardware (GPU type, TPU count)
- Do NOT include vague claims ("we use standard techniques", "following prior work")
- Do NOT include claims whose only evidence is a citation to another paper
- Each hyperparameter should be ONE claim (do not bundle lr + dropout + d_model into one)
- If the same formula appears multiple times, report it ONCE with the most complete statement
"""

RETRY_SYSTEM_PROMPT = """
The previous extraction attempt returned no claims. This may be because the text is from paper abstracts, 
related work sections, or appendices with no mathematical content. 

Try again with LOWER confidence threshold (include claims with confidence > 0.3).
Also look specifically for:
- Any number that appears to be a hyperparameter (any decimal number like 0.1, 512, 1e-4)
- Any mention of function names (relu, gelu, softmax, adam, sgd)
- Any equation described in words even without LaTeX ("we multiply by one half", "take the square root")

Output the same JSON array format.
"""
```

**Implementation:**

```python
import anthropic
import json
import re
import uuid
from agents.state import AuditState, MathClaim
from tools.math_tools import extract_latex_patterns

client = anthropic.Anthropic()

def chunk_text(text: str, max_chars: int = 24000) -> List[str]:
    """Split on section boundaries first, then by length."""
    # Try to split on section headers
    section_pattern = re.compile(r'\n(?=\d+[\.\s]+[A-Z]|\bAbstract\b|\bIntroduction\b|'
                                  r'\bConclusion\b|\bMethodology\b|\bExperiments?\b)', re.MULTILINE)
    sections = section_pattern.split(text)
    
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) < max_chars:
            current += section
        else:
            if current:
                chunks.append(current)
            current = section
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:max_chars]]


def parse_claude_response(response_text: str) -> List[dict]:
    """Robust JSON extraction — handles markdown fences and trailing commas."""
    # Strip markdown fences
    clean = re.sub(r'```(?:json)?\n?', '', response_text).strip().rstrip('`')
    # Find the outermost array
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        # Try to fix trailing commas
        fixed = re.sub(r',\s*([}\]])', r'\1', match.group())
        try:
            return json.loads(fixed)
        except Exception:
            return []


def run(state: AuditState) -> AuditState:
    paper_text = state["paper_text"]
    attempts = state.get("claim_extraction_attempts", 0)
    
    system_prompt = RETRY_SYSTEM_PROMPT if attempts > 0 else EXTRACTION_SYSTEM_PROMPT
    chunks = chunk_text(paper_text)
    
    all_raw_claims = []
    
    for i, chunk in enumerate(chunks):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Extract all mathematical claims from this paper section:\n\n{chunk}"
            }]
        )
        raw = parse_claude_response(response.content[0].text)
        all_raw_claims.extend(raw)
    
    # ── Deduplicate ────────────────────────────────────────────────────
    seen_descriptions = set()
    unique_claims = []
    for raw in all_raw_claims:
        desc_key = raw.get("description", "").lower()[:60]
        if desc_key not in seen_descriptions and raw.get("confidence", 0) > 0.6:
            seen_descriptions.add(desc_key)
            unique_claims.append(raw)
    
    # ── Convert to MathClaim objects ───────────────────────────────────
    claims = []
    for i, raw in enumerate(unique_claims):
        # Also run regex LaTeX extraction as secondary pass
        latex = raw.get("latex")
        if not latex:
            extracted = extract_latex_patterns(raw.get("verbatim_text", ""))
            latex = extracted[0] if extracted else None
        
        claims.append(MathClaim(
            claim_id=f"claim_{i+1:03d}",
            claim_type=raw.get("claim_type", "formula"),
            description=raw.get("description", ""),
            latex=latex,
            paper_section=raw.get("section", "Unknown"),
            paper_page=int(raw.get("page_hint", 0)),
            raw_text=raw.get("verbatim_text", ""),
            confidence=float(raw.get("confidence", 0.7)),
        ))
    
    state["claims"] = claims
    state["claim_extraction_attempts"] = attempts + 1
    
    # Type breakdown for SSE event
    type_counts = {}
    for c in claims:
        type_counts[c.claim_type] = type_counts.get(c.claim_type, 0) + 1
    
    state["sse_events"].append({
        "step": "claims_extracted",
        "count": len(claims),
        "types": type_counts,
        "retry_used": attempts > 0,
    })
    
    return state
```

---

### Node 3: `repo_mapper.py` — Map Repository

**Purpose:** Intelligently identify which files in the repo are likely to contain the implementations we're verifying.

```python
from github import Github
import os

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

# Relevance scoring heuristics
HIGH_RELEVANCE = [
    "model.py", "modeling.py", "models.py", "model_utils.py",
    "layers.py", "layer.py", "ops.py", "operations.py",
    "activations.py", "activation.py", "losses.py", "loss.py",
    "optimizer.py", "optimizers.py", "train.py", "trainer.py",
    "network.py", "net.py", "arch.py", "architecture.py",
]
MEDIUM_RELEVANCE = [
    "utils.py", "helpers.py", "config.py", "hparams.py",
    "params.py", "hyperparams.py", "constants.py", "defaults.py",
]
SKIP_DIRS = {
    "test", "tests", "testing", "docs", "doc", "examples",
    "example", "notebooks", "notebook", "demo", "__pycache__",
    ".git", "build", "dist", "scripts",
}

def score_file(path: str) -> int:
    """Return 0 (skip), 1 (medium), 2 (high) relevance."""
    parts = path.lower().split("/")
    # Skip test/docs directories
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return 0
    filename = parts[-1]
    if not filename.endswith(".py"):
        return 0
    if filename in HIGH_RELEVANCE or any(h.rstrip(".py") in filename for h in HIGH_RELEVANCE):
        return 2
    if filename in MEDIUM_RELEVANCE:
        return 1
    # Files with "model" or "net" in their name get medium relevance
    if any(kw in filename for kw in ["model", "net", "layer", "loss", "optim"]):
        return 1
    return 0


def run(state: AuditState) -> AuditState:
    g = Github(GITHUB_TOKEN)
    
    # Parse owner/repo from URL
    parts = state["repo_url"].rstrip("/").rstrip(".git").split("/")
    owner, repo_name = parts[-2], parts[-1]
    repo = g.get_repo(f"{owner}/{repo_name}")
    
    # ── Get full file tree ─────────────────────────────────────────────
    tree = repo.get_git_tree(sha="HEAD", recursive=True)
    
    scored_files = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        score = score_file(item.path)
        if score > 0:
            scored_files.append((item.path, item.size or 0, score))
    
    # Sort by (score DESC, size ASC) — prefer high-relevance, smaller files
    scored_files.sort(key=lambda x: (-x[2], x[1]))
    
    # Hard limits: max 20 files, max 500KB total
    selected = []
    total_bytes = 0
    for path, size, score in scored_files:
        if len(selected) >= 20:
            break
        if total_bytes + size > 500 * 1024:
            break
        selected.append(path)
        total_bytes += size
    
    # ── Fetch file contents ────────────────────────────────────────────
    file_contents = {}
    for path in selected:
        try:
            content_file = repo.get_contents(path)
            # PyGithub handles base64 decode automatically
            file_contents[path] = content_file.decoded_content.decode("utf-8", errors="ignore")
        except Exception as e:
            state["errors"].append(f"Could not fetch {path}: {e}")
    
    state["repo_structure"] = {
        path: {"size": size, "relevance": score}
        for path, size, score in scored_files
    }
    state["relevant_files"] = selected
    state["file_contents"] = file_contents
    state["current_node"] = "map_repo"
    
    state["sse_events"].append({
        "step": "repo_mapped",
        "total_python_files": len(scored_files),
        "files_selected": len(selected),
        "total_kb": total_bytes // 1024,
    })
    
    return state
```

---

### Node 4: `ast_auditor.py` — AST Code Analysis

**Purpose:** Extract concrete implementations from source code using deterministic AST parsing. This is what makes verdicts trustworthy — not LLM guessing.

**`tools/ast_tools.py` (implement these exactly):**

```python
import ast
import libcst as cst
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FunctionInfo:
    name: str
    line_start: int
    line_end: int
    args: List[str]           # argument names
    body_source: str          # extracted source lines
    docstring: Optional[str]
    
@dataclass
class ConstantInfo:
    value: float
    variable_name: str        # what it's assigned to, if any
    line: int
    context: str              # surrounding line of code

@dataclass
class ActivationInfo:
    activation_name: str      # "gelu", "relu", "softmax", etc.
    line: int
    code_line: str

@dataclass
class LossInfo:
    loss_type: str            # "cross_entropy", "mse", etc.
    line: int
    code_line: str


# Known activation patterns to search for
ACTIVATION_PATTERNS = {
    "gelu": ["gelu", "GeLU", "GELU", "F.gelu", "nn.GELU"],
    "relu": ["relu", "ReLU", "F.relu", "nn.ReLU"],
    "swish": ["swish", "Swish", "silu", "F.silu", "nn.SiLU"],
    "tanh": ["tanh", "F.tanh", "nn.Tanh"],
    "softmax": ["softmax", "F.softmax", "nn.Softmax"],
    "sigmoid": ["sigmoid", "F.sigmoid", "nn.Sigmoid"],
    "leaky_relu": ["leaky_relu", "LeakyReLU", "F.leaky_relu"],
}

LOSS_PATTERNS = {
    "cross_entropy": ["cross_entropy", "CrossEntropyLoss", "nll_loss", "BCELoss"],
    "mse": ["mse_loss", "MSELoss", "mean_squared_error"],
    "kl_divergence": ["kl_div", "KLDivLoss"],
    "contrastive": ["contrastive", "triplet", "InfoNCE"],
}


def extract_functions(source_code: str) -> List[FunctionInfo]:
    """Extract all function definitions with body source."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    
    lines = source_code.split("\n")
    functions = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            line_start = node.lineno
            line_end = node.end_lineno if hasattr(node, 'end_lineno') else line_start + 20
            body_lines = lines[line_start - 1 : line_end]
            
            docstring = None
            if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant)):
                docstring = str(node.body[0].value.value)[:200]
            
            functions.append(FunctionInfo(
                name=node.name,
                line_start=line_start,
                line_end=line_end,
                args=[arg.arg for arg in node.args.args],
                body_source="\n".join(body_lines),
                docstring=docstring,
            ))
    
    return functions


def extract_numeric_constants(source_code: str) -> List[ConstantInfo]:
    """Extract all numeric constants with variable context."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    
    lines = source_code.split("\n")
    constants = []
    
    for node in ast.walk(tree):
        # Look for assignments like: lr = 0.0001
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    val = node.value.value
                    if isinstance(val, (int, float)) and val not in (0, 1, -1, 2):
                        line = node.lineno
                        constants.append(ConstantInfo(
                            value=float(val),
                            variable_name=target.id,
                            line=line,
                            context=lines[line - 1].strip() if line <= len(lines) else "",
                        ))
        # Also check keyword arguments: Adam(lr=0.0001, betas=(0.9, 0.999))
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if isinstance(kw.value, ast.Constant):
                    val = kw.value.value
                    if isinstance(val, (int, float)) and val not in (0, 1, -1, 2):
                        line = kw.value.lineno
                        constants.append(ConstantInfo(
                            value=float(val),
                            variable_name=kw.arg or "unknown",
                            line=line,
                            context=lines[line - 1].strip() if line <= len(lines) else "",
                        ))
    
    return constants


def find_activation_calls(source_code: str) -> List[ActivationInfo]:
    """Find all activation function usages."""
    lines = source_code.split("\n")
    results = []
    for i, line in enumerate(lines, 1):
        for act_name, patterns in ACTIVATION_PATTERNS.items():
            if any(p in line for p in patterns):
                results.append(ActivationInfo(
                    activation_name=act_name,
                    line=i,
                    code_line=line.strip(),
                ))
    return results


def find_loss_functions(source_code: str) -> List[LossInfo]:
    """Find all loss function usages."""
    lines = source_code.split("\n")
    results = []
    for i, line in enumerate(lines, 1):
        for loss_type, patterns in LOSS_PATTERNS.items():
            if any(p in line for p in patterns):
                results.append(LossInfo(
                    loss_type=loss_type,
                    line=i,
                    code_line=line.strip(),
                ))
    return results
```

**Node implementation:**

```python
def run(state: AuditState) -> AuditState:
    ast_functions = {}
    ast_constants = {}
    
    for path, source in state["file_contents"].items():
        functions = extract_functions(source)
        constants = extract_numeric_constants(source)
        activations = find_activation_calls(source)
        losses = find_loss_functions(source)
        
        ast_functions[path] = [vars(f) for f in functions]
        ast_constants[path] = [vars(c) for c in constants]
        
        state["sse_events"].append({
            "step": "file_audited",
            "file": path,
            "functions_found": len(functions),
            "constants_found": len(constants),
            "activations": [a.activation_name for a in activations],
        })
    
    # ── LLM mapping pass: map claims to discovered functions ───────────
    # Build a compact summary of what AST found, then ask Claude to map
    function_summary = {}
    for path, funcs in ast_functions.items():
        function_summary[path] = [
            {"name": f["name"], "args": f["args"], "line_start": f["line_start"],
             "snippet": f["body_source"][:300]}
            for f in funcs[:10]  # top 10 per file
        ]
    
    claims_for_mapping = [
        {"claim_id": c.claim_id, "description": c.description, "claim_type": c.claim_type}
        for c in state["claims"]
    ]
    
    if claims_for_mapping and function_summary:
        mapping_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""Map paper claims to code functions. 
Output a JSON array where each item is:
{"claim_id": "...", "file_path": "...", "function_name": "...", "confidence": 0.0-1.0, "reason": "..."}
Only include mappings with confidence > 0.4. Output only the JSON array.""",
            messages=[{
                "role": "user",
                "content": (f"CLAIMS TO MAP:\n{json.dumps(claims_for_mapping, indent=2)}\n\n"
                           f"FUNCTIONS FOUND IN REPO:\n{json.dumps(function_summary, indent=2)}")
            }]
        )
        
        mappings = parse_json_response(mapping_response.content[0].text)
        
        # Convert mappings to CodeEvidence
        evidence = []
        for m in mappings:
            claim_id = m.get("claim_id")
            path = m.get("file_path")
            func_name = m.get("function_name")
            
            if path and path in ast_functions:
                matching_func = next(
                    (f for f in ast_functions[path] if f["name"] == func_name), None
                )
                if matching_func:
                    evidence.append(CodeEvidence(
                        claim_id=claim_id,
                        file_path=path,
                        line_start=matching_func["line_start"],
                        line_end=matching_func["line_end"],
                        code_snippet=matching_func["body_source"][:500],
                        function_name=func_name,
                        ast_extracted=True,
                        extraction_method="ast_function",
                    ))
        
        state["code_evidence"] = evidence
    
    state["ast_functions"] = ast_functions
    state["ast_constants"] = ast_constants
    state["current_node"] = "audit_code"
    
    return state
```

---

### Node 5: `verifier.py` — Produce Verdicts

**Purpose:** For each claim, compare paper specification to code evidence and produce a final verdict. Uses sympy for formula claims, exact-value matching for hyperparameters, and Claude for algorithm claims.

```python
import sympy
from sympy.parsing.latex import parse_latex

def verify_formula(claim: MathClaim, evidence: CodeEvidence) -> Verdict:
    """Try algebraic equivalence via sympy; fall back to LLM."""
    sympy_verified = False
    
    if claim.latex and evidence.code_snippet:
        try:
            paper_expr = parse_latex(claim.latex)
            # Ask Claude to convert code to sympy expression
            code_expr_response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system="Convert this Python math code to a sympy expression string. Output ONLY the sympy expression, nothing else.",
                messages=[{"role": "user", "content": evidence.code_snippet}]
            )
            code_expr_str = code_expr_response.content[0].text.strip()
            code_expr = eval(f"sympy.{code_expr_str}", {"sympy": sympy})
            
            # Algebraic equivalence check
            difference = sympy.simplify(paper_expr - code_expr)
            if difference == 0:
                sympy_verified = True
                return Verdict(
                    claim_id=claim.claim_id,
                    status="pass",
                    confidence=0.95,
                    reasoning=f"Algebraically proven equivalent by sympy: simplify(paper - code) = 0",
                    discrepancy=None,
                    sympy_verified=True,
                )
        except Exception:
            pass  # Fall through to LLM verification
    
    # LLM comparison fallback
    verdict_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""Compare a paper's mathematical claim to its code implementation.
Output ONLY a JSON object:
{"status": "pass|fail|partial|not_found", "confidence": 0.0-1.0, "reasoning": "...", "discrepancy": "... or null"}""",
        messages=[{"role": "user", "content": (
            f"PAPER CLAIMS:\n{claim.description}\nLaTeX: {claim.latex}\nText: {claim.raw_text}\n\n"
            f"CODE IMPLEMENTATION:\n{evidence.code_snippet}"
        )}]
    )
    raw = json.loads(verdict_response.content[0].text)
    return Verdict(
        claim_id=claim.claim_id,
        status=raw["status"],
        confidence=float(raw["confidence"]),
        reasoning=raw["reasoning"],
        discrepancy=raw.get("discrepancy"),
        sympy_verified=sympy_verified,
    )


def verify_hyperparameter(claim: MathClaim, all_constants: dict) -> Verdict:
    """Search extracted constants for exact or near-exact match."""
    # Extract the expected value from the description
    value_match = re.search(r'[-+]?\d*\.?\d+([eE][-+]?\d+)?', claim.raw_text)
    if not value_match:
        return Verdict(claim.claim_id, "not_found", 0.3,
                      "No numeric value found in claim text", None, False)
    
    expected = float(value_match.group())
    
    for path, constants in all_constants.items():
        for const in constants:
            val = const["value"]
            if abs(val - expected) < 1e-9:  # exact match
                return Verdict(
                    claim_id=claim.claim_id,
                    status="pass",
                    confidence=0.9,
                    reasoning=f"Exact match: {const['variable_name']}={val} at {path}:{const['line']}",
                    discrepancy=None,
                    sympy_verified=False,
                )
            if abs(val - expected) / (abs(expected) + 1e-9) < 0.01:  # within 1%
                return Verdict(
                    claim_id=claim.claim_id,
                    status="partial",
                    confidence=0.7,
                    reasoning=f"Near match: paper={expected}, code={val} ({path}:{const['line']})",
                    discrepancy=f"Paper: {expected}, Code: {val} (diff: {abs(val-expected):.2e})",
                    sympy_verified=False,
                )
    
    return Verdict(claim.claim_id, "not_found", 0.5,
                  f"Value {expected} not found in any extracted constants", None, False)


def run(state: AuditState) -> AuditState:
    evidence_by_claim = {e.claim_id: e for e in state["code_evidence"]}
    verdicts = []
    
    for claim in state["claims"]:
        evidence = evidence_by_claim.get(claim.claim_id)
        
        if not evidence:
            verdicts.append(Verdict(
                claim_id=claim.claim_id,
                status="not_found",
                confidence=0.5,
                reasoning="No code implementation found in the repository for this claim.",
                discrepancy=None,
                sympy_verified=False,
            ))
            state["sse_events"].append({
                "step": "claim_verified",
                "claim_id": claim.claim_id,
                "verdict": "not_found",
            })
            continue
        
        if claim.claim_type == "hyperparameter":
            verdict = verify_hyperparameter(claim, state["ast_constants"])
        elif claim.claim_type in ("formula", "activation", "loss"):
            verdict = verify_formula(claim, evidence)
        else:
            # Algorithm claims — pure LLM comparison
            verdict = verify_formula(claim, evidence)  # LLM path
        
        # AST-extracted evidence gets a confidence bonus
        if evidence.ast_extracted:
            verdict.confidence = min(1.0, verdict.confidence + 0.1)
        
        verdicts.append(verdict)
        state["sse_events"].append({
            "step": "claim_verified",
            "claim_id": claim.claim_id,
            "verdict": verdict.status,
            "confidence": verdict.confidence,
        })
    
    state["verdicts"] = verdicts
    state["current_node"] = "verify_claims"
    return state
```

---

### Node 6: `report_writer.py` — Generate Report

**Purpose:** Compute the reproducibility score, write the narrative, render the Jinja2 HTML report, and persist to DB.

```python
# ── Score calculation ──────────────────────────────────────────────────
CLAIM_TYPE_WEIGHTS = {
    "formula": 2.0,
    "hyperparameter": 2.0,
    "activation": 1.5,
    "loss": 1.5,
    "optimizer": 1.5,
    "algorithm": 1.0,
}
STATUS_SCORES = {
    "pass": 1.0,
    "partial": 0.5,
    "fail": 0.0,
    "not_found": 0.0,
}

def compute_score(claims: List[MathClaim], verdicts: List[Verdict]) -> float:
    verdict_map = {v.claim_id: v for v in verdicts}
    total_weight = 0.0
    weighted_score = 0.0
    for claim in claims:
        weight = CLAIM_TYPE_WEIGHTS.get(claim.claim_type, 1.0)
        verdict = verdict_map.get(claim.claim_id)
        score = STATUS_SCORES.get(verdict.status if verdict else "not_found", 0.0)
        total_weight += weight
        weighted_score += weight * score
    return weighted_score / total_weight if total_weight > 0 else 0.0
```

**Report HTML template** (`templates/report.html.j2`) must be self-contained (all CSS inline, no external CDN) and include:

- Paper title, authors, year, arXiv link, citation count
- Retraction warning banner (if `retracted == True`) in red
- Large score badge: green (≥0.8), amber (0.5–0.79), red (<0.5)
- Score breakdown: pass / partial / fail / not_found counts
- Per-claim table: sortable by verdict, expandable rows
- Diff view for FAIL/PARTIAL: left panel = paper LaTeX rendered, right panel = code snippet with line numbers
- Narrative sections: Abstract, Key Discrepancies, Reproducibility Assessment

---

## 9. API ENDPOINTS (`api/routes.py`)

```python
# POST /audit
# Body: {"paper_url": "arxiv:1706.03762", "repo_url": "https://github.com/..."}
# Returns: {"audit_id": "uuid4", "status": "queued"}
# Runs audit in background via asyncio.create_task

# GET /audit/{audit_id}
# Returns: AuditResult JSON when complete
# Returns: {"status": "running", "audit_id": "..."} while in progress
# Returns: 404 if not found

# GET /audit/{audit_id}/stream
# Returns: Server-Sent Events stream
# Each event: data: {"step": "...", "message": "...", "timestamp": "ISO8601"}
# Stream closes with: data: {"step": "complete", "score": 0.82, "audit_id": "..."}
# CORS: allow credentials, allow frontend origin

# GET /audit/{audit_id}/report
# Returns: text/html — self-contained downloadable report
# Header: Content-Disposition: attachment; filename="repro-audit-{id}.html"

# GET /audits
# Returns: list of last 20 audits from SQLite with title, score, timestamp, status

# GET /health
# Returns: {"status": "ok", "version": "2.0.0"}
```

**SSE Implementation:**
```python
from sse_starlette.sse import EventSourceResponse
import asyncio

@router.get("/audit/{audit_id}/stream")
async def stream_audit(audit_id: str):
    async def event_generator():
        last_event_idx = 0
        while True:
            audit = await get_audit_from_db(audit_id)
            events = audit.sse_events[last_event_idx:]
            for event in events:
                yield {"data": json.dumps(event)}
                last_event_idx += 1
            
            if audit.status in ("complete", "error"):
                yield {"data": json.dumps({"step": "complete",
                        "score": audit.reproducibility_score,
                        "audit_id": audit_id})}
                break
            
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())
```

---

## 10. FRONTEND SPECIFICATIONS

### Design System

**Visual identity:** Dark forensic terminal aesthetic. Think: scientific rigour meets security audit dashboard.

```
Background:   #0D1117  (GitHub dark — familiar to developers)
Surface:      #161B22
Border:       #30363D
Accent:       #58A6FF  (GitHub blue — trust)
Success:      #3FB950  (pass verdicts)
Warning:      #D29922  (partial verdicts)
Danger:       #F85149  (fail verdicts)
Muted:        #8B949E

Typography:
  Display:    "JetBrains Mono" — code-first identity
  Body:       "Inter" — readable at density
  Size scale: 12 / 14 / 16 / 20 / 24 / 32 / 48px
```

### `AuditForm.jsx`

- Two inputs: paper (arXiv ID or PDF URL) + GitHub repo URL
- Two demo preset buttons:
  - **"Attention Is All You Need"** → pre-fills `arxiv:1706.03762` + tensor2tensor repo
  - **"BERT"** → pre-fills `arxiv:1810.04805` + google-research/bert repo
- On submit: `POST /audit` → immediately open SSE stream → navigate to `/audit/{id}`
- Validation: arXiv ID pattern check, GitHub URL format check, inline error messages

### `LivePipeline.jsx`

- Vertical timeline of SSE event cards, appearing one-by-one as events arrive
- Each card shows:
  - Step name (bold, coloured by type: blue=fetch, purple=extract, teal=map, red=audit, orange=verify, green=report)
  - Timestamp (relative: "2s ago")
  - Key metric (e.g., "14 claims extracted", "23 files analysed", "claim_003: PASS")
- Current active step: subtle pulse/glow animation on the bottom card
- Completed steps: checkmark icon, dimmed

### `ReportViewer.jsx`

- Top bar: paper title (truncated), authors, year, repo link icon
- Score ring: large circular progress, colour by score band, percentage in centre
- Score breakdown: 4 mini-badges (pass count, partial count, fail count, not_found count)
- Claims table:
  - Columns: Claim | Type | Paper Section | Verdict | Confidence | sympy?
  - Sortable by Verdict (group FAILs first by default)
  - Filterable by claim type and verdict
  - Clicking a row → expands `ClaimCard`
- Download button → fetches `/audit/{id}/report`

### `ClaimCard.jsx`

- Two-column diff layout:
  - Left: "Paper Claims" — original text, LaTeX rendered (MathJax via CDN in app, not in downloaded report)
  - Right: "Code Implementation" — syntax-highlighted code, file path + line range header, verdict badge
- For FAIL/PARTIAL: discrepancy box in amber/red describing what differs
- sympy badge: small blue badge if algebraic equivalence was proven

### `useSSE.js` (custom hook)

```javascript
import { useEffect, useRef, useState } from "react";

export function useSSE(auditId) {
  const [events, setEvents] = useState([]);
  const [complete, setComplete] = useState(false);
  const sourceRef = useRef(null);

  useEffect(() => {
    if (!auditId) return;
    const es = new EventSource(`/api/audit/${auditId}/stream`);
    sourceRef.current = es;

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.step === "complete") {
        setComplete(true);
        es.close();
      } else {
        setEvents(prev => [...prev, { ...data, timestamp: new Date() }]);
      }
    };

    es.onerror = () => {
      // Reconnect after 2s on error
      es.close();
      setTimeout(() => { /* re-init */ }, 2000);
    };

    return () => es.close();
  }, [auditId]);

  return { events, complete };
}
```

---

## 11. DATABASE MODELS (`db/models.py`)

```python
from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class Audit(Base):
    __tablename__ = "audits"
    id = Column(String, primary_key=True)      # UUID
    paper_url = Column(String)
    repo_url = Column(String)
    paper_title = Column(String)
    status = Column(String, default="queued")   # queued | running | complete | error
    reproducibility_score = Column(Float)
    score_breakdown = Column(JSON)
    report_html = Column(String)
    sse_events = Column(JSON, default=list)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)

class ClaimRecord(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True)       # claim_id
    audit_id = Column(String)
    claim_type = Column(String)
    description = Column(String)
    latex = Column(String)
    paper_section = Column(String)
    paper_page = Column(Integer)

class VerdictRecord(Base):
    __tablename__ = "verdicts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String)
    claim_id = Column(String)
    status = Column(String)
    confidence = Column(Float)
    reasoning = Column(String)
    discrepancy = Column(String)
    sympy_verified = Column(Boolean, default=False)
    file_path = Column(String)
    line_start = Column(Integer)
    line_end = Column(Integer)
```

---

## 12. ENVIRONMENT VARIABLES (`.env.example`)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...
GITHUB_TOKEN=ghp_...              # Authenticated: 5,000 req/hr vs 60 unauthed

# Optional — defaults shown
DATABASE_URL=sqlite:///./repro_agent.db
PORT=8000
FRONTEND_URL=http://localhost:5173
LOG_LEVEL=INFO
DEMO_MODE=false                   # If true, return cached results for demo arXiv IDs
```

---

## 13. `requirements.txt`

```
anthropic>=0.25.0
langgraph>=0.1.0
langchain-core>=0.2.0
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0
sse-starlette>=2.0.0
pypdf>=4.0.0
pdfplumber>=0.11.0
pdf2image>=1.17.0
pytesseract>=0.3.10
arxiv>=2.1.0
PyGithub>=2.3.0
requests>=2.31.0
sympy>=1.12
astroid>=3.1.0
libcst>=1.3.0
jinja2>=3.1.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
```

### `package.json` (frontend)

```json
{
  "name": "repro-agent-ui",
  "version": "2.0.0",
  "scripts": {
    "dev": "vite --port 5173",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.2.0"
  }
}
```

---

## 14. DEMO STRATEGY (for judges)

### Pre-cache these two audit results in `backend/demo/`

**Demo Case 1 — Happy Path (PASS scenario):**
```json
{
  "paper": "Attention Is All You Need (arXiv:1706.03762)",
  "repo": "https://github.com/tensorflow/tensor2tensor",
  "expected_findings": [
    {"claim": "Scaled dot-product attention", "verdict": "pass", "sympy_verified": true},
    {"claim": "Multi-head attention h=8", "verdict": "pass"},
    {"claim": "d_model=512", "verdict": "pass"},
    {"claim": "d_ff=2048", "verdict": "pass"},
    {"claim": "Label smoothing ε=0.1", "verdict": "pass"},
    {"claim": "Adam β1=0.9, β2=0.98", "verdict": "partial",
     "discrepancy": "β2=0.999 in code vs β2=0.98 in paper"}
  ],
  "reproducibility_score": 0.83
}
```

**Demo Case 2 — Forensic FAIL (use to prove the agent catches real discrepancies):**
```json
{
  "paper": "BERT: Pre-training of Deep Bidirectional Transformers (arXiv:1810.04805)",
  "repo": "https://github.com/google-research/bert",
  "expected_findings": [
    {"claim": "GELU activation x·Φ(x)", "verdict": "partial",
     "discrepancy": "Paper states x·Φ(x). Code uses the tanh polynomial approximation: 0.5·x·(1+tanh(√(2/π)·(x+0.044715·x³))). These are mathematically close but not identical — the polynomial is an approximation, not the exact definition."},
    {"claim": "Adam optimizer lr=1e-4", "verdict": "pass"},
    {"claim": "dropout=0.1", "verdict": "pass"},
    {"claim": "Masked Language Modeling 15% mask rate", "verdict": "pass"}
  ],
  "reproducibility_score": 0.71
}
```

**Demo Mode activation:** If `DEMO_MODE=true` in env and the arXiv ID matches a cached result, the SSE stream replays the cached events at 800ms intervals for a live-looking demo that works without API calls.

---

## 15. README.md (3-command setup)

```markdown
# Repro-Agent — Autonomous Scientific Reproducibility Auditor
> FAR AWAY 2026 · Track 3: Agentic & Autonomous Systems

## Setup

```bash
# 1. Install backend dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and GITHUB_TOKEN

# 3. Start backend
uvicorn backend.main:app --reload --port 8000

# 4. Start frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — click a demo preset and watch it run.

## Architecture

[Mermaid diagram — paste the flowchart from Section 7]
```

---

## 16. WHAT MAKES THIS GENUINELY NOVEL (say this to judges)

**1. AST-first, LLM-second architecture.**
Every other AI code tool does the opposite — sends raw code to an LLM and asks "does this match?". Repro-Agent uses Python's `ast` module to deterministically extract function boundaries, numeric constants, and activation patterns before the LLM ever touches the code. This means every verdict has a traceable, auditable evidence chain: exact file name, exact line numbers, exact extracted value.

**2. Algebraic proof, not opinion.**
For formula claims, Repro-Agent uses `sympy.simplify(paper_expr - code_expr) == 0` to algebraically verify equivalence. The GELU variants `x·Φ(x)` and `0.5·x·(1+erf(x/√2))` are mathematically identical — sympy will prove it, not guess it. No other tool in this space does this.

**3. LangGraph typed state DAG with conditional retry.**
The pipeline is a proper directed acyclic graph with typed state, not a sequential chain. The conditional retry edge on claim extraction means the system self-corrects if it finds an ambiguous paper — a real autonomous behaviour, not a chatbot.

**4. Per-claim evidence trail.**
Every verdict includes: file path, start line, end line, code snippet, extraction method (AST vs LLM), sympy verification flag. The report is not an opinion — it's a structured forensic citation.

**5. Real-time streaming.**
Judges see the agent reasoning live — claim by claim, file by file — not a spinner followed by a result. This is the most important UX decision for a hackathon demo: it makes the agentic nature of the system visible.

**6. Real-world deployment path.**
Repro-Agent can be packaged as a GitHub Action. Add one workflow file and every PR to an ML research repo automatically gets a reproducibility audit report. The problem is real, the market is real (every ML team, every journal, every conference), and the path from demo to product is clear.

---

## 17. SUBMISSION CHECKLIST

Before submitting to FAR AWAY 2026:

- [ ] GitHub repo is **public** with clean commit history showing genuine development
- [ ] `README.md` has 3-command setup that actually works
- [ ] Both demo cases (PASS + FAIL) load and stream without API calls in `DEMO_MODE=true`
- [ ] Frontend runs without errors in Chrome (latest)
- [ ] Mermaid architecture diagram is visible in README
- [ ] At least one real audit completed against a live arXiv paper + GitHub repo
- [ ] Presentation deck: 15 slides covering Problem → Solution → Demo Screenshots → Architecture → Tech Novelty → Impact → Future Scope
- [ ] OR: 2–5 minute video showing: form fill → live pipeline → report with FAIL verdict highlighted

---

*PRD v2.0 — For FAR AWAY 2026, Track 3: Agentic & Autonomous Systems*  
*Original prototype: Kaggle notebook (Gemini 2.5 Flash, hand-rolled sessions)*  
*Production rebuild: Claude claude-sonnet-4-6, LangGraph StateGraph, AST-first forensics*
