# RepoGuide

> **AI-powered developer onboarding agent** — *From unfamiliar codebase to first contribution.*

Built for the IBM Bob 2.0 Hackathon, September 25–27, 2026.

---

## What is RepoGuide?

RepoGuide helps developers understand unfamiliar GitHub repositories quickly. Paste a GitHub URL and get:

- 📖 **Project Overview** – Summary, technologies, and architecture
- 🏗️ **Architecture Map** – Components, data flow, entry points
- 💬 **Repository Q&A** – Ask anything, get grounded answers with file references
- ✨ **First Contribution** – AI-recommended beginner task with implementation steps

---

## Tech Stack

| Layer     | Technology              |
|-----------|-------------------------|
| Frontend  | React + Vite + TypeScript |
| Backend   | Python + FastAPI        |
| Database  | Supabase (PostgreSQL)   |
| AI        | IBM Bob 2.0             |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- A Supabase project

### 1. Clone the repository

```bash
git clone https://github.com/your-org/RepoGuide.git
cd RepoGuide
```

### 2. Configure environment variables

```bash
cp .env.example backend/.env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GITHUB_TOKEN
```

### 3. Start the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000
API docs: http://localhost:8000/docs

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Project Structure

```
RepoGuide/
├── frontend/          React + Vite + TypeScript
│   └── src/
│       ├── pages/     Route-level page components
│       └── services/  API service layer
├── backend/           Python + FastAPI
│   └── app/
│       ├── api/       Route handlers
│       ├── services/  Business logic
│       ├── database/  Supabase client
│       └── schemas/   Pydantic models
└── plan.md            Full project specification
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/repositories` | Register a GitHub repository |
| GET | `/api/repositories/{id}` | Get repository status |
| POST | `/api/repositories/{id}/analyze` | Start AI analysis |
| GET | `/api/repositories/{id}/analysis` | Get analysis results |
| POST | `/api/repositories/{id}/questions` | Ask a question |
| POST | `/api/repositories/{id}/contributions/generate` | Generate contribution |
| GET | `/api/repositories/{id}/contributions` | Get contribution recommendations |
