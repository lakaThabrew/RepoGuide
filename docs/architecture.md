# Architecture

## Overview
RepoGuide is an AI-powered developer onboarding agent that helps developers understand unfamiliar software repositories.

## System Architecture

```text
React Frontend
      │
      ▼
FastAPI Backend
      │
 ┌────┼──────────────┐
 ▼    ▼              ▼
Repo  Analysis       AI
     Services       Provider
      │
      ▼
Supabase
```

## Major Components
- Frontend: React application with Vite, TypeScript.
- Backend: FastAPI application providing REST API.
- Repository Services: Ingestion and scanning of GitHub repositories.
- Analysis Service: File scanning, context extraction, architecture and setup understanding.
- Q&A Service: Repository-grounded chat and file reference.
- First Contribution Service: Generation of recommended beginner tasks.

## Security Architecture
- Path validation and secret redaction.
- Maximum file sizes and repository size limits.
- No repository code execution.
- Forbidden files (e.g., .env) are blocked.

## Data Flow
Repository Onboarding Flow: GitHub URL -> Clone/Ingest -> Scan files -> Generate Analysis -> View in UI.
