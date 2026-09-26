"""
Pydantic schemas for the Setup Assistant feature.

The SetupGuide is persisted as JSON inside analyses.setup_guide (text column).
It is never stored as many relational tables — the whole guide is one JSONB blob.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

SetupConfidence = Literal["high", "medium", "low"]


class SetupCommand(BaseModel):
    """A single shell command with evidence and explanation."""
    command: str
    explanation: str
    evidence: list[str] = Field(default_factory=list)   # manifest/file names that back this up


class SetupPrerequisite(BaseModel):
    """A runtime / tool prerequisite detected from repository evidence."""
    name: str                                             # e.g. "Python", "Node.js"
    version_note: str                                     # exact version or "version not specified"
    evidence: list[str] = Field(default_factory=list)


class SetupSection(BaseModel):
    """A single section in the setup guide."""
    title: str
    description: str
    commands: list[SetupCommand] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class SetupWarning(BaseModel):
    """An uncertainty or caution flag with supporting evidence."""
    message: str
    evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level guide
# ---------------------------------------------------------------------------

class SetupGuide(BaseModel):
    """
    The complete setup guide for a repository.

    Sections are ordered to guide a developer from zero to running:
      1. prerequisites
      2. install_dependencies
      3. environment_configuration
      4. database_setup          (only when database evidence present)
      5. run_application
      6. verify_setup

    confidence reflects how well the indexed evidence supports the guide.
    warnings surface cautions the developer should be aware of.
    """
    repository_id: str
    generated_at: Optional[datetime] = None

    prerequisites: list[SetupPrerequisite] = Field(default_factory=list)
    install_dependencies: Optional[SetupSection] = None
    environment_configuration: Optional[SetupSection] = None
    database_setup: Optional[SetupSection] = None
    run_application: Optional[SetupSection] = None
    verify_setup: Optional[SetupSection] = None

    confidence: SetupConfidence = "low"
    warnings: list[SetupWarning] = Field(default_factory=list)

    # Indicates the guide was built without AI enrichment
    is_deterministic: bool = True


# ---------------------------------------------------------------------------
# API response / persistence wrappers
# ---------------------------------------------------------------------------

class SetupGuideResponse(BaseModel):
    """Response shape for GET /repositories/{id}/setup."""
    repository_id: str
    guide: Optional[SetupGuide] = None
    status: str = "ok"                    # ok | no_analysis | insufficient_evidence | error
    error: Optional[str] = None
    generated_at: Optional[datetime] = None


class SetupGenerateResponse(BaseModel):
    """Response shape for POST /repositories/{id}/setup/generate."""
    message: str
    repository_id: str
    status: str
    confidence: Optional[str] = None
    warnings_count: int = 0
    error: Optional[str] = None
