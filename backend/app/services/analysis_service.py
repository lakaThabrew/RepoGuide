"""
analysis_service.py — Repository analysis foundation.

Flow:
  1. Load repository record + file list from Supabase
  2. Extract structured evidence from file metadata (names, paths, extensions)
  3. Optionally enrich select key files with content snippets (capped, sanitised)
  4. Call AI provider (NullProvider until a real one is configured)
  5. Merge AI output with evidence-only findings
  6. Validate result against AnalysisResult schema
  7. Persist to analyses table; update repository status

SECURITY:
  - Repository file CONTENT is only read for a small allow-list of manifest
    files (package.json, requirements.txt, etc.) with a hard character cap.
  - Content is treated as untrusted DATA at all times.
  - Prompt injection patterns in file names/content are detected and flagged.
  - Credentials / .env content are never forwarded to the AI.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.database.supabase import get_supabase
from app.schemas.analysis import (
    AnalysisResult,
    Dependency,
    EntryPoint,
    FileEvidence,
    RouteEvidence,
    TechnologyFindings,
)
from app.services.ai_provider import NullProvider, get_provider
from app.services.github_service import scan_repository_files
from app.services.repository_service import get_repository, update_repository_status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CONTENT_BYTES = 8_000          # max bytes read from any single manifest file
MAX_SNIPPET_FILES = 10             # max manifest files to read content from

# Manifest files from which we read limited content for evidence
MANIFEST_FILENAMES = {
    "package.json", "package-lock.json", "yarn.lock",
    "requirements.txt", "Pipfile", "Pipfile.lock", "pyproject.toml", "setup.py", "setup.cfg",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json",
    "Gemfile", "Gemfile.lock",
    "*.csproj",                    # matched by suffix below
    "Makefile", "makefile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example",               # safe — example only, never .env itself
}

MANIFEST_SUFFIXES = {".toml", ".gradle", ".csproj"}

# Files that must NEVER be read for content under any circumstances
FORBIDDEN_CONTENT_FILES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".env.test", ".secret", "secrets.yml",
    "secrets.yaml", "id_rsa", "id_ed25519", ".npmrc", ".pypirc",
}

# Prompt-injection detection pattern (applied to file names and snippets)
_INJECTION_RE = re.compile(
    r"ignore\s+(all\s+)?previous\s+instructions?"
    r"|new\s+system\s+prompt"
    r"|you\s+are\s+now"
    r"|pretend\s+you\s+are"    # matches "pretend_you_are" when underscores treated as \W
    r"|pretend.you.are"        # also matches underscore-separated variants
    r"|act\s+as\s+(?:an?\s+)?(?:ai|assistant|gpt|claude)"
    r"|disregard\s+(all\s+)?prior",
    re.IGNORECASE,
)

# Language detection by extension
EXTENSION_LANGUAGES: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
    ".swift": "Swift", ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir",
    ".hs": "Haskell", ".clj": "Clojure", ".r": "R",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".css": "CSS", ".scss": "CSS/SCSS", ".sass": "CSS/SCSS",
    ".sql": "SQL", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".tf": "Terraform", ".hcl": "HCL",
    ".md": "Markdown", ".rst": "reStructuredText",
}

# Framework/runtime signals from file names and paths
_FRAMEWORK_SIGNALS: list[tuple[str, str, str]] = [
    # (pattern_in_path_or_name, framework_label, kind)
    # kind: "framework", "runtime", "package_manager"
    ("next.config",         "Next.js",          "framework"),
    ("nuxt.config",         "Nuxt.js",          "framework"),
    ("angular.json",        "Angular",          "framework"),
    ("vue.config",          "Vue.js",           "framework"),
    ("svelte.config",       "Svelte",           "framework"),
    ("remix.config",        "Remix",            "framework"),
    ("gatsby-config",       "Gatsby",           "framework"),
    ("astro.config",        "Astro",            "framework"),
    ("vite.config",         "Vite",             "framework"),
    ("webpack.config",      "Webpack",          "framework"),
    ("tailwind.config",     "Tailwind CSS",     "framework"),
    (".django",             "Django",           "framework"),
    ("manage.py",           "Django",           "framework"),
    ("wsgi.py",             "Django/WSGI",      "framework"),
    ("asgi.py",             "Django/ASGI",      "framework"),
    ("flask",               "Flask",            "framework"),
    ("fastapi",             "FastAPI",          "framework"),
    ("express",             "Express.js",       "framework"),
    ("rails",               "Ruby on Rails",    "framework"),
    ("spring",              "Spring",           "framework"),
    ("laravel",             "Laravel",          "framework"),
    ("symfony",             "Symfony",          "framework"),
    ("phoenix",             "Phoenix",          "framework"),
    (".nvmrc",              "Node.js",          "runtime"),
    (".node-version",       "Node.js",          "runtime"),
    (".python-version",     "Python",           "runtime"),
    (".ruby-version",       "Ruby",             "runtime"),
    ("go.mod",              "Go",               "runtime"),
    ("Cargo.toml",          "Rust",             "runtime"),
    ("pom.xml",             "Java/Maven",       "runtime"),
    ("build.gradle",        "Java/Gradle",      "runtime"),
    ("yarn.lock",           "Yarn",             "package_manager"),
    ("pnpm-lock.yaml",      "pnpm",             "package_manager"),
    ("package-lock.json",   "npm",              "package_manager"),
    ("Pipfile",             "Pipenv",           "package_manager"),
    ("poetry.lock",         "Poetry",           "package_manager"),
    ("uv.lock",             "uv",               "package_manager"),
    ("Gemfile.lock",        "Bundler",          "package_manager"),
    ("composer.lock",       "Composer",         "package_manager"),
]

# Database signals
_DB_SIGNALS: list[tuple[str, str]] = [
    ("postgres",    "PostgreSQL"),
    ("psycopg",     "PostgreSQL"),
    ("mysql",       "MySQL"),
    ("sqlite",      "SQLite"),
    ("mongodb",     "MongoDB"),
    ("redis",       "Redis"),
    ("prisma",      "Prisma ORM"),
    ("sqlalchemy",  "SQLAlchemy"),
    ("typeorm",     "TypeORM"),
    ("mongoose",    "Mongoose"),
    ("supabase",    "Supabase"),
    ("firebase",    "Firebase"),
    ("dynamodb",    "DynamoDB"),
    ("elasticsearch", "Elasticsearch"),
]

# Auth signals
_AUTH_SIGNALS: list[tuple[str, str]] = [
    ("auth",       "authentication"),
    ("oauth",      "OAuth"),
    ("jwt",        "JWT"),
    ("passport",   "Passport.js"),
    ("devise",     "Devise (Ruby)"),
    ("nextauth",   "NextAuth.js"),
    ("keycloak",   "Keycloak"),
    ("clerk",      "Clerk"),
    ("supabase",   "Supabase Auth"),
    ("firebase",   "Firebase Auth"),
    ("cognito",    "AWS Cognito"),
    ("ldap",       "LDAP"),
    ("saml",       "SAML"),
]

# Entry point patterns
_ENTRY_POINT_PATTERNS: list[tuple[str, str]] = [
    ("main.py",        "Python application entry point"),
    ("app.py",         "Python application entry point"),
    ("server.py",      "Python server entry point"),
    ("run.py",         "Python run script"),
    ("manage.py",      "Django management entry point"),
    ("index.js",       "JavaScript entry point"),
    ("index.ts",       "TypeScript entry point"),
    ("server.js",      "Node.js server entry point"),
    ("server.ts",      "Node.js/TypeScript server entry point"),
    ("main.ts",        "TypeScript entry point"),
    ("main.go",        "Go application entry point"),
    ("main.rs",        "Rust application entry point"),
    ("Application.java", "Java application entry point"),
    ("Program.cs",     "C# application entry point"),
    ("index.html",     "Web frontend entry point"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contains_injection(text: str) -> bool:
    """Return True if text contains prompt-injection patterns."""
    return bool(_INJECTION_RE.search(text))


def _safe_read_file(path: Path, max_bytes: int = MAX_CONTENT_BYTES) -> Optional[str]:
    """
    Read up to max_bytes from a file.
    Returns None if the file is forbidden, too large, or unreadable.
    Never reads .env or credential files.
    """
    filename_lower = path.name.lower()

    # Hard safety check — never read credential/env files
    if filename_lower in FORBIDDEN_CONTENT_FILES:
        logger.warning("Refusing to read forbidden file: %s", path)
        return None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(max_bytes)
        return content
    except OSError:
        return None


def _is_manifest_file(file_name: str, extension: str) -> bool:
    return (
        file_name in MANIFEST_FILENAMES
        or extension in MANIFEST_SUFFIXES
    )


# ---------------------------------------------------------------------------
# Evidence extraction — operates on file METADATA, not content
# ---------------------------------------------------------------------------

def _extract_evidence_from_file_list(
    files: list[dict],
    repo_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build a structured evidence dict purely from file metadata (paths, names,
    extensions).  For a small allow-list of manifest files, read limited
    content from disk if repo_path is provided.

    Returns a plain dict safe to serialise and pass to the AI.
    """
    languages: dict[str, int] = {}           # lang -> file count
    frameworks: set[str] = set()
    runtimes: set[str] = set()
    package_managers: set[str] = set()
    databases: set[str] = set()
    auth_findings: list[dict] = []
    test_files: list[str] = []
    config_files: list[str] = []
    deployment_files: list[str] = []
    important_dirs: set[str] = set()
    important_files_evidence: list[dict] = []
    entry_points_evidence: list[dict] = []
    api_routes: list[dict] = []
    backend_components: set[str] = set()
    frontend_components: set[str] = set()
    manifest_snippets: dict[str, str] = {}
    dev_commands: list[str] = []
    injection_warnings: list[str] = []
    total_files = 0
    total_dirs = 0

    manifest_read_count = 0

    for f in files:
        path_str: str = f.get("file_path", "")
        name: str = f.get("file_name", "")
        ext: str = (f.get("extension") or "").lower()
        is_dir: bool = f.get("is_directory", False)
        name_lower = name.lower()
        path_lower = path_str.lower()

        # Injection check on file paths
        if _contains_injection(path_str) or _contains_injection(name):
            injection_warnings.append(path_str)
            logger.warning("Prompt injection pattern detected in file path: %s", path_str)
            continue  # skip this file entirely

        if is_dir:
            total_dirs += 1
            # Track important top-level directories
            parts = path_str.split("/")
            if len(parts) == 1:
                important_dirs.add(path_str)
            continue

        total_files += 1

        # --- Language counting ---
        lang = EXTENSION_LANGUAGES.get(ext)
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

        # --- Framework / runtime / package-manager signals ---
        for pattern, label, kind in _FRAMEWORK_SIGNALS:
            if pattern.lower() in path_lower or pattern.lower() in name_lower:
                if kind == "framework":
                    frameworks.add(label)
                elif kind == "runtime":
                    runtimes.add(label)
                elif kind == "package_manager":
                    package_managers.add(label)

        # --- Database signals (path/filename) ---
        for signal, label in _DB_SIGNALS:
            if signal in path_lower or signal in name_lower:
                databases.add(label)

        # --- Auth signals ---
        for signal, label in _AUTH_SIGNALS:
            if signal in path_lower or signal in name_lower:
                auth_findings.append({
                    "file_path": path_str,
                    "reason": f"Path contains auth signal '{signal}' suggesting {label}",
                    "confidence": "medium",
                })

        # --- Test files ---
        if (
            "test" in path_lower
            or "spec" in path_lower
            or name_lower.startswith("test_")
            or name_lower.endswith("_test.py")
            or name_lower.endswith(".test.js")
            or name_lower.endswith(".test.ts")
            or name_lower.endswith(".spec.js")
            or name_lower.endswith(".spec.ts")
        ):
            test_files.append(path_str)

        # --- Config files ---
        if (
            name_lower in {"jest.config.js", "tsconfig.json", "babel.config.js",
                           ".eslintrc.js", ".eslintrc.json", ".prettierrc",
                           "pytest.ini", "pyproject.toml", ".flake8",
                           "mypy.ini", ".mypy.ini", "setup.cfg"}
            or ext in {".env", ".cfg", ".ini", ".yaml", ".yml", ".toml"}
            or name_lower.startswith(".env")
        ):
            config_files.append(path_str)

        # --- Deployment files ---
        if (
            name_lower in {"dockerfile", "docker-compose.yml", "docker-compose.yaml",
                           ".github", "heroku.yml", "app.yaml", "fly.toml",
                           "render.yaml", "vercel.json", "netlify.toml",
                           "railway.json", ".railway", "serverless.yml",
                           "serverless.yaml", "template.yaml", "template.yml",
                           "cloudformation.yml", "cloudformation.yaml"}
            or ".github/workflows" in path_lower
            or "kubernetes" in path_lower
            or "k8s" in path_lower
            or name_lower.endswith(".tf")
        ):
            deployment_files.append(path_str)

        # --- Entry points ---
        for ep_name, ep_label in _ENTRY_POINT_PATTERNS:
            if name_lower == ep_name.lower():
                entry_points_evidence.append({
                    "file_path": path_str,
                    "kind": ep_label,
                    "evidence": f"File name '{name}' matches known entry-point pattern",
                })

        # --- Backend / frontend component dirs ---
        if any(seg in path_lower.split("/") for seg in ("api", "routes", "controllers",
                                                          "handlers", "views", "middleware")):
            backend_components.add(path_str.split("/")[0])
        if any(seg in path_lower.split("/") for seg in ("components", "pages", "layouts",
                                                          "hooks", "store", "styles",
                                                          "public", "assets")):
            frontend_components.add(path_str.split("/")[0])

        # --- API route evidence (Python FastAPI/Flask/Django pattern) ---
        if ext == ".py" and any(k in path_lower for k in ("routes", "api", "views", "urls")):
            api_routes.append({
                "file_path": path_str,
                "evidence": f"File path '{path_str}' is in a routes/api/views area",
            })

        # --- Manifest content snippets ---
        if (
            _is_manifest_file(name, ext)
            and repo_path
            and manifest_read_count < MAX_SNIPPET_FILES
            and name_lower not in FORBIDDEN_CONTENT_FILES
        ):
            full_path = Path(repo_path) / path_str
            content = _safe_read_file(full_path)
            if content:
                # Check content for injection
                if _contains_injection(content):
                    injection_warnings.append(f"{path_str}:content")
                    logger.warning("Prompt injection pattern in content of: %s", path_str)
                else:
                    # Redact anything that looks like a real secret
                    redacted = _redact_secrets(content)
                    manifest_snippets[path_str] = redacted
                    manifest_read_count += 1

    # Derive important files heuristically
    important_files_evidence = _select_important_files(files, entry_points_evidence, test_files)

    # Derive dev commands from manifest snippets
    dev_commands = _extract_dev_commands(manifest_snippets)

    # Determine primary language (most files)
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    primary_languages = [l for l, _ in sorted_langs[:5]]

    return {
        "total_files": total_files,
        "total_dirs": total_dirs,
        "primary_languages": primary_languages,
        "language_file_counts": dict(sorted_langs),
        "frameworks": sorted(frameworks),
        "runtimes": sorted(runtimes),
        "package_managers": sorted(package_managers),
        "databases": sorted(databases),
        "auth_signals": auth_findings[:20],     # cap for AI payload
        "test_files": test_files[:30],
        "config_files": config_files[:30],
        "deployment_files": deployment_files[:20],
        "important_directories": sorted(important_dirs)[:20],
        "important_files": important_files_evidence[:20],
        "entry_points": entry_points_evidence[:10],
        "api_route_files": api_routes[:20],
        "backend_components": sorted(backend_components)[:10],
        "frontend_components": sorted(frontend_components)[:10],
        "manifest_snippets": manifest_snippets,
        "dev_commands": dev_commands[:10],
        "injection_warnings": injection_warnings,
    }


def _select_important_files(
    files: list[dict],
    entry_points: list[dict],
    test_files: list[str],
) -> list[dict]:
    """Pick up to 20 files most likely to be important to a new developer."""
    important: list[dict] = []
    seen: set[str] = set()

    # Always-important filenames
    priority_names = {
        "readme.md", "readme.rst", "readme.txt", "readme",
        "contributing.md", "license", "license.md",
        "package.json", "requirements.txt", "pyproject.toml",
        "go.mod", "cargo.toml", "pom.xml",
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile", ".github",
        "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs",
    }

    for f in files:
        if f.get("is_directory"):
            continue
        name_lower = (f.get("file_name") or "").lower()
        path = f.get("file_path", "")
        if name_lower in priority_names and path not in seen:
            important.append({
                "file_path": path,
                "reason": "High-priority file for project understanding",
                "confidence": "high",
            })
            seen.add(path)

    for ep in entry_points:
        path = ep["file_path"]
        if path not in seen:
            important.append({
                "file_path": path,
                "reason": ep["kind"],
                "confidence": "high",
            })
            seen.add(path)

    return important[:20]


def _extract_dev_commands(manifest_snippets: dict[str, str]) -> list[str]:
    """
    Extract dev commands from package.json 'scripts' section or Makefile targets.
    Returns human-readable strings like 'npm run dev', 'make test'.
    """
    commands: list[str] = []

    for file_path, content in manifest_snippets.items():
        name = Path(file_path).name.lower()

        if name == "package.json":
            try:
                data = json.loads(content)
                scripts = data.get("scripts", {})
                for script_name, cmd in list(scripts.items())[:10]:
                    commands.append(f"npm run {script_name}  # {cmd}")
            except (json.JSONDecodeError, AttributeError):
                pass

        elif name in ("makefile", "makefile"):
            # Extract target names from lines like "target_name:"
            for line in content.splitlines()[:50]:
                m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_\-]*)\s*:", line)
                if m and not m.group(1).startswith("."):
                    commands.append(f"make {m.group(1)}")

    return commands


_SECRET_PATTERN = re.compile(
    r'(?i)(password|passwd|secret|api_key|apikey|token|private_key|access_key|auth_key'
    r'|database_url|db_url|db_password|connection_string|service_role)'
    r'\s*[:=]\s*\S+',
)


def _redact_secrets(content: str) -> str:
    """Redact any key=value or key: value patterns that look like secrets."""
    return _SECRET_PATTERN.sub(r"\1: [REDACTED]", content)


# ---------------------------------------------------------------------------
# AI synthesis
# ---------------------------------------------------------------------------

def _build_analysis_result(
    evidence: dict[str, Any],
    ai_output: dict[str, Any],
    repo_meta: dict,
) -> AnalysisResult:
    """
    Merge evidence-layer findings with AI output into a validated AnalysisResult.
    If AI output has __null_provider__ flag, build an evidence-only summary.
    """
    null_provider = ai_output.get("__null_provider__", False)

    if null_provider:
        project_summary = _evidence_only_summary(evidence, repo_meta)
        architecture = _evidence_only_architecture(evidence)
    else:
        project_summary = ai_output.get("project_summary") or _evidence_only_summary(evidence, repo_meta)
        architecture = ai_output.get("architecture") or _evidence_only_architecture(evidence)

    # Determine evidence quality — sanitise to valid literal values only
    _VALID_QUALITY = {"sufficient", "partial", "insufficient"}
    total = evidence.get("total_files", 0)
    if total == 0:
        quality = "insufficient"
    elif total < 5 and not evidence.get("entry_points"):
        quality = "partial"
    else:
        raw_quality = ai_output.get("evidence_quality", "partial") if not null_provider else "partial"
        quality = raw_quality if raw_quality in _VALID_QUALITY else "partial"

    # Build technologies
    tech = TechnologyFindings(
        languages=evidence.get("primary_languages", []),
        frameworks=evidence.get("frameworks", []),
        runtimes=evidence.get("runtimes", []),
        package_managers=evidence.get("package_managers", []),
        databases=evidence.get("databases", []),
        auth_signals=[
            FileEvidence(**a) for a in evidence.get("auth_signals", [])[:10]
        ],
        test_files=evidence.get("test_files", [])[:20],
        config_files=evidence.get("config_files", [])[:20],
        deployment_files=evidence.get("deployment_files", []),
        dev_commands=evidence.get("dev_commands", []),
        api_routes=[
            RouteEvidence(
                file_path=r["file_path"],
                evidence=r["evidence"],
            )
            for r in evidence.get("api_route_files", [])
        ],
        backend_components=evidence.get("backend_components", []),
        frontend_components=evidence.get("frontend_components", []),
        important_directories=evidence.get("important_directories", []),
    )

    important_files = [
        FileEvidence(**f) for f in evidence.get("important_files", [])
    ]

    entry_points = [
        EntryPoint(
            file_path=ep["file_path"],
            kind=ep["kind"],
            evidence=ep["evidence"],
        )
        for ep in evidence.get("entry_points", [])
    ]

    # Parse dependencies from manifest snippets
    dependencies = _parse_dependencies(evidence.get("manifest_snippets", {}))

    return AnalysisResult(
        project_summary=project_summary,
        architecture=architecture,
        important_files=important_files,
        technologies=tech,
        entry_points=entry_points,
        dependencies=dependencies,
        evidence_quality=quality,  # type: ignore[arg-type]
    )


def _evidence_only_summary(evidence: dict[str, Any], repo_meta: dict) -> str:
    """Build a plain-language summary from evidence alone, no AI invention."""
    parts: list[str] = []
    name = repo_meta.get("name") or "this repository"
    desc = repo_meta.get("description")

    parts.append(f"Repository: {name}.")
    if desc:
        parts.append(f"GitHub description: {desc}.")

    langs = evidence.get("primary_languages", [])
    if langs:
        parts.append(f"Primary language(s): {', '.join(langs)}.")

    frameworks = evidence.get("frameworks", [])
    if frameworks:
        parts.append(f"Detected framework(s): {', '.join(frameworks)}.")

    total = evidence.get("total_files", 0)
    if total == 0:
        parts.append("No source files were found — repository may be empty.")
    else:
        parts.append(f"Contains {total} scanned source files.")

    if evidence.get("injection_warnings"):
        parts.append(
            "[WARNING: prompt-injection patterns were detected in repository content "
            "and those files were excluded from analysis.]"
        )

    parts.append(
        "(AI summary not available — configure AI_API_KEY to enable enriched descriptions.)"
    )
    return " ".join(parts)


def _evidence_only_architecture(evidence: dict[str, Any]) -> str:
    """Build a structural description from directory/file evidence alone."""
    parts: list[str] = []

    dirs = evidence.get("important_directories", [])
    if dirs:
        parts.append(f"Top-level directories: {', '.join(dirs)}.")

    backend = evidence.get("backend_components", [])
    if backend:
        parts.append(f"Backend component areas: {', '.join(backend)}.")

    frontend = evidence.get("frontend_components", [])
    if frontend:
        parts.append(f"Frontend component areas: {', '.join(frontend)}.")

    deploys = evidence.get("deployment_files", [])
    if deploys:
        parts.append(f"Deployment-related files: {', '.join(deploys[:5])}.")

    if not parts:
        return "Insufficient evidence to determine architecture."

    return " ".join(parts)


def _parse_dependencies(manifest_snippets: dict[str, str]) -> list[Dependency]:
    """Extract dependency list from manifest file snippets."""
    deps: list[Dependency] = []

    for file_path, content in manifest_snippets.items():
        name = Path(file_path).name.lower()

        if name == "package.json":
            try:
                data = json.loads(content)
                for dep_name, version in list(data.get("dependencies", {}).items())[:50]:
                    deps.append(Dependency(
                        name=dep_name, version=str(version),
                        kind="runtime", source_file=file_path,
                    ))
                for dep_name, version in list(data.get("devDependencies", {}).items())[:30]:
                    deps.append(Dependency(
                        name=dep_name, version=str(version),
                        kind="dev", source_file=file_path,
                    ))
            except (json.JSONDecodeError, AttributeError):
                pass

        elif name == "requirements.txt":
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # parse "pkg==1.0" or "pkg>=1.0" or just "pkg"
                    m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*[><=!~^]+\s*(\S+)", line)
                    if m:
                        deps.append(Dependency(
                            name=m.group(1), version=m.group(2),
                            kind="runtime", source_file=file_path,
                        ))
                    else:
                        pkg = re.match(r"^([A-Za-z0-9_\-\.]+)", line)
                        if pkg:
                            deps.append(Dependency(
                                name=pkg.group(1), kind="runtime",
                                source_file=file_path,
                            ))

    return deps[:100]  # cap


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------

def _persist_analysis(repository_id: str, result: AnalysisResult) -> dict:
    """
    Write the analysis result to the analyses table.
    Uses jsonb columns for structured data and text columns for summaries.
    """
    supabase = get_supabase()

    # Serialise JSONB fields as plain Python objects (supabase-py handles JSON encoding)
    row = {
        "repository_id": repository_id,
        "project_summary": result.project_summary,
        "architecture": result.architecture,
        "setup_guide": None,         # populated in a later task
        "important_files": [f.model_dump() for f in result.important_files],
        "technologies": result.technologies.model_dump(),
        "entry_points": [ep.model_dump() for ep in result.entry_points],
        "dependencies": [d.model_dump() for d in result.dependencies],
    }

    response = supabase.table("analyses").upsert(
        row,
        on_conflict="repository_id",  # one analysis row per repo (update if re-run)
    ).execute()

    return response.data[0] if response.data else row


def _get_repository_files(repository_id: str) -> list[dict]:
    """Fetch the stored file list from Supabase for a given repository."""
    supabase = get_supabase()
    response = (
        supabase.table("repository_files")
        .select("file_path,file_name,extension,file_size,is_directory")
        .eq("repository_id", repository_id)
        .execute()
    )
    return response.data or []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_repository(repository_id: str) -> dict:
    """
    Main entry point: analyse a repository and persist the result.

    Returns a dict with keys:
      analysis_id, repository_id, status, evidence_quality, error (optional)

    Does NOT raise — all errors are captured and returned in the dict so the
    API layer can respond appropriately.
    """
    # 1. Load repository record
    try:
        repo = get_repository(repository_id)
    except Exception as exc:
        logger.error("Failed to fetch repository %s: %s", repository_id, exc)
        return {"repository_id": repository_id, "status": "error",
                "error": "Failed to retrieve repository record."}

    if not repo:
        return {"repository_id": repository_id, "status": "error",
                "error": "Repository not found."}

    # 2. Update status to 'analyzing'
    try:
        update_repository_status(repository_id, "analyzing")
    except Exception as exc:
        logger.warning("Could not update repository status: %s", exc)

    try:
        # 3. Fetch stored file list from Supabase
        file_list = _get_repository_files(repository_id)

        if not file_list:
            logger.info("No stored files for %s; repository may be empty or not yet scanned", repository_id)
            # Still attempt evidence extraction (will flag as insufficient)

        # 4. Extract structured evidence from file metadata
        evidence = _extract_evidence_from_file_list(
            file_list,
            repo_path=None,         # no local clone available — metadata-only
        )

        # 5. Guard: empty repo
        if evidence["total_files"] == 0 and evidence["total_dirs"] == 0:
            result = AnalysisResult(
                project_summary=(
                    f"Repository '{repo.get('name', repository_id)}' appears to be empty "
                    f"or has not been scanned yet. No file metadata is available."
                ),
                architecture="No structure evidence available.",
                evidence_quality="insufficient",  # type: ignore[arg-type]
            )
        else:
            # 6. Call AI provider
            provider = get_provider()
            if provider.is_available:
                try:
                    # Pass evidence (no raw file content) to the AI
                    ai_output = provider.analyse_repository(evidence)
                except Exception as exc:
                    logger.error("AI provider failed for %s: %s", repository_id, exc)
                    ai_output = {
                        "__null_provider__": True,
                        "project_summary": (
                            "AI analysis failed; evidence-only summary provided."
                        ),
                        "architecture": "",
                    }
            else:
                ai_output = provider.analyse_repository(evidence)  # returns NullProvider sentinel

            # 7. Build validated AnalysisResult
            result = _build_analysis_result(evidence, ai_output, repo)

        # 8. Persist to Supabase
        saved = _persist_analysis(repository_id, result)

        # 9. Update repository status
        try:
            update_repository_status(repository_id, "analyzed")
        except Exception as exc:
            logger.warning("Could not update repository status to analyzed: %s", exc)

        return {
            "analysis_id": saved.get("id"),
            "repository_id": repository_id,
            "status": "analyzed",
            "evidence_quality": result.evidence_quality,
        }

    except Exception as exc:
        logger.exception("Unexpected error during analysis of %s", repository_id)
        try:
            update_repository_status(repository_id, "error")
        except Exception:
            pass
        return {
            "repository_id": repository_id,
            "status": "error",
            "error": "Analysis failed due to an internal error.",
        }


def get_analysis(repository_id: str) -> Optional[dict]:
    """
    Retrieve the stored analysis for a repository from Supabase.
    Returns None if no analysis exists yet.
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("analyses")
            .select("*")
            .eq("repository_id", repository_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = response.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("Failed to retrieve analysis for %s: %s", repository_id, exc)
        return None
