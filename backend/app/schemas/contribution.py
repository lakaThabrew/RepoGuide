"""
Pydantic schemas for the contribution recommendation feature.

These models represent a structured first-contribution recommendation produced
by the deterministic contribution analysis engine.

Maps to the contributions table columns:
  repository_id -> str
  candidates    -> jsonb  (list[ContributionCandidate])
  recommended_ids -> jsonb (list of candidate IDs)
  is_deterministic -> bool
  analysis_id   -> str (FK reference to analyses row)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Candidate primitives
# ---------------------------------------------------------------------------

ContributionType = Literal[
    "documentation",
    "testing",
    "developer_experience",
    "maintenance",
    "feature",
]

Difficulty = Literal["beginner", "intermediate", "advanced"]

Impact = Literal["low", "medium", "high"]


class FileToRead(BaseModel):
    """A file the contributor should read as preparation."""
    file_path: str
    reason: str                       # why this file matters for this contribution


class ContributionEvidence(BaseModel):
    """A single piece of evidence that justifies the contribution candidate."""
    observation: str                  # what was observed in the repository
    source: str                       # where the observation came from (e.g. "test_files metadata")


class ContributionCandidate(BaseModel):
    """A single realistic first-contribution opportunity."""
    id: str                           # stable slug, e.g. "doc-readme-sections"
    title: str
    description: str
    type: ContributionType
    difficulty: Difficulty
    impact: Impact
    confidence: Literal["high", "medium", "low"]
    why_good_first_contribution: str  # evidence-based explanation
    files_to_read: list[FileToRead] = Field(default_factory=list)
    related_components: list[str] = Field(default_factory=list)
    evidence: list[ContributionEvidence] = Field(default_factory=list)
    suggested_steps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class ContributionResponse(BaseModel):
    """
    Response shape for GET /repositories/{id}/contributions.

    is_deterministic is True when no AI provider enriched the result.
    analysis_id is the ID of the analysis row used to generate candidates.
    """
    repository_id: str
    candidates: list[ContributionCandidate] = Field(default_factory=list)
    recommended_ids: list[str] = Field(default_factory=list)
    is_deterministic: bool = True
    analysis_id: Optional[str] = None
    generated_at: Optional[datetime] = None
    evidence_quality: Optional[str] = None
    status: str = "ok"
    error: Optional[str] = None


class ContributionGenerateResponse(BaseModel):
    """Response shape for POST …/contributions/generate."""
    message: str
    repository_id: str
    status: str
    candidates_count: Optional[int] = None
    error: Optional[str] = None
