# RepoGuide — AI Developer Onboarding Agent

> **Hackathon:** IBM Bob 2.0 Hackathon
> **Hackathon Dates:** September 25–27, 2026
> **Project:** RepoGuide
> **Version:** 2.0
> **Architecture:** React + FastAPI + Supabase PostgreSQL
> **Core Idea:** From unfamiliar codebase to first contribution.

---

# 1. Project Vision

RepoGuide is an AI-powered developer onboarding agent that helps developers understand unfamiliar software repositories.

A developer provides a GitHub repository URL.

RepoGuide analyzes the repository and produces an interactive onboarding experience:

```text
GitHub Repository
        ↓
Repository Ingestion
        ↓
Repository Analysis
        ↓
Project Overview
        ↓
Architecture Understanding
        ↓
Important Files
        ↓
Setup Guide
        ↓
Repository Q&A
        ↓
First Contribution Recommendation
        ↓
Implementation Guidance
```

The central product promise is:

> **From unfamiliar codebase to first contribution.**

---

# 2. Problem

Developers joining an unfamiliar project often spend significant time:

* Reading thousands of lines of code
* Searching through directories
* Understanding project architecture
* Finding the application entry point
* Understanding dependencies
* Learning how to run the project
* Finding relevant files
* Understanding unfamiliar modules
* Finding beginner-friendly issues
* Figuring out where to make their first change

Existing documentation may be:

* Incomplete
* Outdated
* Scattered
* Too technical for newcomers
* Not connected to the actual source code

RepoGuide aims to make repository onboarding interactive and repository-specific.

---

# 3. Target User

Primary user:

> A developer who has received an unfamiliar GitHub repository and needs to understand it quickly.

Examples:

* New team member
* Open-source contributor
* University project member
* Intern
* Junior developer
* Hackathon teammate
* Developer joining an existing codebase

---

# 4. Core User Journey

The complete MVP journey should be:

```text
1. User opens RepoGuide
        ↓
2. User enters GitHub repository URL
        ↓
3. RepoGuide fetches repository
        ↓
4. Repository is scanned
        ↓
5. AI analyzes repository
        ↓
6. User sees project overview
        ↓
7. User explores architecture
        ↓
8. User reads setup guide
        ↓
9. User asks repository-specific questions
        ↓
10. User asks for a first contribution
        ↓
11. RepoGuide recommends a task
        ↓
12. RepoGuide explains implementation approach
```

---

# 5. Technology Stack

## Frontend

```text
React
Vite
TypeScript
CSS
```

Optional UI libraries may be added if they accelerate development.

---

## Backend

```text
Python
FastAPI
Pydantic
Uvicorn
```

---

## Database

```text
Supabase
PostgreSQL
```

Supabase will provide:

* PostgreSQL database
* Database API
* Database dashboard
* Optional authentication if required later
* Hosted database
* Secure environment-based configuration

---

## Repository Integration

```text
GitHub
GitHub API
Git
```

---

## AI

```text
IBM Bob 2.0
```

Any additional model/API should only be used if permitted by the hackathon rules and if technically necessary.

---

# 6. High-Level Architecture

```text
                         ┌───────────────────┐
                         │       User        │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   React Frontend  │
                         │      Vite         │
                         └─────────┬─────────┘
                                   │
                              REST API
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   FastAPI Backend │
                         └─────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
       ┌─────────────┐      ┌─────────────┐     ┌──────────────┐
       │   GitHub    │      │ AI / Agent  │     │   Supabase   │
       │ Repository  │      │ Processing   │     │ PostgreSQL   │
       └─────────────┘      └─────────────┘     └──────────────┘
```

---

# 7. Important Architectural Principle

Supabase is the persistence layer.

FastAPI is the application/business logic layer.

React is the user interface.

The AI agent is the intelligence layer.

GitHub is the source-code source.

Therefore:

```text
React
  ↓
FastAPI
  ↓
┌───────────────┬───────────────┐
│               │               │
GitHub          AI              Supabase
```

Do not connect the React frontend directly to sensitive backend services.

---

# 8. Project Structure

The final repository should look approximately like:

```text
repoguide/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── repositories.py
│   │   │   ├── analyses.py
│   │   │   ├── questions.py
│   │   │   └── contributions.py
│   │   │
│   │   ├── services/
│   │   │   ├── github_service.py
│   │   │   ├── repository_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── question_service.py
│   │   │   └── contribution_service.py
│   │   │
│   │   ├── database/
│   │   │   ├── supabase.py
│   │   │   └── repositories.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── utils/
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── database.md
│   └── development.md
│
├── screenshots/
│   └── bob/
│
├── sample-repositories/
│
├── .env.example
├── .gitignore
├── README.md
├── plan.md
└── docker-compose.yml
```

---

# 9. Supabase Database Design

The database should remain simple.

Do not over-engineer the database.

---

# 10. `repositories` Table

Purpose:

Store repositories analyzed by RepoGuide.

Suggested schema:

```sql
create table repositories (
    id uuid primary key default gen_random_uuid(),

    github_url text not null,

    owner text,
    name text,

    description text,

    default_branch text,

    language text,

    status text default 'pending',

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

Possible status values:

```text
pending
cloning
scanning
analyzing
completed
failed
```

---

# 11. `repository_files` Table

Purpose:

Store metadata about repository files.

```sql
create table repository_files (
    id uuid primary key default gen_random_uuid(),

    repository_id uuid
        references repositories(id)
        on delete cascade,

    file_path text not null,

    file_name text,

    extension text,

    language text,

    file_size integer,

    is_directory boolean default false,

    created_at timestamptz default now()
);
```

Do not automatically store every source file's full content in PostgreSQL.

Repository source code should primarily be processed by the backend.

---

# 12. `analyses` Table

Purpose:

Store AI-generated repository analysis.

```sql
create table analyses (
    id uuid primary key default gen_random_uuid(),

    repository_id uuid
        references repositories(id)
        on delete cascade,

    project_summary text,

    architecture text,

    setup_guide text,

    important_files jsonb,

    technologies jsonb,

    entry_points jsonb,

    dependencies jsonb,

    created_at timestamptz default now()
);
```

---

# 13. `questions` Table

Purpose:

Store repository Q&A sessions.

```sql
create table questions (
    id uuid primary key default gen_random_uuid(),

    repository_id uuid
        references repositories(id)
        on delete cascade,

    question text not null,

    answer text,

    referenced_files jsonb,

    created_at timestamptz default now()
);
```

---

# 14. `contributions` Table

Purpose:

Store recommended first contributions.

```sql
create table contributions (
    id uuid primary key default gen_random_uuid(),

    repository_id uuid
        references repositories(id)
        on delete cascade,

    title text,

    description text,

    difficulty text,

    why_suitable text,

    relevant_files jsonb,

    implementation_steps jsonb,

    tests_to_add jsonb,

    created_at timestamptz default now()
);
```

---

# 15. Database Relationships

```text
repositories
     │
     ├────────── repository_files
     │
     ├────────── analyses
     │
     ├────────── questions
     │
     └────────── contributions
```

One repository can have:

```text
Many files
Many questions
Many analyses
Many contribution recommendations
```

---

# 16. Supabase Security

Never commit:

```text
SUPABASE_SERVICE_ROLE_KEY
```

to GitHub.

Use:

```text
.env
```

and add:

```text
.env
```

to `.gitignore`.

Create:

```text
.env.example
```

containing only variable names.

Example:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

GITHUB_TOKEN=

AI_API_KEY=

FRONTEND_URL=
```

---

# 17. Backend Configuration

Create:

```text
backend/app/config.py
```

The configuration should load environment variables.

Conceptually:

```text
Environment
      ↓
Configuration
      ↓
Supabase Client
      ↓
Services
```

Do not hardcode credentials.

---

# 18. Supabase Connection

Create:

```text
backend/app/database/supabase.py
```

Responsibilities:

* Initialize Supabase client
* Expose database connection
* Handle configuration
* Avoid exposing credentials to frontend

---

# 19. Repository API

Create:

```text
POST /api/repositories
```

Request:

```json
{
  "github_url": "https://github.com/example/project"
}
```

Response:

```json
{
  "id": "repository-id",
  "github_url": "https://github.com/example/project",
  "status": "pending"
}
```

---

# 20. Repository Status API

Create:

```text
GET /api/repositories/{repository_id}
```

Response:

```json
{
  "id": "repository-id",
  "name": "example-project",
  "status": "completed"
}
```

---

# 21. Analysis API

Create:

```text
POST /api/repositories/{repository_id}/analyze
```

This endpoint starts repository analysis.

During the hackathon it should eventually perform:

```text
Repository
    ↓
File scanning
    ↓
Context extraction
    ↓
AI analysis
    ↓
Database storage
```

---

# 22. Analysis Retrieval API

Create:

```text
GET /api/repositories/{repository_id}/analysis
```

Response should contain:

```text
Project summary
Architecture
Technologies
Important files
Entry points
Dependencies
Setup instructions
```

---

# 23. Q&A API

Create:

```text
POST /api/repositories/{repository_id}/questions
```

Request:

```json
{
  "question": "How does authentication work?"
}
```

Response:

```json
{
  "answer": "...",
  "referenced_files": [
    "src/auth/service.py",
    "src/auth/routes.py"
  ]
}
```

---

# 24. Contribution API

Create:

```text
POST /api/repositories/{repository_id}/contributions/generate
```

The agent should analyze the repository and generate a suitable first contribution.

---

# 25. Contribution Retrieval API

Create:

```text
GET /api/repositories/{repository_id}/contributions
```

Response:

```json
{
  "title": "...",
  "difficulty": "Beginner",
  "why_suitable": "...",
  "relevant_files": [],
  "implementation_steps": [],
  "tests_to_add": []
}
```

---

# 26. Health Check

Create:

```text
GET /health
```

Expected:

```json
{
  "status": "ok"
}
```

Use this for deployment monitoring.

---

# 27. Frontend Routes

Create:

```text
/
```

Landing page.

```text
/repository
```

Repository input.

```text
/repository/:id
```

Repository dashboard.

```text
/repository/:id/architecture
```

Architecture.

```text
/repository/:id/setup
```

Setup guide.

```text
/repository/:id/ask
```

Repository Q&A.

```text
/repository/:id/contribution
```

First contribution.

---

# 28. Frontend Components

Create reusable components:

```text
Navbar
Sidebar
RepositoryInput
RepositoryCard
StatusIndicator
AnalysisCard
ArchitectureView
FileTree
SetupGuide
ChatInterface
QuestionInput
AnswerCard
ContributionCard
LoadingState
ErrorState
CodeReference
```

---

# 29. Repository Input UI

The main action should be:

```text
Analyze a Repository

GitHub URL

[________________________________]

[ Analyze Repository ]
```

Validate:

* URL exists
* URL is a GitHub URL
* Repository path is valid

---

# 30. Analysis Loading UI

Display progress:

```text
Connecting to repository...
        ↓
Scanning files...
        ↓
Understanding project structure...
        ↓
Analyzing architecture...
        ↓
Generating onboarding guide...
```

This creates a clear user experience.

---

# 31. Repository Dashboard

Display:

```text
Repository Name

Description

Primary Language

Technologies

Repository Status
```

Then navigation:

```text
Overview
Architecture
Files
Setup
Ask RepoGuide
First Contribution
```

---

# 32. Architecture Page

Display:

```text
Project Architecture

Overview

Components

Data Flow

Important Modules
```

The initial implementation may use structured text.

An interactive diagram can be added later if time permits.

---

# 33. Important Files

Show:

```text
File
Purpose
Why Important
```

Example:

```text
src/main.py

Application entry point.

Starts the FastAPI application and
registers API routes.
```

---

# 34. Setup Guide

Display generated instructions:

```text
Prerequisites

Installation

Environment Variables

Database Setup

Running the Application

Testing

Common Problems
```

Each instruction should be grounded in repository evidence.

---

# 35. Q&A Interface

Create a chat interface:

```text
You:
How does authentication work?

RepoGuide:
Authentication starts in...
Relevant files:
- src/auth/routes.py
- src/auth/service.py
```

Include file references wherever possible.

---

# 36. First Contribution Interface

Display:

```text
Find My First Contribution
```

Then:

```text
Recommended Task

Difficulty

Why this task?

Relevant files

Implementation steps

Tests to add
```

---

# 37. AI Repository Analysis

This is a core hackathon feature.

The analysis should identify:

```text
Project purpose
Languages
Frameworks
Architecture
Entry points
Important modules
Dependencies
Configuration
Tests
Potential documentation gaps
```

The analysis should be based on the actual repository.

---

# 38. Repository Context Pipeline

The backend should eventually implement:

```text
GitHub URL
      ↓
Repository download
      ↓
File discovery
      ↓
File filtering
      ↓
Language detection
      ↓
Important file selection
      ↓
Context construction
      ↓
AI analysis
```

---

# 39. File Filtering Rules

Ignore:

```text
.git/
node_modules/
dist/
build/
__pycache__/
coverage/
.venv/
venv/
.env
*.lock
large binary files
generated files
```

The filtering system should be configurable.

---

# 40. Repository Size Protection

Do not blindly process an unlimited repository.

Implement limits such as:

```text
Maximum repository size
Maximum individual file size
Maximum number of files
Maximum context size
```

If a repository is too large:

```text
Repository is too large for the current analysis limit.
Please try a smaller repository.
```

---

# 41. AI Context Strategy

Do not send the entire repository blindly to the model.

Construct structured context.

Example:

```text
Repository Metadata
+
Directory Structure
+
README
+
Configuration
+
Entry Points
+
Important Source Files
+
Tests
+
Dependency Files
```

Then provide additional relevant files when answering questions.

---

# 42. Repository Q&A Context Retrieval

For a question such as:

```text
How does authentication work?
```

the system should identify relevant files.

Conceptually:

```text
Question
   ↓
Relevant files/modules
   ↓
Repository context
   ↓
AI
   ↓
Answer
```

The answer should include references such as:

```text
src/auth/service.py
src/auth/routes.py
```

---

# 43. First Contribution Agent

The agent should consider:

```text
TODO comments
Issues
Documentation
Tests
Simple bugs
Small missing features
Code complexity
Number of files affected
Dependencies
```

It should prefer tasks that are understandable and relatively isolated.

The output should explain:

```text
Why this task?
Which files?
What needs changing?
What tests?
What risks?
```

---

# 44. Example Contribution

Example output:

```text
Improve validation for invalid login requests.

Difficulty:
Beginner

Relevant files:
src/auth/service.py
tests/test_auth.py

Why this task?

The existing login flow already contains validation
logic. The change is isolated and can be verified
with automated tests.

Implementation:

1. Inspect login validation.
2. Add invalid-input handling.
3. Add a unit test.
4. Run authentication tests.
```

---

# 45. Implementation Guidance

The user should be able to ask:

```text
How should I implement this?
```

The agent should return:

```text
Files to modify

Functions to inspect

Implementation steps

Potential side effects

Tests to add

Commands to run
```

---

# 46. AI Grounding Requirement

The agent must avoid generic answers whenever possible.

Bad:

```text
You should modify the authentication system
and add tests.
```

Better:

```text
The login request enters through
src/auth/routes.py and is validated by
validate_login() in src/auth/service.py.

The most isolated change is therefore in
src/auth/service.py.

Add a test to tests/test_auth.py.
```

Repository-specific evidence is important.

---

# 47. Hackathon Boundary

## Pre-Hackathon

The following can be prepared:

```text
React application
FastAPI application
Supabase project
Database schema
Database connection
API structure
Frontend UI
GitHub service skeleton
Repository scanning utilities
File filtering
Sample repository
Documentation
Tests
Deployment configuration
```

---

# 48. Core Hackathon Work

The following should be developed during the hackathon, subject to the official IBM Bob 2.0 rules:

```text
AI repository analysis
AI architecture understanding
Repository-grounded Q&A
AI setup-guide generation
AI first-contribution recommendation
AI implementation guidance
Complete AI workflow
```

The exact event rules should be checked at kickoff.

---

# 49. Pre-Hackathon Checklist

Before the competition begins:

```text
[ ] GitHub repository created

[ ] React + Vite initialized

[ ] TypeScript configured

[ ] FastAPI initialized

[ ] Supabase project created

[ ] Supabase PostgreSQL database configured

[ ] Database tables created

[ ] Supabase environment variables configured locally

[ ] FastAPI connected to Supabase

[ ] /health endpoint working

[ ] Repository creation API working

[ ] Repository retrieval API working

[ ] React connected to FastAPI

[ ] Repository input page complete

[ ] Dashboard UI complete

[ ] Architecture UI prepared

[ ] Setup UI prepared

[ ] Q&A UI prepared

[ ] First Contribution UI prepared

[ ] GitHub service skeleton created

[ ] Repository scanner created

[ ] File filtering created

[ ] Sample repository prepared

[ ] .env.example created

[ ] .gitignore configured

[ ] README created

[ ] plan.md created

[ ] Local frontend tested

[ ] Local backend tested

[ ] Supabase connection tested

[ ] Basic API tests passing
```

---

# 50. Hackathon Day 1

## Hours 0–2

Attend kickoff.

Confirm:

```text
Official rules
Submission requirements
Allowed technologies
Bob 2.0 requirements
Pre-existing code restrictions
AI/model requirements
```

Do not assume general hackathon guidance overrides the specific event rules.

---

## Hours 2–6

Use IBM Bob 2.0 to inspect the existing project.

Ask Bob to help with:

```text
Repository analysis architecture
Implementation planning
Missing components
Technical risks
```

Start implementing the AI core.

---

## Hours 6–12

Complete:

```text
Repository ingestion
+
Repository analysis
```

Goal:

```text
GitHub URL
    ↓
Repository
    ↓
AI analysis
    ↓
Project overview
```

---

## Hours 12–18

Implement:

```text
Architecture explanation
Important files
Technologies
Entry points
```

Store results in Supabase.

---

## Hours 18–24

Implement repository Q&A.

Goal:

```text
Question
    ↓
Relevant repository context
    ↓
AI
    ↓
Grounded answer
    ↓
File references
```

At the end of Day 1, the core product should already be usable.

---

# 51. Hackathon Day 2

## Hours 24–30

Implement:

```text
Setup Guide
```

The guide should be generated from repository evidence.

---

## Hours 30–36

Implement:

```text
First Contribution Agent
```

This is the main differentiating feature.

---

## Hours 36–40

Connect the entire experience:

```text
Repository
   ↓
Analysis
   ↓
Architecture
   ↓
Setup
   ↓
Q&A
   ↓
First Contribution
   ↓
Implementation Guidance
```

---

## Hours 40–42

Testing.

Test:

```text
Small repository
Medium repository
Python repository
JavaScript repository
Multi-language repository
Repository with weak documentation
Invalid repository
```

---

## Hours 42–44

Deployment.

Verify:

```text
Frontend URL
Backend API
Supabase
Repository analysis
AI
Q&A
First Contribution
```

---

## Hours 44–46

Prepare:

```text
Demo video
Presentation
Screenshots
Bob evidence
README
Project description
```

---

## Hours 46–48

Final submission.

Avoid major changes.

---

# 52. Supabase Production Checklist

Before deployment:

```text
[ ] Database schema verified

[ ] Tables accessible

[ ] Foreign keys verified

[ ] Environment variables configured

[ ] Service role key not exposed

[ ] No secrets committed

[ ] Error handling implemented

[ ] Database connection tested

[ ] Production backend connected

[ ] Production frontend connected
```

---

# 53. Environment Variables

Backend:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

GITHUB_TOKEN=

AI_API_KEY=

FRONTEND_URL=
```

Frontend:

```env
VITE_API_URL=
```

Never put the Supabase service-role key in the frontend.

---

# 54. Error Handling

Backend errors:

```text
400 Invalid repository URL
404 Repository not found
413 Repository too large
422 Invalid request
500 Analysis failure
503 AI service unavailable
```

Frontend should show human-readable messages.

---

# 55. Security Considerations

RepoGuide may process source code.

Therefore:

```text
Do not log secrets
Do not expose API keys
Do not expose service-role credentials
Do not store .env files
Do not unnecessarily persist source code
Do not execute arbitrary repository code
```

Important:

> RepoGuide should analyze source code as data. It should not automatically execute untrusted repository code.

---

# 56. GitHub Security

Do not request unnecessary GitHub permissions.

If public repositories are sufficient for the MVP, prioritize public repository analysis.

If authentication is added later, use the minimum required permissions.

---

# 57. Supabase Data Retention

Only store information required for the demo.

Potentially store:

```text
Repository metadata
Analysis results
Questions
Answers
Contribution recommendations
```

Avoid storing complete source-code files in Supabase unless necessary.

---

# 58. Performance Strategy

Prioritize the demo repository.

Use:

```text
Caching
File filtering
Relevant-file selection
Database persistence
Incremental analysis
```

Avoid analyzing unnecessary files.

---

# 59. MVP Priority

Priority order:

```text
1. Repository ingestion
2. AI repository analysis
3. Project overview
4. Architecture
5. Q&A
6. First contribution
7. Setup guide
8. Implementation guidance
9. UI polish
10. Extra features
```

---

# 60. Optional Features

Only implement after the MVP works.

```text
[ ] Interactive architecture diagram
[ ] Dependency graph
[ ] Documentation gap detection
[ ] GitHub Issues integration
[ ] Beginner / Developer / Expert modes
[ ] Test generation
[ ] Code change suggestions
[ ] Pull request preparation
[ ] Contribution progress
[ ] Repository health report
```

---

# 61. Features to Avoid

Do not spend hackathon time on:

```text
[ ] Complex authentication
[ ] Payment system
[ ] User profiles
[ ] Social features
[ ] Mobile application
[ ] Enterprise administration
[ ] Complex analytics
[ ] Large-scale multi-tenancy
```

These are outside the MVP.

---

# 62. Demo Repository

Select ONE repository for the final demonstration.

It should have:

```text
Multiple modules
Clear architecture
Several source files
Tests
Configuration
Dependencies
Potential contribution opportunities
```

Avoid a repository that is:

```text
Too small
Too huge
Extremely complex
Mostly generated code
Difficult to run
```

---

# 63. Golden Demo

The final demo should take approximately:

```text
3–5 minutes
```

Flow:

```text
1. Open RepoGuide

2. Enter GitHub repository

3. Click Analyze

4. Show project overview

5. Show architecture

6. Show important files

7. Show generated setup guide

8. Ask:
   "How does authentication work?"

9. Show repository-grounded answer

10. Click:
    Find My First Contribution

11. Show recommended task

12. Ask:
    "How should I implement this?"

13. Show implementation guidance

14. Explain how IBM Bob 2.0 helped create RepoGuide
```

---

# 64. Demo Story

Use this narrative:

> Imagine joining a software project you've never seen before.

> You receive a GitHub repository containing hundreds or thousands of files.

> Where do you start?

> RepoGuide analyzes the repository and creates an interactive onboarding experience.

> Instead of searching through the codebase manually, you can ask questions about the actual project.

> And instead of stopping at documentation, RepoGuide identifies a practical first contribution and explains how to approach it.

---

# 65. IBM Bob 2.0 Evidence

Capture genuine evidence of Bob 2.0 usage.

Examples:

```text
screenshots/bob/
│
├── repository-analysis.png
├── architecture-analysis.png
├── backend-development.png
├── frontend-development.png
├── debugging.png
├── testing.png
└── final-workflow.png
```

For every screenshot, understand:

```text
What task was given to Bob?
What did Bob change?
What was the result?
```

Do not fabricate evidence.

---

# 66. Git Commit Strategy

Use meaningful commits.

Example:

```text
chore: initialize RepoGuide
feat: add React application shell
feat: add FastAPI backend
feat: connect Supabase database
feat: add repository API
feat: add GitHub repository service
feat: add repository scanner
feat: add repository analysis
feat: add architecture generation
feat: add repository Q&A
feat: add setup guide
feat: add first contribution agent
feat: add implementation guidance
fix: improve repository context selection
test: add repository analysis tests
docs: update README
chore: prepare hackathon submission
```

Commit history should accurately represent actual development.

---

# 67. Testing Strategy

## Backend

Test:

```text
Repository validation
GitHub URL parsing
Supabase connection
Repository creation
Repository retrieval
Analysis storage
Question storage
Contribution storage
```

## Frontend

Test:

```text
Repository input
Loading state
Error state
Dashboard
Q&A
Contribution page
```

## AI

Test:

```text
Architecture accuracy
File references
Question relevance
Contribution relevance
Hallucination resistance
```

---

# 68. AI Evaluation

For the final demo repository, prepare a fixed set of questions.

Example:

```text
Q1:
What is the main entry point?

Q2:
How does authentication work?

Q3:
Where is the database configured?

Q4:
How would I add a new API endpoint?

Q5:
Which files should I modify to add a new feature?
```

Verify that the answers reference actual repository files.

---

# 69. First Contribution Evaluation

Prepare several possible contribution types:

```text
Documentation improvement
Simple bug fix
Test improvement
Small feature
Error handling
Validation improvement
```

The agent should provide a reason for its recommendation.

---

# 70. Final Product Architecture

The final system should conceptually operate as:

```text
                       USER
                         │
                         ▼
                ┌────────────────┐
                │ React Frontend │
                └───────┬────────┘
                        │
                        ▼
                ┌────────────────┐
                │ FastAPI API    │
                └───────┬────────┘
                        │
          ┌─────────────┼──────────────┐
          │             │              │
          ▼             ▼              ▼
      GitHub        AI Agent       Supabase
          │             │              │
          │             │              │
          └─────────────┼──────────────┘
                        │
                        ▼
              Developer Onboarding
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
         Understand   Ask       Contribute
```

---

# 71. Definition of Done

RepoGuide is considered MVP-complete when:

```text
[ ] User can enter GitHub URL

[ ] Repository can be fetched

[ ] Repository files can be scanned

[ ] Repository can be analyzed

[ ] Project overview is generated

[ ] Architecture explanation is generated

[ ] Important files are identified

[ ] Setup guide is generated

[ ] User can ask repository questions

[ ] Answers reference actual files

[ ] First contribution can be generated

[ ] Contribution includes relevant files

[ ] Contribution includes implementation steps

[ ] Supabase stores important results

[ ] React frontend works

[ ] FastAPI backend works

[ ] Production deployment works

[ ] Demo repository works reliably

[ ] Bob 2.0 contribution is documented

[ ] Video is recorded

[ ] Slides are complete

[ ] Submission is complete
```

---

# 72. Main Technical Principle

Do not optimize for the number of features.

Optimize for this:

```text
Repository
     ↓
Understanding
     ↓
Question
     ↓
Answer
     ↓
Contribution
```

This should be the strongest part of the project.

---

# 73. Final Product Statement

> **RepoGuide is an AI-powered developer onboarding agent that turns an unfamiliar GitHub repository into an interactive onboarding experience. It analyzes project structure, explains architecture, answers repository-specific questions, generates setup guidance, and helps developers identify and approach their first contribution.**

---

# 74. Final Development Principle

The project should follow:

```text
Simple Infrastructure
        +
Strong AI Workflow
        +
Clear User Experience
        +
Real Repository
        =
Strong Hackathon Prototype
```

Do not attempt to build a complete enterprise developer platform.

Build one excellent onboarding experience.

---

# 75. Final Golden Path

The entire product should ultimately feel like:

```text
┌──────────────────────────────┐
│          RepoGuide           │
│                              │
│  Understand any codebase.    │
│  Make your first contribution│
│  faster.                     │
│                              │
│ [ GitHub Repository URL ]    │
│                              │
│       [ Analyze ]            │
└──────────────┬───────────────┘
               │
               ▼
        Repository Analysis
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
   Overview  Architecture  Setup
       │
       ▼
   Ask RepoGuide
       │
       ▼
 First Contribution
       │
       ▼
Implementation Guidance
```

# END OF PLAN
