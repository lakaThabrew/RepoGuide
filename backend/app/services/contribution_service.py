"""
contribution_service.py — Deterministic first-contribution recommendation engine.

Flow:
  1. Fetch repository record from Supabase
  2. Fetch stored analysis from Supabase
  3. Validate evidence quality
  4. Run candidate generators — each generator examines real analysis evidence
  5. Rank/filter candidates
  6. Select recommended first-contribution candidate(s)
  7. Persist results to the contributions table
  8. Return a structured ContributionResponse

DESIGN PRINCIPLES:
  - Every candidate MUST reference actual evidence from the analysis.
  - No file paths are invented; only files present in analysis metadata are used.
  - Confidence levels reflect how strongly evidence supports the candidate.
  - Security: repository content is never executed; no secrets are exposed.
  - Prompt injection in repository text cannot alter confidence/difficulty/type.

SECURITY:
  - Analysis metadata is treated as untrusted DATA.
  - Repository content is never executed.
  - Forbidden file patterns are filtered from all file references.
  - Secret/credential files are never referenced.
  - No stack traces are returned to callers.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.database.supabase import get_supabase
from app.schemas.contribution import (
    ContributionCandidate,
    ContributionEvidence,
    ContributionResponse,
    FileToRead,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CANDIDATES = 8
MIN_FILES_FOR_ANALYSIS = 3  # fewer files → insufficient evidence

# Files that must never appear in contribution file-to-read lists
_FORBIDDEN_FILE_RE = re.compile(
    r"(^|/)\.env$"
    r"|(^|/)\.env\.(local|production|staging|development|test)$"
    r"|(^|/)\.secret$"
    r"|(^|/)secrets\.(yml|yaml)$"
    r"|(^|/)id_rsa$"
    r"|(^|/)id_ed25519$"
    r"|(^|/)\.npmrc$"
    r"|(^|/)\.pypirc$",
    re.IGNORECASE,
)

# Suitability scoring weights for first-contribution selection
# Lower scores = more suitable for a first contribution
_DIFFICULTY_SCORE = {"beginner": 0, "intermediate": 1, "advanced": 2}
_IMPACT_SCORE = {"high": 0, "medium": 1, "low": 2}
_CONFIDENCE_SCORE = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

def _safe_path(path: str) -> bool:
    """Return True if the path is safe to expose in contribution output."""
    return not bool(_FORBIDDEN_FILE_RE.search(path))


def _filter_paths(paths: list[str]) -> list[str]:
    """Remove forbidden file paths from a list."""
    return [p for p in paths if _safe_path(p)]


def _safe_text(text: str) -> str:
    """
    Sanitise a string from analysis data before including in output.

    Removes prompt-injection-like phrases so that repository content
    cannot manipulate the contribution output text.
    The value of the candidate fields (type, difficulty, confidence) is
    always computed programmatically — never derived from repository text.
    """
    _INJECTION_RE = re.compile(
        r"ignore\s+(all\s+)?previous\s+instructions?"
        r"|new\s+system\s+prompt"
        r"|you\s+are\s+now"
        r"|pretend\s+you\s+are"
        r"|pretend.you.are"
        r"|act\s+as\s+(?:an?\s+)?(?:ai|assistant|gpt|claude)"
        r"|disregard\s+(all\s+)?prior",
        re.IGNORECASE,
    )
    return _INJECTION_RE.sub("[REDACTED]", text)


# ---------------------------------------------------------------------------
# Evidence helpers — operate on the stored analysis dict
# ---------------------------------------------------------------------------

def _get_important_files(analysis: dict) -> list[dict]:
    return [
        f for f in (analysis.get("important_files") or [])
        if isinstance(f, dict) and _safe_path(f.get("file_path", ""))
    ]


def _get_technologies(analysis: dict) -> dict:
    return analysis.get("technologies") or {}


def _get_test_files(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return _filter_paths(tech.get("test_files") or [])


def _get_test_directories(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return _filter_paths(tech.get("test_directories") or [])


def _get_doc_files(analysis: dict) -> list[dict]:
    return [
        f for f in _get_important_files(analysis)
        if f.get("category") == "documentation" and _safe_path(f.get("file_path", ""))
    ]


def _get_api_files(analysis: dict) -> list[dict]:
    return [
        f for f in _get_important_files(analysis)
        if f.get("category") in ("API", "entry_point") and _safe_path(f.get("file_path", ""))
    ]


def _get_service_files(analysis: dict) -> list[dict]:
    return [
        f for f in _get_important_files(analysis)
        if f.get("category") == "core service" and _safe_path(f.get("file_path", ""))
    ]


def _get_config_files(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return _filter_paths(tech.get("config_files") or [])


def _get_arch_components(analysis: dict) -> list[dict]:
    tech = _get_technologies(analysis)
    return tech.get("arch_components") or []


def _get_dev_commands(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return tech.get("dev_commands") or []


def _get_doc_directories(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return _filter_paths(tech.get("doc_directories") or [])


def _get_source_directories(analysis: dict) -> list[str]:
    tech = _get_technologies(analysis)
    return _filter_paths(tech.get("source_directories") or [])


def _get_languages(analysis: dict) -> list[str]:
    return _get_technologies(analysis).get("languages") or []


def _get_frameworks(analysis: dict) -> list[str]:
    return _get_technologies(analysis).get("frameworks") or []


def _total_file_count(analysis: dict) -> int:
    """Estimate total files from important files list + test files."""
    important = len(_get_important_files(analysis))
    test = len(_get_test_files(analysis))
    return important + test


# ---------------------------------------------------------------------------
# Candidate generators
# ---------------------------------------------------------------------------
# Each generator takes the analysis dict and returns a ContributionCandidate
# or None if there is insufficient evidence to produce a grounded candidate.
# ---------------------------------------------------------------------------

def _generate_documentation_candidate(analysis: dict) -> Optional[ContributionCandidate]:
    """
    Generate a documentation improvement candidate when evidence shows:
    - README.md exists (documentation is improvable, not absent)
    - OR significant modules exist with no obvious documentation
    - OR no CONTRIBUTING.md / documentation directories are present
    """
    doc_files = _get_doc_files(analysis)
    doc_dirs = _get_doc_directories(analysis)
    important_files = _get_important_files(analysis)
    languages = _get_languages(analysis)
    frameworks = _get_frameworks(analysis)

    has_readme = any(
        "readme" in f.get("file_path", "").lower()
        for f in doc_files
    )
    has_contributing = any(
        "contributing" in f.get("file_path", "").lower()
        for f in doc_files
    )
    has_service_files = bool(_get_service_files(analysis))
    has_api_files = bool(_get_api_files(analysis))

    # Need at least some code structure to suggest documentation
    has_significant_modules = has_service_files or has_api_files or len(important_files) >= 4

    if not has_significant_modules and not doc_files:
        return None

    evidence: list[ContributionEvidence] = []
    files_to_read: list[FileToRead] = []
    related_components: list[str] = []

    if has_readme:
        readme = next(
            (f["file_path"] for f in doc_files if "readme" in f["file_path"].lower()), None
        )
        evidence.append(ContributionEvidence(
            observation=f"README.md present at {readme} — can be reviewed for completeness",
            source="important_files metadata",
        ))
        if readme:
            files_to_read.append(FileToRead(
                file_path=readme,
                reason="Primary documentation file — assess what sections are present and what is missing",
            ))

    if not has_contributing:
        evidence.append(ContributionEvidence(
            observation="No CONTRIBUTING.md detected in repository metadata",
            source="important_files metadata",
        ))

    if doc_dirs:
        evidence.append(ContributionEvidence(
            observation=f"Documentation directory detected: {doc_dirs[0]}",
            source="doc_directories metadata",
        ))

    if languages:
        evidence.append(ContributionEvidence(
            observation=f"Repository uses {', '.join(languages[:3])} — setup documentation may be valuable",
            source="technologies metadata",
        ))

    if has_service_files:
        svc_files = _get_service_files(analysis)
        for sf in svc_files[:2]:
            fp = sf.get("file_path", "")
            if fp and _safe_path(fp):
                evidence.append(ContributionEvidence(
                    observation=f"Core service file {fp} exists — module documentation could be added",
                    source="important_files metadata",
                ))
                files_to_read.append(FileToRead(
                    file_path=fp,
                    reason="Core service module — understand what it does to document it accurately",
                ))
        related_components.append("services")

    if has_api_files:
        related_components.append("backend/API")

    # Always add config files as reading material if present
    config_files = _get_config_files(analysis)
    for cf in config_files[:2]:
        if _safe_path(cf):
            files_to_read.append(FileToRead(
                file_path=cf,
                reason="Configuration / dependency manifest — understand the project setup to document it",
            ))

    if not evidence:
        return None

    # Confidence: higher if README exists (easier to improve)
    confidence: str = "high" if has_readme else "medium"

    steps = [
        "Read the existing README.md (if present) to identify what is covered.",
        f"Review the project structure: {', '.join(_get_source_directories(analysis)[:3]) or 'source directories'}.",
    ]
    if not has_contributing:
        steps.append("Add a CONTRIBUTING.md explaining how to set up, test, and submit changes.")
    if frameworks:
        steps.append(f"Ensure the README covers how to run the {', '.join(frameworks[:2])} stack locally.")
    if _get_dev_commands(analysis):
        cmds = _get_dev_commands(analysis)[:2]
        steps.append(f"Document the available run commands: {'; '.join(cmds)}.")
    steps.append("Open a PR with your documentation improvements.")

    description_parts = ["Improve or extend the repository documentation."]
    if not has_contributing:
        description_parts.append("A CONTRIBUTING.md is not present.")
    if has_readme:
        description_parts.append("The README can be reviewed and extended with clearer setup instructions.")

    return ContributionCandidate(
        id="doc-improve-readme",
        title="Improve repository documentation",
        description=" ".join(description_parts),
        type="documentation",
        difficulty="beginner",
        impact="medium",
        confidence=confidence,  # type: ignore[arg-type]
        why_good_first_contribution=(
            "Documentation improvements are typically self-contained and do not require "
            "deep knowledge of the entire codebase. They are easy to review and have clear value."
        ),
        files_to_read=files_to_read[:5],
        related_components=list(dict.fromkeys(related_components)),
        evidence=evidence[:6],
        suggested_steps=steps,
    )


def _generate_testing_candidate(analysis: dict) -> Optional[ContributionCandidate]:
    """
    Generate a testing improvement candidate when evidence shows:
    - Service or API files with limited corresponding test coverage
    - A test directory / framework already present (so the contributor
      can follow the existing pattern)
    """
    test_files = _get_test_files(analysis)
    test_dirs = _get_test_directories(analysis)
    service_files = _get_service_files(analysis)
    api_files = _get_api_files(analysis)
    important_files = _get_important_files(analysis)

    has_test_infrastructure = bool(test_files or test_dirs)

    # No point suggesting tests if there are no existing service/API modules
    has_testable_modules = bool(service_files or api_files)

    if not has_testable_modules:
        return None

    evidence: list[ContributionEvidence] = []
    files_to_read: list[FileToRead] = []
    related_components: list[str] = []

    if has_test_infrastructure:
        if test_dirs:
            evidence.append(ContributionEvidence(
                observation=f"Test directory detected: {test_dirs[0]}",
                source="test_directories metadata",
            ))
        if test_files:
            evidence.append(ContributionEvidence(
                observation=f"{len(test_files)} test file(s) detected — existing test patterns to follow",
                source="test_files metadata",
            ))
            for tf in test_files[:2]:
                files_to_read.append(FileToRead(
                    file_path=tf,
                    reason="Existing test file — study the testing pattern and conventions used in this project",
                ))
    else:
        evidence.append(ContributionEvidence(
            observation="No test files detected in repository metadata — a test suite would add value",
            source="test_files metadata",
        ))

    if service_files:
        for sf in service_files[:2]:
            fp = sf.get("file_path", "")
            if fp:
                evidence.append(ContributionEvidence(
                    observation=f"Core service file {fp} exists without obvious corresponding test file",
                    source="important_files metadata",
                ))
                files_to_read.append(FileToRead(
                    file_path=fp,
                    reason="Service to be tested — understand its public interface before writing tests",
                ))
        related_components.append("services")

    if api_files:
        for af in api_files[:2]:
            fp = af.get("file_path", "")
            if fp:
                evidence.append(ContributionEvidence(
                    observation=f"API file {fp} detected — adding endpoint tests would improve confidence",
                    source="important_files metadata",
                ))
                files_to_read.append(FileToRead(
                    file_path=fp,
                    reason="API file — understand the route structure to write targeted endpoint tests",
                ))
        related_components.append("backend/API")

    if not evidence:
        return None

    # Confidence depends on whether test infrastructure already exists
    confidence: str = "high" if has_test_infrastructure else "medium"

    languages = _get_languages(analysis)
    frameworks = _get_frameworks(analysis)

    steps = [
        "Read the existing test files to understand the testing conventions used.",
        "Identify a service or API module that has limited test coverage based on the file list.",
    ]
    if "Python" in languages:
        steps.append("Add focused pytest tests for the identified module.")
    elif "TypeScript" in languages or "JavaScript" in languages:
        steps.append("Add focused tests using the detected test framework.")
    else:
        steps.append("Add focused tests for the identified module.")
    steps.append("Run the test suite to confirm new tests pass.")
    steps.append("Open a PR with the new tests.")

    # Narrow description based on evidence
    if has_test_infrastructure:
        desc = (
            "Add tests for an existing service or API module. "
            "The repository already has a test directory and test files to follow as a pattern."
        )
    else:
        desc = (
            "Introduce a basic test suite for a core module. "
            "The repository does not appear to have test files yet, making this a high-value addition."
        )

    return ContributionCandidate(
        id="testing-add-service-tests",
        title="Add tests for an existing module",
        description=desc,
        type="testing",
        difficulty="beginner" if has_test_infrastructure else "intermediate",
        impact="high",
        confidence=confidence,  # type: ignore[arg-type]
        why_good_first_contribution=(
            "Writing tests is a well-scoped task: you read the module, understand what it should do, "
            "and write assertions. If the project already has tests, you can follow the existing pattern. "
            "Tests are easy to review and improve the project's long-term maintainability."
        ),
        files_to_read=files_to_read[:6],
        related_components=list(dict.fromkeys(related_components)),
        evidence=evidence[:6],
        suggested_steps=steps,
    )


def _generate_devex_candidate(analysis: dict) -> Optional[ContributionCandidate]:
    """
    Generate a developer-experience candidate when evidence shows:
    - No dev commands detected in manifest files (setup is unclear)
    - OR config files present but no README or CONTRIBUTING
    - OR Dockerfile / deployment files with no obvious documentation
    """
    dev_commands = _get_dev_commands(analysis)
    config_files = _get_config_files(analysis)
    doc_files = _get_doc_files(analysis)
    deployment_files = _get_technologies(analysis).get("deployment_files") or []

    has_dev_commands = bool(dev_commands)
    has_readme = any("readme" in f.get("file_path", "").lower() for f in doc_files)
    has_deployment = bool(deployment_files)
    has_config = bool(config_files)

    evidence: list[ContributionEvidence] = []
    files_to_read: list[FileToRead] = []
    related_components: list[str] = []

    if not has_dev_commands and has_config:
        evidence.append(ContributionEvidence(
            observation="Configuration files present but no dev/run commands detected from manifests",
            source="dev_commands and config_files metadata",
        ))
        for cf in config_files[:2]:
            if _safe_path(cf):
                files_to_read.append(FileToRead(
                    file_path=cf,
                    reason="Configuration file — understand the project setup to document run commands",
                ))

    if has_deployment:
        safe_df = _filter_paths(deployment_files[:2])
        for df in safe_df:
            evidence.append(ContributionEvidence(
                observation=f"Deployment file {df} detected — a developer guide for local Docker setup could help",
                source="deployment_files metadata",
            ))
            files_to_read.append(FileToRead(
                file_path=df,
                reason="Deployment configuration — document how to run the project with Docker or similar",
            ))
        related_components.append("deployment/infrastructure")

    if not has_readme and has_config:
        evidence.append(ContributionEvidence(
            observation="No README detected but project configuration files are present",
            source="important_files and config_files metadata",
        ))

    languages = _get_languages(analysis)
    if languages:
        evidence.append(ContributionEvidence(
            observation=f"Project uses {', '.join(languages[:3])} — setup steps for these languages would be helpful",
            source="technologies metadata",
        ))

    if not evidence:
        return None

    steps = [
        "Review the project's configuration files and entry points.",
        "Try to follow the current setup process from scratch (or document your experience attempting it).",
    ]
    if has_dev_commands:
        steps.append(f"Document the run commands: {'; '.join(dev_commands[:3])}.")
    if has_deployment:
        steps.append("Add or improve Docker / deployment instructions in the README.")
    steps.append("Add a clear 'Getting Started' or 'Development' section to the README.")
    steps.append("Open a PR with your developer experience improvements.")

    return ContributionCandidate(
        id="devex-setup-guide",
        title="Improve developer setup and onboarding documentation",
        description=(
            "Add or improve the developer setup guide so that a new contributor can "
            "get the project running locally with minimal friction."
        ),
        type="developer_experience",
        difficulty="beginner",
        impact="medium",
        confidence="medium",
        why_good_first_contribution=(
            "This task requires no deep understanding of the application logic — "
            "only the ability to set up the project and document what you discover. "
            "It directly helps the next contributor and is easy to review."
        ),
        files_to_read=files_to_read[:5],
        related_components=list(dict.fromkeys(related_components)),
        evidence=evidence[:5],
        suggested_steps=steps,
    )


def _generate_maintenance_candidate(analysis: dict) -> Optional[ContributionCandidate]:
    """
    Generate a maintenance candidate only when there is concrete evidence such as:
    - Config files indicating linting/formatting that may need configuration
    - Missing standard project files (e.g. .gitignore, .editorconfig)
    - Presence of both lock files and manifest files suggesting dependency audit opportunity

    Does NOT invent maintenance issues.
    """
    config_files = _get_config_files(analysis)
    important_files = _get_important_files(analysis)
    languages = _get_languages(analysis)
    tech = _get_technologies(analysis)
    package_managers = tech.get("package_managers") or []

    # Look for lockfile + manifest pairs (evidence of dependency management)
    has_lockfile = any(
        "lock" in (f.get("file_path") or "").lower()
        for f in important_files
        if not f.get("is_directory")
    )
    has_manifest = any(
        "requirements.txt" in (f.get("file_path") or "").lower()
        or "package.json" in (f.get("file_path") or "").lower()
        or "go.mod" in (f.get("file_path") or "").lower()
        for f in important_files
    )

    # Look for linting config
    has_lint_config = any(
        any(linter in (cf or "").lower()
            for linter in ("eslint", "flake8", "pylint", "mypy", "ruff", "prettier"))
        for cf in config_files
    )

    # Only generate this candidate if there is clear dependency management evidence
    if not (has_manifest and (has_lockfile or package_managers)):
        return None

    evidence: list[ContributionEvidence] = []
    files_to_read: list[FileToRead] = []

    if has_manifest:
        manifest_files = [
            f for f in important_files
            if any(m in (f.get("file_path") or "").lower()
                   for m in ("requirements.txt", "package.json", "go.mod", "cargo.toml"))
        ]
        for mf in manifest_files[:2]:
            fp = mf.get("file_path", "")
            if fp and _safe_path(fp):
                evidence.append(ContributionEvidence(
                    observation=f"Dependency manifest {fp} found — dependency versions could be reviewed",
                    source="important_files metadata",
                ))
                files_to_read.append(FileToRead(
                    file_path=fp,
                    reason="Dependency manifest — review for outdated or pinned dependencies",
                ))

    if has_lint_config:
        evidence.append(ContributionEvidence(
            observation="Linting configuration detected — code style consistency can be verified",
            source="config_files metadata",
        ))

    if not evidence:
        return None

    steps = [
        "Review the dependency manifest files to identify outdated dependencies.",
        "Run the project's package manager update command (if documented).",
        "Check that tests still pass after updating dependencies.",
        "Open a PR with the dependency updates.",
    ]
    if has_lint_config:
        steps.insert(1, "Run the linting tools to identify and fix any code style issues.")

    return ContributionCandidate(
        id="maintenance-dependency-review",
        title="Review and update project dependencies",
        description=(
            "Review the project's dependency manifest(s) for outdated packages "
            "and update where appropriate."
        ),
        type="maintenance",
        difficulty="beginner",
        impact="low",
        confidence="medium",
        why_good_first_contribution=(
            "Dependency updates are well-scoped: you update a version, verify the tests pass, "
            "and open a PR. This is a common and well-understood contribution type."
        ),
        files_to_read=files_to_read[:4],
        related_components=[],
        evidence=evidence[:4],
        suggested_steps=steps,
    )


def _generate_feature_candidate(analysis: dict) -> Optional[ContributionCandidate]:
    """
    Generate a feature candidate ONLY when evidence explicitly suggests
    incomplete/stubbed functionality:
    - An arch component named after an unfinished area
    - A file path containing 'stub', 'placeholder', or 'todo' in its name
    - OR dev_commands contain references to tasks that imply feature gaps

    Does NOT invent feature ideas.
    Only returns a candidate if concrete evidence is available.
    """
    important_files = _get_important_files(analysis)
    tech = _get_technologies(analysis)

    # Look for stub/todo/placeholder in file paths
    stub_files = [
        f for f in important_files
        if any(
            kw in (f.get("file_path") or "").lower()
            for kw in ("stub", "placeholder", "todo", "fixme", "wip", "incomplete")
        )
        and _safe_path(f.get("file_path", ""))
    ]

    if not stub_files:
        return None

    evidence: list[ContributionEvidence] = []
    files_to_read: list[FileToRead] = []

    for sf in stub_files[:3]:
        fp = sf.get("file_path", "")
        evidence.append(ContributionEvidence(
            observation=f"File path '{fp}' contains a signal of incomplete functionality (stub/placeholder/todo/wip)",
            source="important_files file path metadata",
        ))
        files_to_read.append(FileToRead(
            file_path=fp,
            reason="Possibly incomplete module — read to understand what work is needed",
        ))

    if not evidence:
        return None

    return ContributionCandidate(
        id="feature-complete-stub",
        title="Complete a stubbed or placeholder module",
        description=(
            "One or more files in the repository have names that indicate incomplete or "
            "placeholder functionality. Completing this work could be a natural first contribution."
        ),
        type="feature",
        difficulty="intermediate",
        impact="medium",
        confidence="medium",
        why_good_first_contribution=(
            "Stubbed functionality often has clear requirements implied by its context. "
            "Reading the surrounding code gives you the specification; writing the implementation "
            "is a focused, bounded task."
        ),
        files_to_read=files_to_read[:4],
        related_components=[],
        evidence=evidence[:4],
        suggested_steps=[
            "Read the stub/placeholder file to understand what it is supposed to do.",
            "Review surrounding files and tests to understand the expected behaviour.",
            "Implement the missing functionality.",
            "Add or update tests to cover the new implementation.",
            "Open a PR with your changes.",
        ],
    )


# ---------------------------------------------------------------------------
# First-contribution suitability evaluator
# ---------------------------------------------------------------------------

def _score_candidate(candidate: ContributionCandidate, analysis: dict) -> float:
    """
    Compute a suitability score for first-contribution selection.

    Lower score = more suitable for a first contribution.

    Factors (all evidence-based):
    - Difficulty: beginner is best
    - Number of files to read: fewer = more focused
    - Whether the area has existing tests (confirms scope is bounded)
    - Whether the candidate is in a central or peripheral area
    - Confidence in the evidence

    This score is ONLY used for ranking — never exposed directly.
    """
    score = 0.0

    # Difficulty (most important factor)
    score += _DIFFICULTY_SCORE.get(candidate.difficulty, 2) * 3.0

    # Confidence in evidence
    score += _CONFIDENCE_SCORE.get(candidate.confidence, 2) * 1.5

    # Number of files to read (smaller reading path = more focused)
    score += min(len(candidate.files_to_read), 5) * 0.5

    # Bonus for types that are generally more self-contained
    if candidate.type == "documentation":
        score -= 1.0
    elif candidate.type == "testing":
        test_files = _get_test_files(analysis)
        if test_files:
            # Existing tests = can follow a pattern → more beginner friendly
            score -= 1.5
        else:
            score += 0.5

    return score


def _select_recommended(
    candidates: list[ContributionCandidate],
    analysis: dict,
) -> list[str]:
    """
    Select the best first-contribution candidate ID(s).

    Returns a list with ideally 1 candidate, possibly 2 if scores are close.
    Never returns an empty list when candidates exist.
    """
    if not candidates:
        return []

    scored = sorted(candidates, key=lambda c: _score_candidate(c, analysis))
    best = scored[0]
    result = [best.id]

    # If second candidate is within 1.5 score points, include it as an alternative
    if len(scored) >= 2:
        second_score = _score_candidate(scored[1], analysis)
        best_score = _score_candidate(best, analysis)
        if (second_score - best_score) <= 1.5:
            result.append(scored[1].id)

    return result


# ---------------------------------------------------------------------------
# Evidence quality assessment
# ---------------------------------------------------------------------------

def _assess_evidence_quality(analysis: dict) -> str:
    """
    Return 'sufficient', 'partial', or 'insufficient' based on available evidence.
    Mirrors the logic in analysis_service for consistency.
    """
    tech = _get_technologies(analysis)
    total = _total_file_count(analysis)

    if total == 0:
        return "insufficient"
    if total < MIN_FILES_FOR_ANALYSIS:
        return "partial"
    if tech.get("languages") and _get_important_files(analysis):
        return "sufficient"
    return "partial"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_contributions(
    repository_id: str,
    response: ContributionResponse,
    analysis_id: Optional[str],
) -> None:
    """
    Persist the contribution recommendation to the contributions table.

    Uses upsert so repeated calls do not create duplicate rows.
    Errors are logged but do not propagate — persistence is best-effort.
    """
    try:
        supabase = get_supabase()

        # Serialise candidates to plain dicts for JSONB storage
        row = {
            "repository_id": repository_id,
            "candidates": [c.model_dump() for c in response.candidates],
            "recommended_ids": response.recommended_ids,
            "is_deterministic": response.is_deterministic,
            "analysis_id": analysis_id,
        }

        # Upsert: delete existing row for this repository then insert fresh
        supabase.table("contributions").delete().eq(
            "repository_id", repository_id
        ).execute()

        supabase.table("contributions").insert(row).execute()

    except Exception as exc:
        logger.warning(
            "Could not persist contributions for %s: %s", repository_id, exc
        )


def _load_persisted_contributions(
    repository_id: str,
) -> Optional[dict]:
    """
    Load a previously persisted contribution record from the database.

    Returns the raw row dict or None.
    """
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("contributions")
            .select("*")
            .eq("repository_id", repository_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning(
            "Could not load contributions for %s: %s", repository_id, exc
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_contributions(repository_id: str) -> ContributionResponse:
    """
    Main entry point: generate first-contribution recommendations for a repository.

    Fetches the stored analysis, runs deterministic candidate generators,
    persists the result, and returns a ContributionResponse.

    Does NOT raise — all errors are captured and reflected in the response
    so the API layer can respond appropriately without leaking stack traces.
    """
    # --- 1. Fetch repository ---
    try:
        supabase = get_supabase()
        repo_resp = (
            supabase.table("repositories")
            .select("id,name,description,github_url")
            .eq("id", repository_id)
            .limit(1)
            .execute()
        )
        repo_rows = repo_resp.data or []
    except Exception as exc:
        logger.error("Failed to fetch repository %s: %s", repository_id, exc)
        return ContributionResponse(
            repository_id=repository_id,
            status="error",
            error="Failed to retrieve repository record.",
        )

    if not repo_rows:
        return ContributionResponse(
            repository_id=repository_id,
            status="error",
            error="Repository not found.",
        )

    # --- 2. Fetch analysis ---
    try:
        analysis_resp = (
            supabase.table("analyses")
            .select("*")
            .eq("repository_id", repository_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        analysis_rows = analysis_resp.data or []
    except Exception as exc:
        logger.error("Failed to fetch analysis for %s: %s", repository_id, exc)
        return ContributionResponse(
            repository_id=repository_id,
            status="error",
            error="Failed to retrieve analysis record.",
        )

    if not analysis_rows:
        return ContributionResponse(
            repository_id=repository_id,
            status="no_analysis",
            error=(
                "No analysis found for this repository. "
                "Run repository analysis before generating contribution recommendations."
            ),
        )

    analysis = analysis_rows[0]
    analysis_id = analysis.get("id")

    # --- 3. Assess evidence quality ---
    quality = _assess_evidence_quality(analysis)

    if quality == "insufficient":
        return ContributionResponse(
            repository_id=repository_id,
            status="insufficient_evidence",
            error=(
                "RepoGuide does not have enough indexed information to safely recommend "
                "a contribution. The repository may be empty or have too few files."
            ),
            evidence_quality=quality,
            analysis_id=analysis_id,
        )

    # --- 4. Run candidate generators ---
    generators = [
        _generate_documentation_candidate,
        _generate_testing_candidate,
        _generate_devex_candidate,
        _generate_maintenance_candidate,
        _generate_feature_candidate,
    ]

    candidates: list[ContributionCandidate] = []
    for gen in generators:
        try:
            candidate = gen(analysis)
            if candidate is not None:
                candidates.append(candidate)
        except Exception as exc:
            logger.warning("Candidate generator %s failed: %s", gen.__name__, exc)

    if not candidates:
        return ContributionResponse(
            repository_id=repository_id,
            status="insufficient_evidence",
            error=(
                "RepoGuide could not identify any grounded contribution opportunities "
                "from the available repository metadata."
            ),
            evidence_quality=quality,
            analysis_id=analysis_id,
        )

    # --- 5. Select recommended candidates ---
    recommended_ids = _select_recommended(candidates, analysis)

    response = ContributionResponse(
        repository_id=repository_id,
        candidates=candidates[:MAX_CANDIDATES],
        recommended_ids=recommended_ids,
        is_deterministic=True,
        analysis_id=analysis_id,
        generated_at=datetime.now(timezone.utc),
        evidence_quality=quality,
        status="ok",
    )

    # --- 6. Persist ---
    _persist_contributions(repository_id, response, analysis_id)

    return response


def get_contributions(repository_id: str) -> ContributionResponse:
    """
    Retrieve contributions for a repository: load persisted result or generate fresh.

    Tries the database first, then falls back to live generation.
    """
    persisted = _load_persisted_contributions(repository_id)

    if persisted:
        # Reconstruct from persisted JSON
        try:
            raw_candidates = persisted.get("candidates") or []
            candidates = [ContributionCandidate(**c) for c in raw_candidates]
            return ContributionResponse(
                repository_id=repository_id,
                candidates=candidates,
                recommended_ids=persisted.get("recommended_ids") or [],
                is_deterministic=persisted.get("is_deterministic", True),
                analysis_id=persisted.get("analysis_id"),
                status="ok",
            )
        except Exception as exc:
            logger.warning(
                "Could not reconstruct persisted contributions for %s, regenerating: %s",
                repository_id,
                exc,
            )

    # Fall back to live generation
    return generate_contributions(repository_id)
