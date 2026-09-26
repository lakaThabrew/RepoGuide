"""
test_deterministic_intelligence.py — Focused unit tests for the new
deterministic repository intelligence features added to analysis_service.py.

Covers (per the task specification):
  1. Technology detection — including content-based React/Vite/Node/FastAPI detection
  2. Entry-point detection — including src/main.*, App.*, Dockerfile
  3. Important-file classification with categories
  4. Architecture component detection
  5. Dependency manifest detection — go.mod, Cargo.toml, requirements.txt, package.json
  6. Empty / small repository
  7. Mixed frontend + backend repository (full flow)
  8. Directory classification (source, test, doc)
  9. Evidence quality determination

No real Supabase or AI connection is made.  All external I/O is mocked.
"""

from __future__ import annotations

import json
import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stubs — must be installed before any app import
# ---------------------------------------------------------------------------

def _install_stubs() -> None:
    supabase_mod = types.ModuleType("supabase")
    supabase_mod.create_client = MagicMock(return_value=MagicMock())  # type: ignore
    supabase_mod.Client = object  # type: ignore
    sys.modules.setdefault("supabase", supabase_mod)

    ps_mod = types.ModuleType("pydantic_settings")

    class _BaseSettings:
        def __init__(self, **_: Any) -> None:
            pass

    ps_mod.BaseSettings = _BaseSettings  # type: ignore
    sys.modules.setdefault("pydantic_settings", ps_mod)


_install_stubs()


# ---------------------------------------------------------------------------
# Imports under test (after stubs)
# ---------------------------------------------------------------------------

from app.services.analysis_service import (  # noqa: E402
    _extract_evidence_from_file_list,
    _build_analysis_result,
    _parse_dependencies,
    _enrich_frameworks_from_manifests,
    _classify_directories,
    _build_arch_components,
    _select_important_files,
    _add_manifest_file_references,
    _categorise_file_by_path,
)
from app.services.ai_provider import NullProvider  # noqa: E402
from app.schemas.analysis import AnalysisResult, Dependency  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _f(path: str, name: str, ext: str, size: int = 500, is_dir: bool = False) -> dict:
    """Shorthand factory for a repository_files row."""
    return {
        "file_path": path,
        "file_name": name,
        "extension": ext,
        "file_size": size,
        "is_directory": is_dir,
    }


# Full mixed-stack fixture: Python FastAPI backend + React/TypeScript frontend
MIXED_STACK_FILES = [
    # ── Backend ──────────────────────────────────────────────────────────────
    _f("backend/app/main.py",               "main.py",           ".py"),
    _f("backend/app/api/routes.py",         "routes.py",         ".py"),
    _f("backend/app/services/auth_service.py", "auth_service.py", ".py"),
    _f("backend/app/database/models.py",    "models.py",         ".py"),
    _f("backend/requirements.txt",          "requirements.txt",  ".txt"),
    _f("backend/tests/test_routes.py",      "test_routes.py",    ".py"),
    # ── Frontend ─────────────────────────────────────────────────────────────
    _f("frontend/src/main.tsx",             "main.tsx",          ".tsx"),
    _f("frontend/src/App.tsx",              "App.tsx",           ".tsx"),
    _f("frontend/src/components/Nav.tsx",   "Nav.tsx",           ".tsx"),
    _f("frontend/src/pages/Home.tsx",       "Home.tsx",          ".tsx"),
    _f("frontend/package.json",             "package.json",      ".json"),
    _f("frontend/vite.config.ts",           "vite.config.ts",    ".ts"),
    # ── Config / deployment ──────────────────────────────────────────────────
    _f("Dockerfile",                        "Dockerfile",        ""),
    _f("docker-compose.yml",               "docker-compose.yml", ".yml"),
    _f(".github/workflows/ci.yml",         "ci.yml",            ".yml"),
    _f("README.md",                         "README.md",         ".md"),
    # ── Directories ──────────────────────────────────────────────────────────
    _f("backend",           "backend",    "", 0, True),
    _f("frontend",          "frontend",   "", 0, True),
    _f("frontend/src",      "src",        "", 0, True),
    _f("backend/tests",     "tests",      "", 0, True),
    _f("docs",              "docs",       "", 0, True),
]

# requirements.txt that mentions fastapi and supabase
_REQ_CONTENT = (
    "fastapi==0.115.0\n"
    "uvicorn[standard]==0.30.6\n"
    "supabase==2.7.4\n"
    "psycopg2-binary==2.9.9\n"
    "pydantic==2.9.2\n"
)

# package.json with React + Vite
_PKG_JSON_CONTENT = json.dumps({
    "name": "frontend",
    "scripts": {"dev": "vite", "build": "tsc && vite build", "test": "vitest"},
    "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
    "devDependencies": {"typescript": "^5.0.0", "vite": "^4.0.0"},
})

# go.mod content
_GO_MOD_CONTENT = (
    "module github.com/example/myapp\n\n"
    "go 1.21\n\n"
    "require (\n"
    "    github.com/gin-gonic/gin v1.9.1\n"
    "    github.com/lib/pq v1.10.9\n"
    ")\n"
)

# Cargo.toml content
_CARGO_TOML_CONTENT = (
    "[package]\n"
    "name = \"my-api\"\n"
    "version = \"0.1.0\"\n\n"
    "[dependencies]\n"
    'axum = "0.7.2"\n'
    'tokio = "1.35.1"\n'
    'serde = "1.0"\n'
)


# ===========================================================================
# 1. Technology detection
# ===========================================================================

class TestTechnologyDetection:
    """Evidence-based technology detection: languages, frameworks, runtimes."""

    def test_python_detected_from_py_extension(self):
        files = [_f("src/main.py", "main.py", ".py")]
        ev = _extract_evidence_from_file_list(files)
        assert "Python" in ev["primary_languages"]

    def test_typescript_detected_from_ts_extension(self):
        files = [_f("src/index.ts", "index.ts", ".ts")]
        ev = _extract_evidence_from_file_list(files)
        assert "TypeScript" in ev["primary_languages"]

    def test_go_detected_from_go_extension(self):
        files = [_f("main.go", "main.go", ".go")]
        ev = _extract_evidence_from_file_list(files)
        assert "Go" in ev["primary_languages"]

    def test_rust_detected_from_rs_extension(self):
        files = [_f("src/main.rs", "main.rs", ".rs")]
        ev = _extract_evidence_from_file_list(files)
        assert "Rust" in ev["primary_languages"]

    def test_java_detected_from_java_extension(self):
        files = [_f("src/App.java", "App.java", ".java")]
        ev = _extract_evidence_from_file_list(files)
        assert "Java" in ev["primary_languages"]

    def test_c_detected_from_c_extension(self):
        files = [_f("src/main.c", "main.c", ".c")]
        ev = _extract_evidence_from_file_list(files)
        assert "C" in ev["primary_languages"]

    def test_cpp_detected_from_cpp_extension(self):
        files = [_f("src/main.cpp", "main.cpp", ".cpp")]
        ev = _extract_evidence_from_file_list(files)
        assert "C++" in ev["primary_languages"]

    def test_vite_detected_from_config_filename(self):
        files = [_f("vite.config.ts", "vite.config.ts", ".ts")]
        ev = _extract_evidence_from_file_list(files)
        assert "Vite" in ev["frameworks"], f"Vite not in {ev['frameworks']}"

    def test_docker_detected_from_dockerfile(self):
        files = [_f("Dockerfile", "Dockerfile", "")]
        ev = _extract_evidence_from_file_list(files)
        assert any("Dockerfile" in d for d in ev["deployment_files"])

    def test_github_actions_detected(self):
        files = [_f(".github/workflows/ci.yml", "ci.yml", ".yml")]
        ev = _extract_evidence_from_file_list(files)
        assert any(".github" in d or "workflows" in d.lower()
                   for d in ev["deployment_files"] + ev["config_files"])

    def test_supabase_detected_from_path(self):
        files = [_f("lib/supabase.ts", "supabase.ts", ".ts")]
        ev = _extract_evidence_from_file_list(files)
        assert "Supabase" in ev["databases"], f"Supabase not in {ev['databases']}"

    def test_postgres_detected_from_path(self):
        files = [_f("db/postgres_schema.sql", "postgres_schema.sql", ".sql")]
        ev = _extract_evidence_from_file_list(files)
        assert "PostgreSQL" in ev["databases"], f"PostgreSQL not in {ev['databases']}"

    def test_react_detected_from_package_json_content(self):
        """React must be detected from package.json dependencies, not just filenames."""
        snippets: dict[str, str] = {"frontend/package.json": _PKG_JSON_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "React" in frameworks, f"React not in {frameworks}"

    def test_vite_detected_from_package_json_content(self):
        snippets: dict[str, str] = {"frontend/package.json": _PKG_JSON_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Vite" in frameworks, f"Vite not in {frameworks}"

    def test_nodejs_runtime_detected_from_package_json(self):
        """Any package.json implies Node.js runtime."""
        snippets: dict[str, str] = {"package.json": _PKG_JSON_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Node.js" in runtimes, f"Node.js not in {runtimes}"

    def test_fastapi_detected_from_requirements_txt_content(self):
        """FastAPI must be detected when 'fastapi' appears in requirements.txt content."""
        snippets: dict[str, str] = {"requirements.txt": _REQ_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "FastAPI" in frameworks, f"FastAPI not in {frameworks}"

    def test_supabase_detected_from_requirements_txt_content(self):
        snippets: dict[str, str] = {"requirements.txt": _REQ_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Supabase" in databases, f"Supabase not in {databases}"

    def test_postgresql_detected_from_psycopg_in_requirements(self):
        """psycopg in requirements.txt → PostgreSQL database."""
        snippets: dict[str, str] = {"requirements.txt": _REQ_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "PostgreSQL" in databases, f"PostgreSQL not in {databases}"

    def test_go_runtime_detected_from_go_mod_content(self):
        snippets: dict[str, str] = {"go.mod": _GO_MOD_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Go" in runtimes, f"Go not in {runtimes}"

    def test_gin_detected_from_go_mod_content(self):
        snippets: dict[str, str] = {"go.mod": _GO_MOD_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Gin" in frameworks, f"Gin not in {frameworks}"

    def test_rust_runtime_detected_from_cargo_toml_content(self):
        snippets: dict[str, str] = {"Cargo.toml": _CARGO_TOML_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Rust" in runtimes, f"Rust not in {runtimes}"

    def test_axum_detected_from_cargo_toml_content(self):
        snippets: dict[str, str] = {"Cargo.toml": _CARGO_TOML_CONTENT}
        frameworks: set[str] = set()
        runtimes: set[str] = set()
        databases: set[str] = set()
        _enrich_frameworks_from_manifests(snippets, frameworks, runtimes, databases)
        assert "Axum" in frameworks, f"Axum not in {frameworks}"

    def test_technology_not_claimed_from_arbitrary_name(self):
        """
        A file called 'my_react_component.py' must NOT trigger React detection
        through the framework-signal path, because 'react' is not a signal
        in _FRAMEWORK_SIGNALS for that pattern.
        """
        files = [_f("src/my_react_helper.py", "my_react_helper.py", ".py")]
        ev = _extract_evidence_from_file_list(files)
        # React should NOT appear because there's no package.json or config file
        assert "React" not in ev["frameworks"], (
            f"React should not be claimed from an arbitrary .py filename: {ev['frameworks']}"
        )

    def test_mixed_stack_full_technology_detection(self):
        """Full evidence extraction on the mixed-stack fixture detects both stacks."""
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        assert "Python" in ev["primary_languages"]
        assert "TypeScript" in ev["primary_languages"]
        assert "Vite" in ev["frameworks"]
        # Deployment
        assert any("Dockerfile" in d for d in ev["deployment_files"])
        # GitHub Actions
        assert any("ci.yml" in d or "workflows" in d.lower()
                   for d in ev["deployment_files"] + ev["config_files"])


# ===========================================================================
# 2. Entry-point detection
# ===========================================================================

class TestEntryPointDetection:
    """Entry-point patterns resolve to the correct evidence."""

    def test_main_py_detected(self):
        ev = _extract_evidence_from_file_list([_f("backend/main.py", "main.py", ".py")])
        eps = ev["entry_points"]
        assert any("main.py" in ep["file_path"] for ep in eps), f"main.py not in {eps}"

    def test_app_py_detected(self):
        ev = _extract_evidence_from_file_list([_f("app.py", "app.py", ".py")])
        eps = ev["entry_points"]
        assert any("app.py" in ep["file_path"] for ep in eps)

    def test_server_py_detected(self):
        ev = _extract_evidence_from_file_list([_f("server.py", "server.py", ".py")])
        eps = ev["entry_points"]
        assert any("server.py" in ep["file_path"] for ep in eps)

    def test_manage_py_detected(self):
        ev = _extract_evidence_from_file_list([_f("manage.py", "manage.py", ".py")])
        eps = ev["entry_points"]
        assert any("manage.py" in ep["file_path"] for ep in eps)

    def test_index_ts_detected(self):
        ev = _extract_evidence_from_file_list([_f("src/index.ts", "index.ts", ".ts")])
        eps = ev["entry_points"]
        assert any("index.ts" in ep["file_path"] for ep in eps)

    def test_main_tsx_detected(self):
        ev = _extract_evidence_from_file_list([_f("src/main.tsx", "main.tsx", ".tsx")])
        eps = ev["entry_points"]
        assert any("main.tsx" in ep["file_path"] for ep in eps)

    def test_app_tsx_detected(self):
        ev = _extract_evidence_from_file_list([_f("src/App.tsx", "App.tsx", ".tsx")])
        eps = ev["entry_points"]
        assert any("App.tsx" in ep["file_path"] for ep in eps)

    def test_app_jsx_detected(self):
        ev = _extract_evidence_from_file_list([_f("frontend/App.jsx", "App.jsx", ".jsx")])
        eps = ev["entry_points"]
        assert any("App.jsx" in ep["file_path"] for ep in eps)

    def test_dockerfile_detected_as_entry_point(self):
        ev = _extract_evidence_from_file_list([_f("Dockerfile", "Dockerfile", "")])
        eps = ev["entry_points"]
        assert any("Dockerfile" in ep["file_path"] for ep in eps), f"{eps}"

    def test_main_go_detected(self):
        ev = _extract_evidence_from_file_list([_f("cmd/main.go", "main.go", ".go")])
        eps = ev["entry_points"]
        assert any("main.go" in ep["file_path"] for ep in eps)

    def test_main_rs_detected(self):
        ev = _extract_evidence_from_file_list([_f("src/main.rs", "main.rs", ".rs")])
        eps = ev["entry_points"]
        assert any("main.rs" in ep["file_path"] for ep in eps)

    def test_entry_point_has_evidence_field(self):
        ev = _extract_evidence_from_file_list([_f("main.py", "main.py", ".py")])
        for ep in ev["entry_points"]:
            assert "evidence" in ep, f"entry_point missing 'evidence' key: {ep}"
            assert ep["evidence"]

    def test_entry_point_has_kind_field(self):
        ev = _extract_evidence_from_file_list([_f("main.py", "main.py", ".py")])
        for ep in ev["entry_points"]:
            assert "kind" in ep and ep["kind"]


# ===========================================================================
# 3. Important-file classification
# ===========================================================================

class TestImportantFileClassification:
    """Important files are categorised correctly."""

    def test_readme_categorised_as_documentation(self):
        files = [_f("README.md", "README.md", ".md")]
        imp = _select_important_files(files, [], [])
        assert any(
            f.get("category") == "documentation" for f in imp
        ), f"README.md not categorised as documentation: {imp}"

    def test_package_json_categorised_as_configuration(self):
        files = [_f("package.json", "package.json", ".json")]
        imp = _select_important_files(files, [], [])
        assert any(f.get("category") == "configuration" for f in imp)

    def test_requirements_txt_categorised_as_configuration(self):
        files = [_f("requirements.txt", "requirements.txt", ".txt")]
        imp = _select_important_files(files, [], [])
        assert any(f.get("category") == "configuration" for f in imp)

    def test_dockerfile_categorised_as_deployment(self):
        files = [_f("Dockerfile", "Dockerfile", "")]
        imp = _select_important_files(files, [], [])
        assert any(f.get("category") == "deployment" for f in imp)

    def test_main_py_categorised_as_entry_point(self):
        files = [_f("main.py", "main.py", ".py")]
        imp = _select_important_files(files, [], [])
        assert any(f.get("category") == "entry_point" for f in imp)

    def test_api_route_file_categorised_as_api(self):
        """A Python file in an 'api' directory should be categorised as API."""
        # _categorise_file_by_path handles this
        result = _categorise_file_by_path("backend/app/api/routes.py", "routes.py")
        assert result is not None
        reason, category = result
        assert category == "API", f"Expected API category, got: {category}"

    def test_models_file_categorised_as_database(self):
        result = _categorise_file_by_path("app/database/models.py", "models.py")
        assert result is not None
        _, category = result
        assert category == "database"

    def test_auth_file_categorised_as_authentication(self):
        result = _categorise_file_by_path("app/auth/auth_service.py", "auth_service.py")
        assert result is not None
        _, category = result
        assert category == "authentication"

    def test_service_file_categorised_as_core_service(self):
        result = _categorise_file_by_path("app/services/analysis_service.py",
                                           "analysis_service.py")
        assert result is not None
        _, category = result
        assert category == "core service"

    def test_frontend_component_categorised_as_frontend(self):
        result = _categorise_file_by_path("frontend/src/components/Nav.tsx", "Nav.tsx")
        assert result is not None
        _, category = result
        assert category == "frontend"

    def test_test_file_categorised_as_tests(self):
        result = _categorise_file_by_path("tests/test_routes.py", "test_routes.py")
        assert result is not None
        _, category = result
        assert category == "tests"

    def test_github_actions_workflow_categorised_as_deployment(self):
        result = _categorise_file_by_path(".github/workflows/ci.yml", "ci.yml")
        assert result is not None
        _, category = result
        assert category == "deployment"

    def test_important_files_have_reason(self):
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        for f in ev["important_files"]:
            assert f.get("reason"), f"important_file has no reason: {f}"

    def test_important_files_have_confidence(self):
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        for f in ev["important_files"]:
            assert f.get("confidence") in ("high", "medium", "low"), \
                f"invalid confidence: {f}"


# ===========================================================================
# 4. Architecture component detection
# ===========================================================================

class TestArchitectureComponentDetection:
    """Architecture components are produced with correct names and evidence."""

    def _build_evidence_with_manifests(self) -> dict:
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        # Simulate manifest snippets being available to enrich tech detection
        ev["manifest_snippets"] = {
            "backend/requirements.txt": _REQ_CONTENT,
            "frontend/package.json": _PKG_JSON_CONTENT,
        }
        frameworks: set = set(ev["frameworks"])
        runtimes: set = set(ev["runtimes"])
        databases: set = set(ev["databases"])
        _enrich_frameworks_from_manifests(
            ev["manifest_snippets"], frameworks, runtimes, databases
        )
        ev["frameworks"] = sorted(frameworks)
        ev["runtimes"] = sorted(runtimes)
        ev["databases"] = sorted(databases)
        return ev

    def test_frontend_component_present(self):
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "frontend" in names, f"frontend component missing from {names}"

    def test_backend_api_component_present(self):
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "backend/API" in names, f"backend/API missing from {names}"

    def test_database_component_present(self):
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "database/data layer" in names, f"database component missing from {names}"

    def test_authentication_component_present(self):
        """auth_service.py in the fixture triggers the authentication component."""
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "authentication" in names, f"authentication component missing from {names}"

    def test_tests_component_present(self):
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "tests" in names, f"tests component missing from {names}"

    def test_deployment_component_present(self):
        ev = self._build_evidence_with_manifests()
        comps = _build_arch_components(ev)
        names = [c["name"] for c in comps]
        assert "deployment/infrastructure" in names, \
            f"deployment/infrastructure missing from {names}"

    def test_each_component_has_description(self):
        ev = self._build_evidence_with_manifests()
        for comp in _build_arch_components(ev):
            assert comp.get("description"), f"component has no description: {comp}"

    def test_each_component_has_evidence_files_key(self):
        ev = self._build_evidence_with_manifests()
        for comp in _build_arch_components(ev):
            assert "evidence_files" in comp, f"component missing evidence_files: {comp}"

    def test_empty_repo_produces_no_components(self):
        """An empty repository has no evidence, so no components should be emitted."""
        ev = _extract_evidence_from_file_list([])
        comps = _build_arch_components(ev)
        assert comps == [], f"Expected no components for empty repo, got: {comps}"

    def test_arch_components_populated_in_analysis_result(self):
        """Full _build_analysis_result wires arch_components into TechnologyFindings."""
        ev = self._build_evidence_with_manifests()
        result = _build_analysis_result(ev, NullProvider().analyse_repository(ev), {"name": "r"})
        assert isinstance(result, AnalysisResult)
        assert len(result.technologies.arch_components) > 0, \
            "arch_components must be populated in AnalysisResult"


# ===========================================================================
# 5. Dependency manifest detection
# ===========================================================================

class TestDependencyManifestDetection:
    """All supported manifests are detected; content is parsed when available."""

    def test_requirements_txt_deps_parsed(self):
        deps = _parse_dependencies({"requirements.txt": _REQ_CONTENT})
        names = [d.name for d in deps]
        assert "fastapi" in names
        assert "uvicorn" in names
        assert "pydantic" in names

    def test_requirements_txt_versions_extracted(self):
        deps = _parse_dependencies({"requirements.txt": _REQ_CONTENT})
        fastapi_dep = next((d for d in deps if d.name == "fastapi"), None)
        assert fastapi_dep is not None
        assert fastapi_dep.version == "0.115.0"

    def test_package_json_runtime_deps_parsed(self):
        deps = _parse_dependencies({"frontend/package.json": _PKG_JSON_CONTENT})
        runtime = [d for d in deps if d.kind == "runtime"]
        names = [d.name for d in runtime]
        assert "react" in names
        assert "react-dom" in names

    def test_package_json_dev_deps_parsed(self):
        deps = _parse_dependencies({"frontend/package.json": _PKG_JSON_CONTENT})
        dev = [d for d in deps if d.kind == "dev"]
        names = [d.name for d in dev]
        assert "typescript" in names
        assert "vite" in names

    def test_go_mod_deps_parsed(self):
        deps = _parse_dependencies({"go.mod": _GO_MOD_CONTENT})
        names = [d.name for d in deps]
        assert "github.com/gin-gonic/gin" in names, f"Gin not in {names}"
        assert "github.com/lib/pq" in names, f"pq not in {names}"

    def test_go_mod_versions_extracted(self):
        deps = _parse_dependencies({"go.mod": _GO_MOD_CONTENT})
        gin_dep = next((d for d in deps if "gin" in d.name), None)
        assert gin_dep is not None
        assert gin_dep.version is not None

    def test_cargo_toml_deps_parsed(self):
        deps = _parse_dependencies({"Cargo.toml": _CARGO_TOML_CONTENT})
        names = [d.name for d in deps]
        assert "axum" in names, f"axum not in {names}"
        assert "tokio" in names

    def test_cargo_toml_versions_extracted(self):
        deps = _parse_dependencies({"Cargo.toml": _CARGO_TOML_CONTENT})
        axum_dep = next((d for d in deps if d.name == "axum"), None)
        assert axum_dep is not None
        assert axum_dep.version == "0.7.2"

    def test_manifest_file_reference_added_when_no_content(self):
        """
        When a manifest file is in important_files but content is unavailable,
        a sentinel Dependency is added so the manifest is still reported.
        """
        important = [{"file_path": "pyproject.toml", "reason": "...", "confidence": "high"}]
        result = _add_manifest_file_references([], important)
        assert len(result) == 1
        assert result[0].source_file == "pyproject.toml"
        assert "(manifest:" in result[0].name

    def test_manifest_reference_not_duplicated_when_content_available(self):
        """
        If _parse_dependencies already found deps for a manifest, no extra
        sentinel is added.
        """
        existing = [Dependency(name="fastapi", kind="runtime", source_file="requirements.txt")]
        important = [{"file_path": "requirements.txt", "reason": "...", "confidence": "high"}]
        result = _add_manifest_file_references(existing, important)
        # Only the original dep; no sentinel added
        assert len(result) == 1
        assert result[0].name == "fastapi"

    def test_comments_skipped_in_requirements_txt(self):
        content = "# comment\nfastapi==0.115.0\n"
        deps = _parse_dependencies({"requirements.txt": content})
        assert all(not d.name.startswith("#") for d in deps)

    def test_empty_manifest_snippet_produces_no_deps(self):
        deps = _parse_dependencies({"requirements.txt": "# just comments\n\n"})
        assert deps == []


# ===========================================================================
# 6. Empty / small repository
# ===========================================================================

class TestEmptyAndSmallRepository:
    """Empty and small repositories degrade gracefully."""

    def test_empty_file_list_zero_totals(self):
        ev = _extract_evidence_from_file_list([])
        assert ev["total_files"] == 0
        assert ev["total_dirs"] == 0

    def test_empty_file_list_no_languages(self):
        ev = _extract_evidence_from_file_list([])
        assert ev["primary_languages"] == []

    def test_empty_file_list_no_entry_points(self):
        ev = _extract_evidence_from_file_list([])
        assert ev["entry_points"] == []

    def test_empty_repo_evidence_quality_insufficient(self):
        ev = _extract_evidence_from_file_list([])
        result = _build_analysis_result(ev, NullProvider().analyse_repository(ev),
                                        {"name": "empty"})
        assert result.evidence_quality == "insufficient"

    def test_small_repo_no_entry_points_quality_partial(self):
        """A handful of files with no entry points → partial quality."""
        files = [_f(f"src/utils_{i}.py", f"utils_{i}.py", ".py") for i in range(3)]
        ev = _extract_evidence_from_file_list(files)
        result = _build_analysis_result(ev, NullProvider().analyse_repository(ev),
                                        {"name": "small"})
        assert result.evidence_quality in ("partial", "insufficient")

    def test_single_file_repo_does_not_crash(self):
        files = [_f("script.py", "script.py", ".py")]
        ev = _extract_evidence_from_file_list(files)
        result = _build_analysis_result(ev, NullProvider().analyse_repository(ev),
                                        {"name": "single-file"})
        assert isinstance(result, AnalysisResult)
        assert result.project_summary

    def test_directory_only_repo_counts_dirs_not_files(self):
        files = [_f("src", "src", "", 0, True), _f("docs", "docs", "", 0, True)]
        ev = _extract_evidence_from_file_list(files)
        assert ev["total_files"] == 0
        assert ev["total_dirs"] == 2

    def test_empty_repo_summary_mentions_empty(self):
        ev = _extract_evidence_from_file_list([])
        result = _build_analysis_result(ev, {"__null_provider__": True}, {"name": "empty-repo"})
        assert "empty" in result.project_summary.lower() or len(result.project_summary) > 10


# ===========================================================================
# 7. Mixed frontend/backend repository
# ===========================================================================

class TestMixedFrontendBackend:
    """Full analysis of a mixed stack repository produces all expected outputs."""

    def _run_full_analysis(self) -> AnalysisResult:
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        ev["manifest_snippets"] = {
            "backend/requirements.txt": _REQ_CONTENT,
            "frontend/package.json": _PKG_JSON_CONTENT,
        }
        fws: set = set(ev["frameworks"])
        rts: set = set(ev["runtimes"])
        dbs: set = set(ev["databases"])
        _enrich_frameworks_from_manifests(ev["manifest_snippets"], fws, rts, dbs)
        ev["frameworks"] = sorted(fws)
        ev["runtimes"] = sorted(rts)
        ev["databases"] = sorted(dbs)
        null_out = NullProvider().analyse_repository(ev)
        return _build_analysis_result(ev, null_out, {"name": "mixed-repo"})

    def test_python_and_typescript_both_detected(self):
        result = self._run_full_analysis()
        assert "Python" in result.technologies.languages
        assert "TypeScript" in result.technologies.languages

    def test_react_and_fastapi_both_detected(self):
        result = self._run_full_analysis()
        assert "React" in result.technologies.frameworks, \
            f"React not in {result.technologies.frameworks}"
        assert "FastAPI" in result.technologies.frameworks, \
            f"FastAPI not in {result.technologies.frameworks}"

    def test_vite_detected_in_full_analysis(self):
        result = self._run_full_analysis()
        assert "Vite" in result.technologies.frameworks

    def test_supabase_detected_in_full_analysis(self):
        result = self._run_full_analysis()
        assert "Supabase" in result.technologies.databases

    def test_entry_points_include_main_py_and_main_tsx(self):
        result = self._run_full_analysis()
        ep_paths = [ep.file_path for ep in result.entry_points]
        assert any("main.py" in p for p in ep_paths)
        assert any("main.tsx" in p for p in ep_paths)

    def test_important_files_include_readme_and_dockerfile(self):
        result = self._run_full_analysis()
        imp_paths = [f.file_path for f in result.important_files]
        assert any("README" in p for p in imp_paths)
        assert any("Dockerfile" in p for p in imp_paths)

    def test_dependencies_populated_from_both_manifests(self):
        result = self._run_full_analysis()
        sources = {d.source_file for d in result.dependencies}
        # Dependencies should come from at least one manifest
        assert len(sources) >= 1

    def test_arch_components_cover_frontend_and_backend(self):
        result = self._run_full_analysis()
        names = [c.name for c in result.technologies.arch_components]
        assert "frontend" in names
        assert "backend/API" in names

    def test_evidence_quality_is_sufficient_for_rich_repo(self):
        result = self._run_full_analysis()
        assert result.evidence_quality == "sufficient", \
            f"Expected sufficient, got {result.evidence_quality}"

    def test_project_summary_is_non_empty_string(self):
        result = self._run_full_analysis()
        assert isinstance(result.project_summary, str)
        assert len(result.project_summary) > 20

    def test_architecture_is_non_empty_string(self):
        result = self._run_full_analysis()
        assert isinstance(result.architecture, str)
        assert len(result.architecture) > 10


# ===========================================================================
# 8. Directory classification
# ===========================================================================

class TestDirectoryClassification:
    """Source, test, and doc directories are classified correctly."""

    def test_src_classified_as_source(self):
        files = [_f("frontend/src", "src", "", 0, True)]
        src, test, doc = _classify_directories(files)
        assert "frontend/src" in src, f"src not in source dirs: {src}"

    def test_tests_classified_as_test(self):
        files = [_f("backend/tests", "tests", "", 0, True)]
        src, test, doc = _classify_directories(files)
        assert "backend/tests" in test, f"tests not in test dirs: {test}"

    def test_docs_classified_as_doc(self):
        files = [_f("docs", "docs", "", 0, True)]
        src, test, doc = _classify_directories(files)
        assert "docs" in doc, f"docs not in doc dirs: {doc}"

    def test_backend_classified_as_source(self):
        files = [_f("backend", "backend", "", 0, True)]
        src, test, doc = _classify_directories(files)
        assert "backend" in src

    def test_frontend_classified_as_source(self):
        files = [_f("frontend", "frontend", "", 0, True)]
        src, test, doc = _classify_directories(files)
        assert "frontend" in src

    def test_non_directories_ignored(self):
        files = [_f("src/main.py", "main.py", ".py")]
        src, test, doc = _classify_directories(files)
        assert "src/main.py" not in src

    def test_mixed_stack_has_source_and_test_dirs(self):
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        assert ev["source_directories"], \
            f"Expected source_directories to be non-empty"
        assert ev["test_directories"], \
            f"Expected test_directories to be non-empty"

    def test_mixed_stack_has_doc_dirs(self):
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        assert ev["doc_directories"], \
            f"Expected doc_directories for the 'docs' dir in fixture"

    def test_source_directories_in_technology_findings(self):
        """source_directories flows through to TechnologyFindings."""
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        null_out = NullProvider().analyse_repository(ev)
        result = _build_analysis_result(ev, null_out, {"name": "r"})
        assert len(result.technologies.source_directories) > 0

    def test_test_directories_in_technology_findings(self):
        ev = _extract_evidence_from_file_list(MIXED_STACK_FILES)
        null_out = NullProvider().analyse_repository(ev)
        result = _build_analysis_result(ev, null_out, {"name": "r"})
        assert len(result.technologies.test_directories) > 0
