"""
Pydantic schemas for the analyses table and evidence structures.

The top-level AnalysisResult maps 1-to-1 with the analyses table columns:
  project_summary -> str
  architecture    -> str  (JSON-serialised summary of structure)
  setup_guide     -> str  (not populated in this task)
  important_files -> jsonb  (list[FileEvidence])
  technologies    -> jsonb  (TechnologyFindings)
  entry_points    -> jsonb  (list[EntryPoint])
  dependencies    -> jsonb  (list[Dependency])
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence primitives
# ---------------------------------------------------------------------------

class FileEvidence(BaseModel):
    """A file that is significant to the analysis, with supporting evidence."""
    file_path: str
    reason: str
    symbol: Optional[str] = None          # function/class name if relevant
    confidence: Literal["high", "medium", "low"] = "medium"
    category: Optional[str] = None        # e.g. entry_point, configuration, API, etc.


class EntryPoint(BaseModel):
    """An application entry point discovered through evidence."""
    file_path: str
    kind: str                               # e.g. "web server", "cli", "lambda handler"
    symbol: Optional[str] = None
    evidence: str


class Dependency(BaseModel):
    """A dependency found in a manifest file."""
    name: str
    version: Optional[str] = None
    kind: Literal["runtime", "dev", "unknown"] = "unknown"
    source_file: str                        # e.g. requirements.txt, package.json


class RouteEvidence(BaseModel):
    """An API route discovered in source files."""
    method: Optional[str] = None            # GET / POST / … / unknown
    path: Optional[str] = None
    file_path: str
    symbol: Optional[str] = None
    evidence: str


# ---------------------------------------------------------------------------
# Technology findings — grouped, each item evidence-backed
# ---------------------------------------------------------------------------

class ArchitectureComponent(BaseModel):
    """A high-level architectural component identified in the repository."""
    name: str                              # e.g. "frontend", "backend/API"
    description: str
    evidence_files: list[str] = Field(default_factory=list)
    technology: Optional[str] = None       # primary technology/framework, e.g. "React + Vite"
    directories: list[str] = Field(default_factory=list)   # relevant dirs/files
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence: list[str] = Field(default_factory=list)      # human-readable evidence bullets


class ArchitectureRelationship(BaseModel):
    """An evidence-backed relationship between two architecture components."""
    source: str                            # source component name
    target: str                            # target component name
    relationship_type: str                 # e.g. "calls", "reads_from", "writes_to"
    evidence: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"


class ArchitectureData(BaseModel):
    """Complete architecture data produced from repository evidence."""
    components: list[ArchitectureComponent] = Field(default_factory=list)
    relationships: list[ArchitectureRelationship] = Field(default_factory=list)
    summary: str = ""                      # plain-text architecture summary
    reading_order: list[str] = Field(default_factory=list)  # ordered onboarding steps
    confidence: Literal["high", "medium", "low"] = "low"
    evidence_quality: Literal["sufficient", "partial", "insufficient"] = "insufficient"


class TechnologyFindings(BaseModel):
    """All technology signals extracted from repository files."""
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    runtimes: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    auth_signals: list[FileEvidence] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    deployment_files: list[str] = Field(default_factory=list)
    dev_commands: list[str] = Field(default_factory=list)
    api_routes: list[RouteEvidence] = Field(default_factory=list)
    backend_components: list[str] = Field(default_factory=list)
    frontend_components: list[str] = Field(default_factory=list)
    important_directories: list[str] = Field(default_factory=list)
    # Structured directory classifications
    source_directories: list[str] = Field(default_factory=list)
    test_directories: list[str] = Field(default_factory=list)
    doc_directories: list[str] = Field(default_factory=list)
    # High-level architecture components
    arch_components: list[ArchitectureComponent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level analysis result — maps to the analyses table row
# ---------------------------------------------------------------------------

class AnalysisResult(BaseModel):
    """
    The structured result produced by analysis_service.

    project_summary   -> analyses.project_summary (text)
    architecture      -> analyses.architecture    (text — JSON-encoded summary)
    important_files   -> analyses.important_files (jsonb)
    technologies      -> analyses.technologies    (jsonb)
    entry_points      -> analyses.entry_points    (jsonb)
    dependencies      -> analyses.dependencies    (jsonb)

    setup_guide is left NULL in this task (populated later).
    """
    project_summary: str
    architecture: str                       # human-readable structural summary
    important_files: list[FileEvidence] = Field(default_factory=list)
    technologies: TechnologyFindings = Field(default_factory=TechnologyFindings)
    entry_points: list[EntryPoint] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    evidence_quality: Literal["sufficient", "partial", "insufficient"] = "partial"


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    """Response shape for GET /repositories/{id}/analysis."""
    id: Optional[str] = None
    repository_id: str
    project_summary: Optional[str] = None
    architecture: Optional[str] = None
    setup_guide: Optional[str] = None
    important_files: Optional[Any] = None
    technologies: Optional[Any] = None
    entry_points: Optional[Any] = None
    dependencies: Optional[Any] = None
    created_at: Optional[datetime] = None


class AnalysisTriggerResponse(BaseModel):
    """Response shape for POST /repositories/{id}/analyze."""
    message: str
    repository_id: str
    status: str
    analysis_id: Optional[str] = None
    evidence_quality: Optional[str] = None
    error: Optional[str] = None


class ArchitectureResponse(BaseModel):
    """Response shape for GET /repositories/{id}/architecture."""
    repository_id: str
    architecture_data: Optional[ArchitectureData] = None
    status: str                            # "ready" | "no_analysis" | "insufficient"
    message: Optional[str] = None
