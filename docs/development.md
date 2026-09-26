# Development Guide

## Prerequisites
- Python 3.11+
- Node.js 20+
- Docker

## Local Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Local Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables
See `.env.example` in the root directory. Configure Supabase and AI keys appropriately.

## Docker
Run the application using Docker Compose:
```bash
docker compose up --build
```

Stop the application:
```bash
docker compose down
```
