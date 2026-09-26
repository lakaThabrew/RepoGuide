# RepoGuide

> **RepoGuide helps developers go from an unfamiliar GitHub repository to their first contribution by explaining architecture, setup, source code, and contribution opportunities.**

Built for the **IBM Bob 2.0 Hackathon**, September 25–27, 2026.

---

## Problem

When a developer joins an unfamiliar project, they typically spend hours or days:

- Reading thousands of lines of code with no map
- Hunting for the application entry point
- Guessing how to install and run the project
- Not knowing which files matter and which are noise
- Unable to identify a safe, realistic first contribution

This friction slows onboarding, discourages open-source participation, and wastes experienced engineers' time on repetitive explanations.

---

## Solution

RepoGuide automates repository onboarding. Paste a public GitHub URL and RepoGuide:

1. **Ingests** the repository (shallow clone, file scan, metadata storage)
2. **Analyses** the codebase using deterministic evidence extraction — optionally enriched by IBM Bob 2.0
3. **Presents** a structured onboarding dashboard:
   - Project Overview (summary, tech stack, entry points, dependencies)
   - Architecture Explorer (components, relationships, reading order)
   - Setup Assistant (evidence-grounded install and run commands)
   - Code-Grounded Q&A (ask anything, get source-backed answers)
   - Source File Explorer (browse and inspect real source files)
   - First Contribution Assistant (beginner-friendly task with implementation steps)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Repository Ingestion** | Shallow-clones, scans, and indexes the repository file tree |
| **Repository Intelligence** | Deterministic evidence extraction from file metadata and manifest files |
| **Architecture Explorer** | Component map with data-flow relationships and reading order |
| **Setup Assistant** | Evidence-backed prerequisites, install commands, and run instructions |
| **Code-Grounded Q&A** | Intent-classified questions with source-file retrieval and snippets |
| **Source File Explorer** | Safe, read-only file browser with syntax highlighting |
| **First Contribution Assistant** | Ranked candidates with implementation steps grounded in real evidence |

---

## Architecture

```
React + TypeScript (Vite)
        ↓  HTTP via Vite proxy (/api)
FastAPI (Python)
        ↓  Supabase SDK
Supabase (PostgreSQL)
        ↓  GitHub REST API
GitHub
```

**Optional AI layer**: when `AI_API_KEY` is configured, IBM Bob 2.0 (or any OpenAI-compatible provider) enriches the project summary and Q&A answers. The system is fully functional without AI — all core features use deterministic evidence extraction.

---

## Security

RepoGuide treats all repository content as **untrusted data**:

- **No code execution** — repository source is never run
- **Path traversal protection** — all user-supplied paths validated against `..`, encoded variants, absolute paths, and null bytes
- **Forbidden-file filtering** — `.env`, `id_rsa`, `.npmrc`, private keys, and certificates are never served or referenced
- **Source-size limits** — files over 500 KB are rejected; Q&A context capped at 30 000 chars total
- **Binary detection** — binary files detected via null-byte probe and rejected before display
- **Prompt-injection protection** — injection patterns in questions are rejected; source content in AI context is labelled as DATA and sanitised
- **Secrets never exposed** — GitHub tokens and API keys are never included in responses, logs, or error messages
- **Deterministic-first architecture** — AI is optional; deterministic answers skip AI entirely

---

## Local Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase project (free tier works)
- A GitHub personal access token (for higher rate limits)
- An IBM Bob 2.0 API key (optional — enables AI enrichment)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/RepoGuide.git
cd RepoGuide
```

### 2. Configure environment variables

```bash
cp .env.example backend/.env
```

Edit `backend/.env` and fill in:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

GITHUB_TOKEN=your-github-token

# Optional — enables AI enrichment via IBM Bob 2.0
AI_API_KEY=your-bob-api-key
AI_BASE_URL=https://your-bob-inference-endpoint
AI_MODEL=your-model-id
AI_TIMEOUT=60

FRONTEND_URL=http://localhost:5173
```

### 3. Set up the database

Run [`database_schema.sql`](database_schema.sql) against your Supabase project using the SQL editor in the Supabase dashboard. This creates the five tables: `repositories`, `repository_files`, `analyses`, `questions`, `contributions`.

### 4. Start the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/repositories` | Register and ingest a GitHub repository |
| GET | `/api/repositories/{id}` | Get repository metadata and status |
| POST | `/api/repositories/{id}/analyze` | Run repository analysis |
| GET | `/api/repositories/{id}/analysis` | Get stored analysis results |
| GET | `/api/repositories/{id}/architecture` | Get derived architecture data |
| POST | `/api/repositories/{id}/questions` | Ask a grounded question |
| GET | `/api/repositories/{id}/setup` | Get or generate setup guide |
| POST | `/api/repositories/{id}/setup/generate` | (Re)generate setup guide |
| GET | `/api/repositories/{id}/contributions` | Get contribution recommendations |
| POST | `/api/repositories/{id}/contributions/generate` | (Re)generate contributions |
| GET | `/api/repositories/{id}/files` | List repository file tree |
| GET | `/api/repositories/{id}/files/content?path=…` | Get file content |

---

## Project Structure

```
RepoGuide/
├── frontend/                  React + Vite + TypeScript
│   └── src/
│       ├── pages/             Route-level page components
│       ├── components/        Shared components (Navbar, Footer)
│       └── services/api.ts    Typed API service layer
├── backend/                   Python + FastAPI
│   └── app/
│       ├── api/               Route handlers (repositories, analyses, questions, files, setup, contributions)
│       ├── services/          Business logic (analysis, question, setup, contribution, github, ai_provider)
│       ├── schemas/           Pydantic models
│       └── database/          Supabase client
├── database_schema.sql        PostgreSQL schema for Supabase
├── .env.example               Environment variable template
└── plan.md                    Full project specification
```

---

## Testing

### Backend

```bash
cd backend
venv\Scripts\activate
pytest tests/ -v
```

**Current baseline: 613 tests passing.**

Test suite covers:
- Repository ingestion and file scanning
- Analysis service (deterministic evidence extraction)
- Architecture derivation
- Q&A intent classification, evidence retrieval, scoring, and context budgets
- Setup guide generation
- Contribution recommendation engine
- File explorer (path validation, binary detection, traversal rejection)
- Security properties (forbidden files, prompt injection, path encoding)
- AI provider (null provider, Bob provider, error handling)

### Frontend

```bash
cd frontend
npx tsc --noEmit    # TypeScript: 0 errors
npm run build       # Vite production build: successful
```

---

## Demo Flow

See [`docs/demo.md`](docs/demo.md) for a judge-friendly 3–5 minute walkthrough.

**Quick summary:**
1. Paste a GitHub repository URL on the landing page
2. Watch automatic ingestion → click **Analyze**
3. Browse the Overview: tech stack, entry points, important files
4. Open Architecture: component diagram with evidence
5. Open Setup Guide: evidence-backed install commands
6. Ask: *"Where does the application start?"* → see source-backed answer
7. Click **View** on an evidence file → open in File Explorer
8. Open First Contribution → see recommended task with implementation steps

---

## Limitations

- **Public repositories only** — private GitHub repositories require a token with appropriate access
- **Analysis time** — repository ingestion + analysis takes 30–90 seconds depending on repository size
- **File size cap** — files over 500 KB are not indexed for content preview
- **Maximum 300 files** — repositories with very large file trees are scanned up to 300 files
- **No real-time updates** — the dashboard does not poll for analysis progress; refresh manually
- **AI enrichment is optional** — without an API key, answers are deterministic (still accurate and evidence-backed)
- **No deployment infrastructure** — RepoGuide is a local-run prototype; production deployment is outside the hackathon scope

---

## IBM Bob 2.0 Usage

RepoGuide was **built using IBM Bob 2.0** as the core development agent throughout the project:

- Architecture design and technical specification
- FastAPI backend implementation (all 6 API modules)
- Deterministic intelligence engine (analysis, Q&A, setup, contributions)
- Security architecture (path validation, injection protection, forbidden-file filtering)
- Frontend implementation (React/TypeScript pages and components)
- Test suite development (613 tests)

IBM Bob 2.0 is also the **default AI inference backend** for production use. When `AI_API_KEY` is set to a Bob 2.0 API key and `AI_BASE_URL` points to the Bob inference endpoint, all AI enrichment (project summaries, architecture descriptions, Q&A answers) goes through Bob 2.0.

See the `bob_sessions/` directory for session evidence screenshots.
