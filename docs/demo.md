# RepoGuide — Demo Script

**Target audience:** Hackathon judges, technical evaluators
**Duration:** 3–5 minutes

---

## Setup (before demo)

- Backend running: `uvicorn app.main:app --reload` at `http://localhost:8000`
- Frontend running: `npm run dev` at `http://localhost:5173`
- Browser open to `http://localhost:5173`
- Choose a demo repository — suggestion: `https://github.com/tiangolo/fastapi` (small, well-structured)

---

## Step 1 — Introduce the problem (30 seconds)

> "Every developer has faced this: you're handed an unfamiliar codebase, and you have no idea where to start. Which files matter? How do you run it? Where's the entry point? What's a safe first contribution? RepoGuide solves this."

---

## Step 2 — Paste a GitHub repository (30 seconds)

1. In the landing page input, paste:
   ```
   https://github.com/tiangolo/fastapi
   ```
2. Click **Analyze**
3. Watch the status badge update: `pending → ingesting → scanned → analyzed`

> "RepoGuide just cloned the repository, scanned its files, and ran deterministic analysis. No AI is required — but if IBM Bob 2.0 is configured, it enriches the summary."

---

## Step 3 — Open the Overview (30 seconds)

Navigate to the **Overview** tab.

Point out:
- **Technology stack**: detected languages, frameworks, databases
- **Entry points**: where the application starts
- **Important files**: ranked by relevance with explanations
- **Dependencies**: parsed from manifest files

> "All of this is grounded in repository evidence — file metadata, manifest files, directory structure. Nothing is fabricated."

---

## Step 4 — Open Architecture (30 seconds)

Navigate to **Architecture**.

Point out:
- Component diagram (Frontend / Backend / Database layers)
- Data-flow relationships with evidence files
- Reading order recommendation

> "RepoGuide identifies architectural components from evidence — it doesn't guess."

---

## Step 5 — Open Setup Guide (30 seconds)

Navigate to **Setup Guide**, click **Generate Setup Guide**.

Point out:
- Prerequisites detected from `package.json`, `requirements.txt`, etc.
- Install commands with evidence citations
- Environment configuration section
- Run commands with explanations

> "Every command here is derived from repository files. Notice the evidence citations — you can verify every step."

---

## Step 6 — Ask a question (60 seconds)

Navigate to **Ask RepoGuide**.

**Question 1:**
```
Where does the application start?
```

Point out:
- Answer cites specific entry-point files
- Source snippets from actual repository files
- Click **View** on a source file → opens in File Explorer

**Question 2:**
```
How does the frontend communicate with the backend?
```

Point out:
- Answer identifies frontend/backend components
- Evidence references relevant files
- `is_deterministic` badge shows whether AI was used

> "Answers are source-backed. If evidence is insufficient, RepoGuide says so explicitly — it never fabricates."

---

## Step 7 — Open Source File Explorer (30 seconds)

Navigate to **Files** (reached via the View button or the Files tab).

Point out:
- File tree with directory expansion
- Category badges (entry_point, configuration, API, etc.)
- Click a file → view source code in read-only viewer
- Syntax highlighting by language
- File size and truncation indicators

> "RepoGuide never executes repository code. It fetches content read-only from GitHub and renders it as plain text."

---

## Step 8 — First Contribution (45 seconds)

Navigate to **First Contribution**, click **Find Contributions**.

Point out:
- Recommended first contribution with title, difficulty badge, type
- **Why this is a good first contribution** — grounded reasoning
- **Files to read first** — ordered reading path
- **Implementation steps** — concrete steps
- **Supporting evidence** — what the analysis found
- Other opportunities in the grid

> "These candidates are generated from real analysis evidence. No opportunity is suggested without a basis in the indexed repository data."

---

## Closing (15 seconds)

> "RepoGuide turns an unfamiliar repository into an actionable onboarding path — from zero to first contribution. Built with IBM Bob 2.0 as both the development agent and the optional inference backend."

---

## Demo questions to anticipate

**Q: What if there's no AI key?**
> All features still work. Analysis, Q&A, Setup, and Contributions all run deterministically from file evidence. AI adds richer prose descriptions but is never required.

**Q: How does it handle secrets?**
> Path traversal, `.env` files, private keys, and credential files are blocked at every layer — ingestion, file tree, content serving, and Q&A evidence retrieval.

**Q: How long does analysis take?**
> Ingestion + analysis takes 30–90 seconds depending on repository size. The shallow clone is discarded immediately after scanning.

**Q: Can it handle large repositories?**
> The scanner caps at 300 files and skips binary/build artifacts. Files over 500 KB are excluded from content preview.
