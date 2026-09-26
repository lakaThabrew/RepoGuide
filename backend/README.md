# Backend

FastAPI backend for RepoGuide. Provides REST APIs for repository ingestion, analysis, and Q&A.

## Directory Structure
- `app/`: Main application code, routes, and services.
- `tests/`: Unit and integration tests.

## Running Locally
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing
```bash
pytest
```

## Docker Usage
Built as part of the main `docker-compose.yml`. Runs on port 8000.
