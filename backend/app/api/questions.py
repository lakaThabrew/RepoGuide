"""
questions.py — Q&A endpoint for repository-grounded developer questions.

POST /api/repositories/{repository_id}/questions
  - Accepts a developer question about the repository.
  - Returns a grounded answer with evidence references and optional source snippets.
  - Falls back to deterministic retrieval when no AI provider is configured.
  - Retrieves actual source-file content (up to 5 files, 30 000 chars total).

Errors returned as HTTP 4xx/5xx with a detail message.
Stack traces are never exposed.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from app.services import question_service
from app.services.repository_service import get_supabase

router = APIRouter(prefix="/api/repositories", tags=["questions"])


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class EvidenceItem(BaseModel):
    file_path: str
    reason: Optional[str] = None
    category: Optional[str] = None


class SourceFileItem(BaseModel):
    """A source file retrieved from GitHub with (optionally truncated) content."""
    file_path: str
    language: Optional[str] = None
    file_size: int = 0
    is_binary: bool = False
    truncated: bool = False
    snippet: Optional[str] = None   # first ~300 chars, HTML-escaped in frontend
    error: Optional[str] = None


class QuestionResponse(BaseModel):
    repository_id: str
    question: str
    answer: Optional[str] = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    source_files: list[SourceFileItem] = Field(default_factory=list)
    # Kept for backwards compatibility with the existing frontend
    referenced_files: list[str] = Field(default_factory=list)
    is_deterministic: bool = True
    intent: Optional[str] = None
    status: str = "answered"


@router.post(
    "/{repository_id}/questions",
    response_model=QuestionResponse,
    status_code=200,
)
def ask_question(repository_id: str, payload: QuestionRequest) -> QuestionResponse:
    """
    Ask a question about a repository.

    Returns a grounded answer based on the repository's stored analysis,
    optionally enriched with source-file content fetched from GitHub.

    - 404 if repository or analysis is not found.
    - 422 if the question is empty or too long (Pydantic validation).
    - 400 if the question contains disallowed patterns.
    - 500 on unexpected internal errors.
    """
    # Fetch owner/name from DB so the service can retrieve source files
    owner = ""
    repo_name = ""
    try:
        supabase = get_supabase()
        repo_response = (
            supabase.table("repositories")
            .select("owner,name")
            .eq("id", repository_id)
            .limit(1)
            .execute()
        )
        rows = repo_response.data or []
        if rows:
            owner = rows[0].get("owner") or ""
            repo_name = rows[0].get("name") or ""
    except Exception:
        # Non-fatal — service will fall back to metadata-only answers
        pass

    result = question_service.answer_question(
        repository_id,
        payload.question,
        owner=owner,
        repo_name=repo_name,
    )

    error = result.get("error")

    # Map service-layer errors to appropriate HTTP status codes
    if error:
        if "not found" in error.lower():
            raise HTTPException(status_code=404, detail=error)
        if "disallowed patterns" in error.lower() or "empty" in error.lower():
            raise HTTPException(status_code=400, detail=error)
        if "failed to retrieve" in error.lower():
            raise HTTPException(status_code=500, detail="Internal error. Please try again.")

    answer = result.get("answer")
    evidence_raw: list[dict] = result.get("evidence") or []
    source_files_raw: list[dict] = result.get("source_files") or []

    evidence_items = [
        EvidenceItem(
            file_path=e.get("file_path", ""),
            reason=e.get("reason"),
            category=e.get("category"),
        )
        for e in evidence_raw
        if isinstance(e, dict) and e.get("file_path")
    ]

    source_file_items = [
        SourceFileItem(
            file_path=sf.get("file_path", ""),
            language=sf.get("language"),
            file_size=sf.get("file_size", 0),
            is_binary=sf.get("is_binary", False),
            truncated=sf.get("truncated", False),
            snippet=sf.get("snippet"),
            error=sf.get("error"),
        )
        for sf in source_files_raw
        if isinstance(sf, dict) and sf.get("file_path")
    ]

    referenced_files = [e.file_path for e in evidence_items]

    return QuestionResponse(
        repository_id=repository_id,
        question=result.get("question", payload.question),
        answer=answer,
        evidence=evidence_items,
        source_files=source_file_items,
        referenced_files=referenced_files,
        is_deterministic=result.get("is_deterministic", True),
        intent=result.get("intent"),
        status="answered" if answer else "no_analysis",
    )
