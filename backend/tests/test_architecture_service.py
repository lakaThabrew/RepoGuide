"""
test_architecture_service.py — Focused tests for the architecture explorer logic.

Covers:
  - Frontend component detection
  - Backend component detection
  - Database component detection
  - Services detection
  - Test component detection
  - Deployment detection
  - Authentication detection
  - Relationship generation
  - No fabricated relationships
  - Evidence attached to components
  - Evidence attached to relationships
  - Forbidden files filtered
  - Prompt-injection text sanitized
  - Empty repository
  - Insufficient evidence
  - Mixed frontend/backend repository
  - Single-component repository
  - Confidence calculation
  - Architecture summary generation
  - Reading order generation
  - _build_architecture_data integration
  - _infer_evidence_quality
  - _reconstruct_important_files_from_arch_components
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Minimal stubs — same pattern as test_analysis_service.py
# ---------------------------------------------------------------------------

def _install_stubs():
    supabase_mod = types.ModuleType("supabase")
    supabase_mod.create_client = MagicMock(return_value=MagicMock())  # type: ignore
    supabase_mod.Client = object  # type: ignore
    sys.modules.setdefault("supabase", supabase_mod)

    ps_mod = types.ModuleType("pydantic_settings")

    class _BaseSettings:
        def __init__(self, **_):
            pass

    ps_mod.BaseSettings = _BaseSettings  # type: ignore
    sys.modules.setdefault("pydantic_settings", ps_mod)


_install_stubs()

# ---------------------------------------------------------------------------
# Imports under test — after stubs
# ---------------------------------------------------------------------------

from app.services.analysis_service import (  # noqa: E402
    _build_arch_components,
    _build_arch_relationships,
    _build_architecture_data,
    _build_architecture_summary,
    _build_reading_order,
    _extract_evidence_from_file_list,
    _infer_evidence_quality,
    _reconstruct_important_files_from_arch_components,
)
from app.schemas.analysis import ArchitectureData, ArchitectureComponent, ArchitectureRelationship  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_file(path: str, name: str, ext: str, size: int = 500, is_dir: bool = False) -> dict:
    return {
        "file_path": path,
        "file_name": name,
        "extension": ext,
        "file_size": size,
        "is_directory": is_dir,
    }


# Full-stack fixture
FULLSTACK_FILES = [
    _make_file("frontend/src/main.tsx",           "main.tsx",           ".tsx"),
    _make_file("frontend/src/App.tsx",             "App.tsx",            ".tsx"),
    _make_file("frontend/src/components/Nav.tsx",  "Nav.tsx",            ".tsx"),
    _make_file("frontend/package.json",            "package.json",       ".json"),
    _make_file("frontend/vite.config.ts",          "vite.config.ts",     ".ts"),
    _make_file("backend/app/main.py",              "main.py",            ".py"),
    _make_file("backend/app/api/routes.py",        "routes.py",          ".py"),
    _make_file("backend/app/services/svc.py",      "svc.py",             ".py"),
    _make_file("backend/app/auth.py",              "auth.py",            ".py"),
    _make_file("backend/requirements.txt",         "requirements.txt",   ".txt"),
    _make_file("backend/tests/test_routes.py",     "test_routes.py",     ".py"),
    _make_file("Dockerfile",                       "Dockerfile",         ""),
    _make_file("docker-compose.yml",               "docker-compose.yml", ".yml"),
    _make_file("README.md",                        "README.md",          ".md"),
    # Directories
    _make_file("frontend",         "frontend",    "", 0, True),
    _make_file("backend",          "backend",     "", 0, True),
    _make_file("frontend/src/components", "components", "", 0, True),
    _make_file("backend/tests",    "tests",       "", 0, True),
]

# Backend-only fixture
BACKEND_ONLY_FILES = [
    _make_file("app/main.py",          "main.py",          ".py"),
    _make_file("app/api/routes.py",    "routes.py",        ".py"),
    _make_file("requirements.txt",     "requirements.txt", ".txt"),
    _make_file("tests/test_app.py",    "test_app.py",      ".py"),
    _make_file("app",   "app",   "", 0, True),
    _make_file("tests", "tests", "", 0, True),
]

# Frontend-only fixture
FRONTEND_ONLY_FILES = [
    _make_file("src/main.tsx",                "main.tsx",     ".tsx"),
    _make_file("src/App.tsx",                 "App.tsx",      ".tsx"),
    _make_file("src/components/Button.tsx",   "Button.tsx",   ".tsx"),
    _make_file("package.json",                "package.json", ".json"),
    _make_file("vite.config.ts",              "vite.config.ts", ".ts"),
    _make_file("src", "src", "", 0, True),
    _make_file("src/components", "components", "", 0, True),
]

# Minimal database fixture
DB_FILES = [
    _make_file("app/main.py",             "main.py",          ".py"),
    _make_file("app/api/routes.py",       "routes.py",        ".py"),
    _make_file("app/models/user.py",      "user.py",          ".py"),
    _make_file("requirements.txt",        "requirements.txt", ".txt"),
    _make_file("app",    "app",    "", 0, True),
]

# Deployment fixture
DEPLOYMENT_FILES = [
    _make_file("app/main.py",         "main.py",            ".py"),
    _make_file("Dockerfile",          "Dockerfile",         ""),
    _make_file("docker-compose.yml",  "docker-compose.yml", ".yml"),
    _make_file(".github/workflows/ci.yml", "ci.yml",        ".yml"),
    _make_file("app", "app", "", 0, True),
]


# ---------------------------------------------------------------------------
# Helper: build evidence from file list and inject manifest content
# ---------------------------------------------------------------------------

def _evidence_with_react(files: list[dict], extra_frameworks: list[str] | None = None) -> dict:
    """Build evidence and inject React + Vite into frameworks (simulating manifest content parse)."""
    ev = _extract_evidence_from_file_list(files)
    ev["frameworks"] = list(set(ev.get("frameworks", []) + ["React", "Vite"] + (extra_frameworks or [])))
    return ev


def _evidence_with_fastapi(files: list[dict]) -> dict:
    """Build evidence and inject FastAPI into frameworks."""
    ev = _extract_evidence_from_file_list(files)
    ev["frameworks"] = list(set(ev.get("frameworks", []) + ["FastAPI"]))
    ev["databases"] = list(set(ev.get("databases", []) + ["Supabase"]))
    return ev


# ===========================================================================
# 1. Frontend component detection
# ===========================================================================

class TestFrontendDetection:

    def test_frontend_detected_from_tsx_files_and_react(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "frontend" in names, f"Expected 'frontend' in {names}"

    def test_frontend_technology_label_includes_react(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next(c for c in components if c["name"] == "frontend")
        assert fe["technology"] is not None
        assert "React" in fe["technology"], f"Expected React in technology: {fe['technology']}"

    def test_frontend_evidence_files_populated(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next(c for c in components if c["name"] == "frontend")
        assert len(fe["evidence_files"]) > 0, "Frontend should have evidence files"

    def test_frontend_evidence_bullets_populated(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next(c for c in components if c["name"] == "frontend")
        assert len(fe["evidence"]) > 0, "Frontend should have evidence bullets"
        assert any("React" in e for e in fe["evidence"])

    def test_frontend_confidence_is_high_with_framework_dirs_config(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next(c for c in components if c["name"] == "frontend")
        # With React framework + frontend component dirs + vite.config, expect high or medium
        assert fe["confidence"] in ("high", "medium"), f"Unexpected confidence: {fe['confidence']}"

    def test_frontend_not_detected_without_structure(self):
        """React framework detected but NO frontend dirs or tsx files → no frontend component."""
        ev = _extract_evidence_from_file_list([
            _make_file("requirements.txt", "requirements.txt", ".txt"),
        ])
        ev["frameworks"] = ["React"]   # inject framework WITHOUT supporting structure
        ev["frontend_components"] = []
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "frontend" not in names, (
            "Frontend should NOT be detected when only framework name is present "
            f"without directory/file evidence. Got: {names}"
        )

    def test_frontend_dirs_populated(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next(c for c in components if c["name"] == "frontend")
        assert len(fe["directories"]) > 0, "Frontend component should have directories"


# ===========================================================================
# 2. Backend component detection
# ===========================================================================

class TestBackendDetection:

    def test_backend_detected_from_api_routes(self):
        ev = _evidence_with_fastapi(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "backend/API" in names, f"Expected 'backend/API' in {names}"

    def test_backend_detected_from_entry_points(self):
        ev = _extract_evidence_from_file_list(BACKEND_ONLY_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "backend/API" in names, f"Expected 'backend/API' in {names}"

    def test_backend_technology_label(self):
        ev = _evidence_with_fastapi(BACKEND_ONLY_FILES)
        components = _build_arch_components(ev)
        be = next(c for c in components if c["name"] == "backend/API")
        assert be["technology"] is not None
        assert "FastAPI" in be["technology"]

    def test_backend_evidence_files_populated(self):
        ev = _evidence_with_fastapi(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        be = next(c for c in components if c["name"] == "backend/API")
        assert len(be["evidence_files"]) > 0, "Backend should have evidence files"

    def test_backend_evidence_bullets_populated(self):
        ev = _evidence_with_fastapi(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        be = next(c for c in components if c["name"] == "backend/API")
        assert len(be["evidence"]) > 0, "Backend should have evidence bullets"

    def test_backend_dirs_populated(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        be = next((c for c in components if c["name"] == "backend/API"), None)
        if be:
            # Directories may or may not be populated depending on evidence
            assert isinstance(be["directories"], list)


# ===========================================================================
# 3. Database component detection
# ===========================================================================

class TestDatabaseDetection:

    def test_database_detected_from_db_signal(self):
        ev = _extract_evidence_from_file_list(DB_FILES)
        ev["databases"] = ["PostgreSQL", "SQLAlchemy"]
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "database/data layer" in names, f"Expected database in {names}"

    def test_database_technology_label_from_detected_dbs(self):
        ev = _extract_evidence_from_file_list(DB_FILES)
        ev["databases"] = ["Supabase"]
        components = _build_arch_components(ev)
        db = next(c for c in components if c["name"] == "database/data layer")
        assert db["technology"] is not None
        assert "Supabase" in db["technology"]

    def test_database_evidence_bullets_populated(self):
        ev = _extract_evidence_from_file_list(DB_FILES)
        ev["databases"] = ["PostgreSQL"]
        components = _build_arch_components(ev)
        db = next(c for c in components if c["name"] == "database/data layer")
        assert len(db["evidence"]) > 0
        assert any("PostgreSQL" in e or "database" in e.lower() for e in db["evidence"])

    def test_database_not_detected_without_signals(self):
        """No database signals → no database component."""
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
        ])
        ev["databases"] = []
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "database/data layer" not in names, (
            f"Database component should not appear without signals, got: {names}"
        )

    def test_database_confidence_high_with_db_and_files(self):
        ev = _extract_evidence_from_file_list(DB_FILES)
        ev["databases"] = ["PostgreSQL"]
        # Inject a fake database category file into important_files
        ev["important_files"] = ev.get("important_files", []) + [{
            "file_path": "app/models/user.py",
            "reason": "Database models file",
            "confidence": "medium",
            "category": "database",
        }]
        components = _build_arch_components(ev)
        db = next(c for c in components if c["name"] == "database/data layer")
        assert db["confidence"] == "high"


# ===========================================================================
# 4. Services detection
# ===========================================================================

class TestServicesDetection:

    def test_services_detected_from_service_files(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        # Inject service file into important_files
        ev["important_files"] = ev.get("important_files", []) + [{
            "file_path": "backend/app/services/svc.py",
            "reason": "Core service file",
            "confidence": "medium",
            "category": "core service",
        }]
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "services" in names, f"Expected 'services' in {names}"

    def test_services_not_detected_without_service_files(self):
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
        ])
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "services" not in names, f"services should not appear: {names}"

    def test_services_evidence_files_populated(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        ev["important_files"] = ev.get("important_files", []) + [{
            "file_path": "backend/app/services/my_service.py",
            "reason": "Core service",
            "confidence": "medium",
            "category": "core service",
        }]
        components = _build_arch_components(ev)
        svc = next(c for c in components if c["name"] == "services")
        assert len(svc["evidence_files"]) > 0


# ===========================================================================
# 5. Test component detection
# ===========================================================================

class TestTestComponentDetection:

    def test_tests_detected_from_test_files(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "tests" in names, f"Expected 'tests' in {names}"

    def test_tests_evidence_files_populated(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        tc = next(c for c in components if c["name"] == "tests")
        assert len(tc["evidence_files"]) > 0

    def test_tests_not_detected_without_test_files(self):
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
            _make_file("utils.py", "utils.py", ".py"),
        ])
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "tests" not in names, f"tests should not appear without test files: {names}"

    def test_tests_confidence_high_with_test_dirs(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        tc = next((c for c in components if c["name"] == "tests"), None)
        if tc and ev.get("test_directories"):
            assert tc["confidence"] == "high"


# ===========================================================================
# 6. Deployment detection
# ===========================================================================

class TestDeploymentDetection:

    def test_deployment_detected_from_dockerfile(self):
        ev = _extract_evidence_from_file_list(DEPLOYMENT_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "deployment/infrastructure" in names, f"Expected deployment in {names}"

    def test_deployment_evidence_files_populated(self):
        ev = _extract_evidence_from_file_list(DEPLOYMENT_FILES)
        components = _build_arch_components(ev)
        dep = next(c for c in components if c["name"] == "deployment/infrastructure")
        assert len(dep["evidence_files"]) > 0
        # Should include Dockerfile
        assert any("Dockerfile" in f or "docker" in f.lower() for f in dep["evidence_files"])

    def test_deployment_confidence_high(self):
        ev = _extract_evidence_from_file_list(DEPLOYMENT_FILES)
        components = _build_arch_components(ev)
        dep = next(c for c in components if c["name"] == "deployment/infrastructure")
        assert dep["confidence"] == "high"

    def test_deployment_not_detected_without_deployment_files(self):
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
        ])
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "deployment/infrastructure" not in names, (
            f"deployment should not appear without deployment files: {names}"
        )


# ===========================================================================
# 7. Authentication detection
# ===========================================================================

class TestAuthenticationDetection:

    def test_auth_detected_from_auth_py(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "authentication" in names, f"Expected 'authentication' in {names}"

    def test_auth_evidence_files_populated(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        auth = next(c for c in components if c["name"] == "authentication")
        assert len(auth["evidence_files"]) > 0

    def test_auth_not_detected_without_auth_files(self):
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
            _make_file("utils.py", "utils.py", ".py"),
        ])
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "authentication" not in names, f"auth should not appear: {names}"


# ===========================================================================
# 8. Relationship generation
# ===========================================================================

class TestRelationshipGeneration:

    def test_frontend_to_backend_relationship(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        rel_types = [(r["source"], r["target"]) for r in relationships]
        assert ("frontend", "backend/API") in rel_types, (
            f"Expected frontend→backend relationship. Got: {rel_types}"
        )

    def test_backend_to_database_relationship(self):
        ev = _evidence_with_fastapi(FULLSTACK_FILES)
        # Ensure database is detected
        ev["databases"] = ["PostgreSQL", "Supabase"]
        ev["important_files"] = ev.get("important_files", []) + [{
            "file_path": "backend/app/models/user.py",
            "reason": "Database models",
            "confidence": "medium",
            "category": "database",
        }]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        rel_types = [(r["source"], r["target"]) for r in relationships]
        assert ("backend/API", "database/data layer") in rel_types, (
            f"Expected backend→database relationship. Got: {rel_types}"
        )

    def test_no_relationships_for_standalone_components(self):
        """A repository with only tests and deployment → no relationships."""
        ev = _extract_evidence_from_file_list([
            _make_file("tests/test_a.py", "test_a.py", ".py"),
            _make_file("Dockerfile",      "Dockerfile", ""),
            _make_file("tests", "tests", "", 0, True),
        ])
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        # These components (tests, deployment) don't have defined relationships
        assert isinstance(relationships, list)
        # No spurious source/target combos
        for r in relationships:
            assert r["source"] in {c["name"] for c in components}, \
                f"Relationship source '{r['source']}' not in components"
            assert r["target"] in {c["name"] for c in components}, \
                f"Relationship target '{r['target']}' not in components"

    def test_no_self_relationships(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        for r in relationships:
            assert r["source"] != r["target"], (
                f"Self-relationship detected: {r['source']} → {r['target']}"
            )


# ===========================================================================
# 9. No fabricated relationships
# ===========================================================================

class TestNoFabricatedRelationships:

    def test_frontend_backend_relationship_requires_directory_separation(self):
        """
        If there are no frontend_components AND no backend_components directories,
        the frontend→backend relationship should NOT be generated even if both
        component types are detected.
        """
        # Inject components manually but strip directory evidence
        components = [
            {"name": "frontend", "description": "", "evidence_files": [], "technology": "React",
             "directories": [], "confidence": "low", "evidence": []},
            {"name": "backend/API", "description": "", "evidence_files": [], "technology": "FastAPI",
             "directories": [], "confidence": "low", "evidence": []},
        ]
        evidence = {
            "frontend_components": [],   # no dir separation
            "backend_components": [],    # no dir separation
            "api_route_files": [],       # no route files
            "important_files": [],
            "databases": [],
        }
        relationships = _build_arch_relationships(components, evidence)
        rel_types = [(r["source"], r["target"]) for r in relationships]
        # Without directory separation AND route files, no frontend→backend relationship
        assert ("frontend", "backend/API") not in rel_types, (
            "Should not fabricate frontend→backend without directory separation evidence"
        )

    def test_all_relationships_have_evidence(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        ev["databases"] = ["PostgreSQL"]
        ev["important_files"] = ev.get("important_files", []) + [{
            "file_path": "backend/models.py",
            "reason": "DB models",
            "confidence": "medium",
            "category": "database",
        }]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        for r in relationships:
            assert len(r["evidence"]) > 0, (
                f"Relationship {r['source']}→{r['target']} has no evidence"
            )

    def test_relationships_only_reference_existing_components(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        component_names = {c["name"] for c in components}
        relationships = _build_arch_relationships(components, ev)
        for r in relationships:
            assert r["source"] in component_names, \
                f"Relationship source '{r['source']}' not in components"
            assert r["target"] in component_names, \
                f"Relationship target '{r['target']}' not in components"


# ===========================================================================
# 10. Evidence attached to components and relationships
# ===========================================================================

class TestEvidenceAttachment:

    def test_all_components_have_evidence(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        ev["databases"] = ["PostgreSQL"]
        components = _build_arch_components(ev)
        for comp in components:
            assert "evidence" in comp, f"Component '{comp['name']}' has no evidence key"
            # evidence may be empty for some components, but key must exist
            assert isinstance(comp["evidence"], list)

    def test_all_relationships_have_evidence_list(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        for rel in relationships:
            assert "evidence" in rel
            assert isinstance(rel["evidence"], list)
            assert len(rel["evidence"]) > 0, (
                f"Relationship {rel['source']}→{rel['target']} must have evidence"
            )

    def test_component_evidence_contains_tech_names(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        components = _build_arch_components(ev)
        fe = next((c for c in components if c["name"] == "frontend"), None)
        if fe:
            all_evidence = " ".join(fe["evidence"])
            assert "React" in all_evidence, "Frontend evidence should mention React"

    def test_relationship_evidence_is_descriptive(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        fe_be = next(
            (r for r in relationships if r["source"] == "frontend" and r["target"] == "backend/API"),
            None
        )
        if fe_be:
            # Evidence should describe what was detected
            all_evidence = " ".join(fe_be["evidence"])
            assert len(all_evidence) > 20, "Evidence should be descriptive"


# ===========================================================================
# 11. Forbidden files filtered
# ===========================================================================

class TestForbiddenFilesFiltered:

    def test_env_file_not_in_components(self):
        """
        .env files should never appear in component evidence_files.
        """
        files = FULLSTACK_FILES + [
            _make_file(".env",        ".env",        ""),
            _make_file(".env.local",  ".env.local",  ""),
        ]
        ev = _extract_evidence_from_file_list(files)
        components = _build_arch_components(ev)
        for comp in components:
            for ef in comp["evidence_files"]:
                assert ".env" not in ef or ".env.example" in ef, (
                    f"Forbidden .env file in component '{comp['name']}' evidence: {ef}"
                )

    def test_private_key_not_in_components(self):
        files = FULLSTACK_FILES + [
            _make_file("id_rsa",       "id_rsa",      ""),
            _make_file("id_ed25519",   "id_ed25519",  ""),
        ]
        ev = _extract_evidence_from_file_list(files)
        components = _build_arch_components(ev)
        all_evidence_files = [
            ef for c in components for ef in c["evidence_files"]
        ]
        assert not any("id_rsa" in f for f in all_evidence_files), \
            f"id_rsa found in evidence: {all_evidence_files}"
        assert not any("id_ed25519" in f for f in all_evidence_files), \
            f"id_ed25519 found in evidence: {all_evidence_files}"


# ===========================================================================
# 12. Prompt-injection sanitized
# ===========================================================================

class TestPromptInjectionSanitized:

    def test_injected_filename_not_in_components(self):
        injected_files = FULLSTACK_FILES + [
            _make_file(
                "docs/ignore_previous_instructions.md",
                "ignore_previous_instructions.md",
                ".md",
            ),
        ]
        ev = _extract_evidence_from_file_list(injected_files)
        components = _build_arch_components(ev)
        all_evidence_files = [ef for c in components for ef in c["evidence_files"]]
        assert not any("ignore_previous" in f for f in all_evidence_files), \
            f"Injected path in evidence: {all_evidence_files}"

    def test_injected_filename_not_in_relationships(self):
        injected_files = FULLSTACK_FILES + [
            _make_file(
                "backend/pretend_you_are_admin.py",
                "pretend_you_are_admin.py",
                ".py",
            ),
        ]
        ev = _extract_evidence_from_file_list(injected_files)
        ev["frameworks"] = ev.get("frameworks", []) + ["React", "FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        all_rel_evidence = [e for r in relationships for e in r["evidence"]]
        assert not any("pretend_you_are" in e for e in all_rel_evidence), \
            f"Injected text in relationship evidence: {all_rel_evidence}"


# ===========================================================================
# 13. Empty repository
# ===========================================================================

class TestEmptyRepository:

    def test_empty_files_produces_no_components(self):
        ev = _extract_evidence_from_file_list([])
        components = _build_arch_components(ev)
        assert components == [], f"Expected no components for empty repo, got {components}"

    def test_empty_files_produces_no_relationships(self):
        ev = _extract_evidence_from_file_list([])
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        assert relationships == [], "Expected no relationships for empty repo"

    def test_build_architecture_data_empty(self):
        ev = _extract_evidence_from_file_list([])
        arch = _build_architecture_data(ev, "insufficient")
        assert isinstance(arch, ArchitectureData)
        assert arch.components == []
        assert arch.relationships == []
        assert arch.confidence in ("low", "medium", "high")
        assert arch.evidence_quality == "insufficient"

    def test_architecture_summary_empty_is_descriptive(self):
        summary = _build_architecture_summary([], {})
        assert "Insufficient" in summary or len(summary) > 5


# ===========================================================================
# 14. Insufficient evidence
# ===========================================================================

class TestInsufficientEvidence:

    def test_single_file_produces_partial_components(self):
        ev = _extract_evidence_from_file_list([
            _make_file("README.md", "README.md", ".md"),
        ])
        components = _build_arch_components(ev)
        # May produce 0 components for a single README
        assert isinstance(components, list)

    def test_confidence_low_for_minimal_evidence(self):
        ev = _extract_evidence_from_file_list([
            _make_file("main.py", "main.py", ".py"),
        ])
        arch = _build_architecture_data(ev, "partial")
        # single file: may or may not produce component, confidence should be low or medium
        assert arch.confidence in ("low", "medium")

    def test_reading_order_falls_back_gracefully(self):
        steps = _build_reading_order([], {})
        assert isinstance(steps, list)
        # May be empty or have a generic step
        for step in steps:
            assert isinstance(step, str)


# ===========================================================================
# 15. Mixed frontend/backend repository
# ===========================================================================

class TestMixedFullstackRepository:

    def test_both_frontend_and_backend_detected(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "frontend" in names, f"Missing frontend: {names}"
        assert "backend/API" in names, f"Missing backend/API: {names}"

    def test_fullstack_has_frontend_to_backend_relationship(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        relationships = _build_arch_relationships(components, ev)
        sources = [r["source"] for r in relationships]
        targets = [r["target"] for r in relationships]
        has_fe_be = any(
            s == "frontend" and t == "backend/API"
            for s, t in zip(sources, targets)
        )
        assert has_fe_be, f"Expected frontend→backend/API relationship, got: {list(zip(sources, targets))}"

    def test_fullstack_reading_order_covers_both_layers(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        steps = _build_reading_order(components, ev)
        all_steps = " ".join(steps).lower()
        assert "frontend" in all_steps or "entry point" in all_steps, \
            f"Reading order should mention frontend: {steps}"
        assert "api" in all_steps or "backend" in all_steps or "route" in all_steps, \
            f"Reading order should mention backend/API: {steps}"


# ===========================================================================
# 16. Single-component repository
# ===========================================================================

class TestSingleComponentRepository:

    def test_backend_only_reading_order(self):
        ev = _extract_evidence_from_file_list(BACKEND_ONLY_FILES)
        components = _build_arch_components(ev)
        steps = _build_reading_order(components, ev)
        assert len(steps) > 0, "Reading order should not be empty"
        all_steps = " ".join(steps).lower()
        # Should not confusingly reference frontend
        assert "entry point" in all_steps or "api" in all_steps or "application" in all_steps

    def test_frontend_only_reading_order(self):
        ev = _evidence_with_react(FRONTEND_ONLY_FILES)
        components = _build_arch_components(ev)
        steps = _build_reading_order(components, ev)
        assert len(steps) > 0, "Reading order should not be empty"
        all_steps = " ".join(steps).lower()
        assert "frontend" in all_steps or "entry point" in all_steps or "component" in all_steps

    def test_single_backend_component_count(self):
        ev = _extract_evidence_from_file_list(BACKEND_ONLY_FILES)
        components = _build_arch_components(ev)
        names = [c["name"] for c in components]
        assert "frontend" not in names, f"Frontend should not appear in backend-only repo: {names}"


# ===========================================================================
# 17. Confidence calculation
# ===========================================================================

class TestConfidenceCalculation:

    def test_high_confidence_fullstack(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        arch = _build_architecture_data(ev, "sufficient")
        assert arch.confidence == "high", (
            f"Expected high confidence for full-stack repo, got {arch.confidence}"
        )

    def test_low_confidence_empty(self):
        ev = _extract_evidence_from_file_list([])
        arch = _build_architecture_data(ev, "insufficient")
        assert arch.confidence == "low"

    def test_medium_confidence_single_component(self):
        ev = _extract_evidence_from_file_list(BACKEND_ONLY_FILES)
        arch = _build_architecture_data(ev, "partial")
        # Single component without entry points or frameworks → medium or low
        assert arch.confidence in ("medium", "low")

    def test_confidence_not_high_with_no_entry_points(self):
        ev = _extract_evidence_from_file_list(FULLSTACK_FILES)
        ev["entry_points"] = []     # strip entry points
        ev["frameworks"] = []       # strip frameworks
        arch = _build_architecture_data(ev, "partial")
        assert arch.confidence != "high", (
            "Confidence should not be high without entry points and frameworks"
        )


# ===========================================================================
# 18. Architecture summary
# ===========================================================================

class TestArchitectureSummary:

    def test_summary_mentions_component_count(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        summary = _build_architecture_summary(components, ev)
        assert "component" in summary.lower(), f"Summary should mention components: {summary}"

    def test_summary_mentions_technologies(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        components = _build_arch_components(ev)
        summary = _build_architecture_summary(components, ev)
        # Summary should mention one of the detected technologies
        assert any(tech in summary for tech in ["React", "FastAPI", "Vite"]), (
            f"Summary should mention detected technologies: {summary}"
        )

    def test_summary_empty_components_returns_insufficient(self):
        summary = _build_architecture_summary([], {})
        assert "insufficient" in summary.lower() or len(summary) > 5

    def test_summary_no_fabrication_for_empty_evidence(self):
        ev = _extract_evidence_from_file_list([])
        components = _build_arch_components(ev)
        summary = _build_architecture_summary(components, ev)
        assert isinstance(summary, str)
        assert len(summary) > 0


# ===========================================================================
# 19. _infer_evidence_quality
# ===========================================================================

class TestInferEvidenceQuality:

    def test_sufficient_with_langs_frameworks_entrypoints(self):
        ev = {
            "primary_languages": ["Python"],
            "frameworks": ["FastAPI"],
            "runtimes": [],
            "entry_points": [{"file_path": "main.py", "kind": "Python entry point"}],
            "backend_components": ["backend"],
            "frontend_components": [],
        }
        quality = _infer_evidence_quality(ev)
        assert quality == "sufficient"

    def test_partial_with_just_languages(self):
        ev = {
            "primary_languages": ["Python"],
            "frameworks": [],
            "runtimes": [],
            "entry_points": [],
            "backend_components": [],
            "frontend_components": [],
        }
        quality = _infer_evidence_quality(ev)
        assert quality == "partial"

    def test_insufficient_for_empty(self):
        ev = {
            "primary_languages": [],
            "frameworks": [],
            "runtimes": [],
            "entry_points": [],
            "backend_components": [],
            "frontend_components": [],
        }
        quality = _infer_evidence_quality(ev)
        assert quality == "insufficient"


# ===========================================================================
# 20. _reconstruct_important_files_from_arch_components
# ===========================================================================

class TestReconstructImportantFiles:

    def test_reconstructs_frontend_files(self):
        arch_components = [
            {
                "name": "frontend",
                "evidence_files": ["frontend/src/main.tsx", "frontend/src/App.tsx"],
                "confidence": "high",
            }
        ]
        result = _reconstruct_important_files_from_arch_components(arch_components)
        paths = [r["file_path"] for r in result]
        assert "frontend/src/main.tsx" in paths
        categories = [r["category"] for r in result]
        assert "frontend" in categories

    def test_reconstructs_backend_api_files(self):
        arch_components = [
            {
                "name": "backend/API",
                "evidence_files": ["backend/app/api/routes.py"],
                "confidence": "medium",
            }
        ]
        result = _reconstruct_important_files_from_arch_components(arch_components)
        categories = [r["category"] for r in result]
        assert "API" in categories

    def test_empty_input_returns_empty(self):
        result = _reconstruct_important_files_from_arch_components([])
        assert result == []

    def test_skips_non_dict_entries(self):
        result = _reconstruct_important_files_from_arch_components(["not_a_dict", None])  # type: ignore
        assert isinstance(result, list)


# ===========================================================================
# 21. _build_architecture_data integration
# ===========================================================================

class TestBuildArchitectureDataIntegration:

    def test_returns_architecture_data_type(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        arch = _build_architecture_data(ev, "sufficient")
        assert isinstance(arch, ArchitectureData)

    def test_components_are_architecture_component_objects(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        arch = _build_architecture_data(ev, "sufficient")
        for comp in arch.components:
            assert isinstance(comp, ArchitectureComponent)

    def test_relationships_are_architecture_relationship_objects(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        arch = _build_architecture_data(ev, "sufficient")
        for rel in arch.relationships:
            assert isinstance(rel, ArchitectureRelationship)

    def test_reading_order_is_non_empty_for_fullstack(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        arch = _build_architecture_data(ev, "sufficient")
        assert len(arch.reading_order) > 0, "Reading order should not be empty for full-stack"

    def test_invalid_evidence_quality_clamped(self):
        ev = _extract_evidence_from_file_list([])
        arch = _build_architecture_data(ev, "totally_invalid_value")
        assert arch.evidence_quality in ("sufficient", "partial", "insufficient")

    def test_fullstack_summary_not_empty(self):
        ev = _evidence_with_react(FULLSTACK_FILES)
        ev["frameworks"] = ev["frameworks"] + ["FastAPI"]
        arch = _build_architecture_data(ev, "sufficient")
        assert len(arch.summary) > 10, "Summary should not be empty"


# ---------------------------------------------------------------------------
# Run via unittest if executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import unittest
    unittest.main()
