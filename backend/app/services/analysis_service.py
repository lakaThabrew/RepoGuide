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
    ArchitectureComponent,
    ArchitectureData,
    ArchitectureRelationship,
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

# Entry point patterns: (filename, description, path_hint_optional)
# path_hint: if set, only matches when this string appears somewhere in the path
_ENTRY_POINT_PATTERNS: list[tuple[str, str, str]] = [
    ("main.py",          "Python application entry point",          ""),
    ("app.py",           "Python application entry point",          ""),
    ("server.py",        "Python server entry point",               ""),
    ("run.py",           "Python run script",                       ""),
    ("manage.py",        "Django management entry point",           ""),
    ("index.js",         "JavaScript entry point",                  ""),
    ("index.ts",         "TypeScript entry point",                  ""),
    ("server.js",        "Node.js server entry point",              ""),
    ("server.ts",        "Node.js/TypeScript server entry point",   ""),
    ("main.ts",          "TypeScript entry point",                  ""),
    ("main.jsx",         "React/JavaScript entry point",            ""),
    ("main.tsx",         "React/TypeScript entry point",            ""),
    ("index.jsx",        "React/JavaScript entry point",            ""),
    ("index.tsx",        "React/TypeScript entry point",            ""),
    ("App.tsx",          "React application root component",        ""),
    ("App.jsx",          "React application root component",        ""),
    ("App.js",           "React application root component",        ""),
    ("main.go",          "Go application entry point",              ""),
    ("main.rs",          "Rust application entry point",            ""),
    ("Application.java", "Java application entry point",            ""),
    ("Program.cs",       "C# application entry point",              ""),
    ("index.html",       "Web frontend entry point",                ""),
    ("Dockerfile",       "Container image build definition",        ""),
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
        for ep_name, ep_label, ep_path_hint in _ENTRY_POINT_PATTERNS:
            if name_lower == ep_name.lower():
                # If a path hint is specified, only match when hint appears in path
                if ep_path_hint and ep_path_hint.lower() not in path_lower:
                    continue
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

    # Enrich framework detection from manifest content
    _enrich_frameworks_from_manifests(manifest_snippets, frameworks, runtimes, databases)

    # Classify directories
    source_dirs, test_dirs, doc_dirs = _classify_directories(files)

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
        "source_directories": sorted(source_dirs)[:20],
        "test_directories": sorted(test_dirs)[:20],
        "doc_directories": sorted(doc_dirs)[:10],
        "important_files": important_files_evidence[:20],
        "entry_points": entry_points_evidence[:10],
        "api_route_files": api_routes[:20],
        "backend_components": sorted(backend_components)[:10],
        "frontend_components": sorted(frontend_components)[:10],
        "manifest_snippets": manifest_snippets,
        "dev_commands": dev_commands[:10],
        "injection_warnings": injection_warnings,
    }


# Mapping from lowercase filename → (reason, category) for important-file selection
_PRIORITY_FILE_MAP: dict[str, tuple[str, str]] = {
    "readme.md":              ("Project documentation entry point", "documentation"),
    "readme.rst":             ("Project documentation entry point", "documentation"),
    "readme.txt":             ("Project documentation entry point", "documentation"),
    "readme":                 ("Project documentation entry point", "documentation"),
    "contributing.md":        ("Contribution guide", "documentation"),
    "license":                ("Project licence", "documentation"),
    "license.md":             ("Project licence", "documentation"),
    "package.json":           ("Node.js dependency manifest", "configuration"),
    "requirements.txt":       ("Python dependency manifest", "configuration"),
    "pyproject.toml":         ("Python project / dependency manifest", "configuration"),
    "go.mod":                 ("Go module manifest", "configuration"),
    "cargo.toml":             ("Rust dependency manifest", "configuration"),
    "pom.xml":                ("Java/Maven dependency manifest", "configuration"),
    "build.gradle":           ("Java/Gradle build manifest", "configuration"),
    "dockerfile":             ("Container image build definition", "deployment"),
    "docker-compose.yml":     ("Multi-container orchestration definition", "deployment"),
    "docker-compose.yaml":    ("Multi-container orchestration definition", "deployment"),
    "makefile":               ("Project build / task runner", "configuration"),
    "main.py":                ("Python application entry point", "entry_point"),
    "app.py":                 ("Python application entry point", "entry_point"),
    "server.py":              ("Python server entry point", "entry_point"),
    "manage.py":              ("Django management entry point", "entry_point"),
    "index.js":               ("JavaScript entry point", "entry_point"),
    "index.ts":               ("TypeScript entry point", "entry_point"),
    "main.ts":                ("TypeScript entry point", "entry_point"),
    "main.tsx":               ("React/TypeScript entry point", "entry_point"),
    "main.jsx":               ("React/JavaScript entry point", "entry_point"),
    "app.tsx":                ("React application root component", "frontend"),
    "app.jsx":                ("React application root component", "frontend"),
    "main.go":                ("Go application entry point", "entry_point"),
    "main.rs":                ("Rust application entry point", "entry_point"),
}


def _select_important_files(
    files: list[dict],
    entry_points: list[dict],
    test_files: list[str],
) -> list[dict]:
    """Pick up to 20 files most likely to be important to a new developer."""
    important: list[dict] = []
    seen: set[str] = set()

    for f in files:
        if f.get("is_directory"):
            continue
        name_lower = (f.get("file_name") or "").lower()
        path = f.get("file_path", "")
        path_lower = path.lower()

        if name_lower in _PRIORITY_FILE_MAP and path not in seen:
            reason, category = _PRIORITY_FILE_MAP[name_lower]
            important.append({
                "file_path": path,
                "reason": reason,
                "confidence": "high",
                "category": category,
            })
            seen.add(path)
            continue

        # Categorise API/service/database files by path patterns
        if path not in seen:
            cat = _categorise_file_by_path(path_lower, name_lower)
            if cat:
                reason, category = cat
                important.append({
                    "file_path": path,
                    "reason": reason,
                    "confidence": "medium",
                    "category": category,
                })
                seen.add(path)

    for ep in entry_points:
        path = ep["file_path"]
        if path not in seen:
            important.append({
                "file_path": path,
                "reason": ep["kind"],
                "confidence": "high",
                "category": "entry_point",
            })
            seen.add(path)

    return important[:20]


def _categorise_file_by_path(path_lower: str, name_lower: str) -> Optional[tuple[str, str]]:
    """
    Return (reason, category) for a file based on path/name patterns,
    or None if it is not noteworthy.

    Checks are ordered from most-specific to least-specific to avoid false matches.
    Test files and auth files are checked before generic API/service patterns.
    """
    ext = "." + name_lower.rsplit(".", 1)[-1] if "." in name_lower else ""

    # Deployment / CI  (check early — very specific path)
    if ".github/workflows" in path_lower:
        return ("GitHub Actions CI/CD workflow", "deployment")

    # Test files  (check before API/service — test dirs often contain route names)
    if (
        "test" in path_lower or "spec" in path_lower
        or name_lower.startswith("test_") or name_lower.endswith("_test.py")
    ):
        if ext in (".py", ".ts", ".js", ".go", ".rs", ".java"):
            return ("Test file", "tests")

    # Authentication  (check before service — auth_service has 'auth' AND 'service')
    if any(k in path_lower for k in ("auth", "login", "oauth", "jwt", "token",
                                      "permission", "guard", "session")):
        if ext in (".py", ".ts", ".js", ".go", ".rs", ".java"):
            return ("Authentication / authorisation file", "authentication")

    # Database / ORM files
    if any(k in path_lower for k in ("models", "schema", "migration", "migrate",
                                      "database", "db", "orm")):
        if ext in (".py", ".ts", ".js", ".sql", ".go", ".rs"):
            return ("Database models / schema / migration file", "database")

    # API / route files
    if any(k in path_lower for k in ("api", "routes", "router", "controllers",
                                      "handlers", "views", "endpoints", "urls")):
        if ext in (".py", ".ts", ".js", ".go", ".rs", ".java"):
            return ("API route or controller file", "API")

    # Core service / business logic
    if any(k in path_lower for k in ("service", "services", "core", "logic",
                                      "business", "domain")):
        if ext in (".py", ".ts", ".js", ".go", ".rs", ".java"):
            return ("Core service / business logic file", "core service")

    # Frontend components
    if any(k in path_lower for k in ("components", "pages", "views", "layout",
                                      "hooks", "store", "context")):
        if ext in (".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte"):
            return ("Frontend component / page file", "frontend")

    return None


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


def _enrich_frameworks_from_manifests(
    manifest_snippets: dict[str, str],
    frameworks: set[str],
    runtimes: set[str],
    databases: set[str],
) -> None:
    """
    Detect technologies (React, Vite, Node.js, FastAPI, etc.) from manifest
    file *content* where content is available.  Mutates the passed sets in-place.

    This is the only place where manifest content is used for technology detection.
    Content is already redacted and injection-checked before reaching here.
    """
    for file_path, content in manifest_snippets.items():
        name = Path(file_path).name.lower()

        if name == "package.json":
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, AttributeError):
                continue

            # Collect all dependency names (runtime + dev)
            all_deps: set[str] = set()
            for dep_name in data.get("dependencies", {}):
                all_deps.add(dep_name.lower())
            for dep_name in data.get("devDependencies", {}):
                all_deps.add(dep_name.lower())

            # React
            if "react" in all_deps or "react-dom" in all_deps:
                frameworks.add("React")
            # React Router
            if "react-router" in all_deps or "react-router-dom" in all_deps:
                frameworks.add("React Router")
            # Vite
            if "vite" in all_deps:
                frameworks.add("Vite")
            # Next.js
            if "next" in all_deps:
                frameworks.add("Next.js")
            # Vue
            if "vue" in all_deps:
                frameworks.add("Vue.js")
            # Angular
            if "@angular/core" in all_deps:
                frameworks.add("Angular")
            # Svelte
            if "svelte" in all_deps:
                frameworks.add("Svelte")
            # Express
            if "express" in all_deps:
                frameworks.add("Express.js")
            # Fastify
            if "fastify" in all_deps:
                frameworks.add("Fastify")
            # Node.js runtime (package.json itself implies Node.js)
            runtimes.add("Node.js")
            # TypeScript
            if "typescript" in all_deps:
                runtimes.add("TypeScript")

        elif name in ("requirements.txt", "pipfile"):
            content_lower = content.lower()
            # FastAPI
            if "fastapi" in content_lower:
                frameworks.add("FastAPI")
            # Flask
            if "flask" in content_lower:
                frameworks.add("Flask")
            # Django
            if "django" in content_lower:
                frameworks.add("Django")
            # SQLAlchemy
            if "sqlalchemy" in content_lower:
                databases.add("SQLAlchemy")
            # Supabase
            if "supabase" in content_lower:
                databases.add("Supabase")
            # Psycopg → PostgreSQL
            if "psycopg" in content_lower:
                databases.add("PostgreSQL")
            # Alembic (migrations → DB)
            if "alembic" in content_lower:
                databases.add("SQLAlchemy (Alembic)")

        elif name == "pyproject.toml":
            content_lower = content.lower()
            if "fastapi" in content_lower:
                frameworks.add("FastAPI")
            if "flask" in content_lower:
                frameworks.add("Flask")
            if "django" in content_lower:
                frameworks.add("Django")
            if "sqlalchemy" in content_lower:
                databases.add("SQLAlchemy")
            if "supabase" in content_lower:
                databases.add("Supabase")

        elif name == "go.mod":
            content_lower = content.lower()
            runtimes.add("Go")
            if "gin-gonic" in content_lower or "gin" in content_lower:
                frameworks.add("Gin")
            if "echo" in content_lower:
                frameworks.add("Echo")
            if "fiber" in content_lower:
                frameworks.add("Fiber")

        elif name == "cargo.toml":
            content_lower = content.lower()
            runtimes.add("Rust")
            if "actix" in content_lower:
                frameworks.add("Actix-web")
            if "axum" in content_lower:
                frameworks.add("Axum")
            if "rocket" in content_lower:
                frameworks.add("Rocket")

        elif name in ("pom.xml", "build.gradle", "build.gradle.kts"):
            content_lower = content.lower()
            runtimes.add("Java")
            if "springframework" in content_lower or "spring-boot" in content_lower:
                frameworks.add("Spring Boot")
            if "quarkus" in content_lower:
                frameworks.add("Quarkus")
            if "micronaut" in content_lower:
                frameworks.add("Micronaut")


def _classify_directories(files: list[dict]) -> tuple[set[str], set[str], set[str]]:
    """
    Classify top-level and second-level directories into:
      source_dirs  — likely contain primary source code
      test_dirs    — likely contain tests
      doc_dirs     — likely contain documentation

    Returns (source_dirs, test_dirs, doc_dirs) as sets of directory paths.
    """
    source_dirs: set[str] = set()
    test_dirs: set[str] = set()
    doc_dirs: set[str] = set()

    _SOURCE_NAMES = frozenset({
        "src", "lib", "app", "backend", "frontend", "server", "client",
        "pkg", "internal", "cmd", "api", "core", "main",
    })
    _TEST_NAMES = frozenset({
        "tests", "test", "spec", "specs", "__tests__", "e2e",
        "integration", "unit", "test_suite",
    })
    _DOC_NAMES = frozenset({
        "docs", "doc", "documentation", "wiki", "guides", "examples",
    })

    for f in files:
        if not f.get("is_directory"):
            continue
        path_str: str = f.get("file_path", "")
        parts = [p.lower() for p in path_str.split("/") if p]
        if not parts:
            continue
        # Only look at top 2 levels
        for depth, part in enumerate(parts[:2]):
            dir_path = "/".join(path_str.split("/")[:depth + 1])
            if part in _SOURCE_NAMES:
                source_dirs.add(dir_path)
            elif part in _TEST_NAMES:
                test_dirs.add(dir_path)
            elif part in _DOC_NAMES:
                doc_dirs.add(dir_path)

    return source_dirs, test_dirs, doc_dirs


# Frontend framework labels — used for frontend vs backend classification
_FRONTEND_FRAMEWORKS = frozenset({
    "React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js",
    "Gatsby", "Astro", "Remix",
})
_FRONTEND_BUILD_TOOLS = frozenset({"Vite", "Webpack", "Tailwind CSS"})


def _build_arch_components(evidence: dict[str, Any]) -> list[dict]:
    """
    Produce a list of high-level architecture components with rich evidence.

    Each component dict has:
      name, description, evidence_files, technology, directories, confidence, evidence

    Components are only emitted when real evidence supports them.
    Do NOT emit a component merely because a technology name is detected —
    require corroborating directory/file structure.
    """
    components: list[dict] = []
    fws: list[str] = evidence.get("frameworks", [])
    langs: list[str] = evidence.get("primary_languages", [])
    dbs: list[str] = evidence.get("databases", [])
    runtimes: list[str] = evidence.get("runtimes", [])

    # ── Frontend ────────────────────────────────────────────────────────────
    # Require: frontend framework + frontend component directories OR
    #          frontend-extension source files detected
    fe_frameworks = [f for f in fws if f in _FRONTEND_FRAMEWORKS]
    fe_dirs = evidence.get("frontend_components", [])  # dirs like "frontend", "src"
    fe_important = [
        f for f in evidence.get("important_files", [])
        if f.get("category") == "frontend"
        or (f.get("category") == "entry_point"
            and any(f.get("file_path", "").endswith(ext) for ext in (".tsx", ".jsx", ".vue", ".svelte")))
    ]
    fe_config = [
        f for f in evidence.get("config_files", [])
        if any(name in f.lower() for name in ("vite.config", "next.config", "angular.json",
                                               "vue.config", "svelte.config"))
    ]

    # Require corroborating directory or source file evidence — not just a framework name
    fe_has_structure = bool(fe_dirs) or bool(fe_important) or bool(fe_config)
    if fe_frameworks and fe_has_structure:
        fe_evidence_files = list(dict.fromkeys(
            [f["file_path"] for f in fe_important[:3]]
            + fe_dirs[:3]
            + fe_config[:2]
        ))[:5]
        fe_evidence_bullets = [f"Frontend framework detected: {fw}" for fw in fe_frameworks[:3]]
        if fe_dirs:
            fe_evidence_bullets.append(f"Frontend source directories: {', '.join(fe_dirs[:3])}")
        if fe_config:
            fe_evidence_bullets.append(f"Build configuration found: {', '.join(fe_config[:2])}")
        # Determine technology label
        fe_tech_parts = fe_frameworks[:2]
        build_tools = [f for f in fws if f in _FRONTEND_BUILD_TOOLS]
        if build_tools:
            fe_tech_parts += build_tools[:1]
        fe_tech = " + ".join(fe_tech_parts) if fe_tech_parts else None

        # Confidence: high if framework + dirs + config; medium if framework + dirs only
        if fe_frameworks and fe_dirs and fe_config:
            fe_confidence = "high"
        elif fe_frameworks and (fe_dirs or fe_important):
            fe_confidence = "medium"
        else:
            fe_confidence = "low"

        components.append({
            "name": "frontend",
            "description": (
                f"Client-side application layer built with "
                f"{', '.join(fe_frameworks[:2])}."
            ),
            "evidence_files": fe_evidence_files,
            "technology": fe_tech,
            "directories": fe_dirs[:5],
            "confidence": fe_confidence,
            "evidence": fe_evidence_bullets,
        })

    # ── Backend / API ────────────────────────────────────────────────────────
    # Require: API route files OR backend component dirs OR backend entry point
    be_dirs = evidence.get("backend_components", [])
    api_files = [f["file_path"] for f in evidence.get("important_files", [])
                 if f.get("category") in ("API", "core service")]
    be_route_files = [r["file_path"] if isinstance(r, dict) else r
                      for r in evidence.get("api_route_files", [])][:5]
    be_entry_points = [ep["file_path"] for ep in evidence.get("entry_points", [])
                       if any(k in ep.get("kind", "").lower()
                              for k in ("python", "server", "go", "rust", "java"))]
    be_has_structure = bool(be_dirs) or bool(api_files) or bool(be_route_files) or bool(be_entry_points)
    if be_has_structure:
        be_fws = [f for f in fws if f not in _FRONTEND_FRAMEWORKS and f not in _FRONTEND_BUILD_TOOLS]
        be_evidence_files = list(dict.fromkeys(
            api_files[:3] + be_route_files[:3] + be_entry_points[:2]
        ))[:5]
        be_evidence_bullets: list[str] = []
        if be_fws:
            be_evidence_bullets.append(f"Backend framework(s): {', '.join(be_fws[:3])}")
        if be_dirs:
            be_evidence_bullets.append(f"Backend source directories: {', '.join(be_dirs[:3])}")
        if be_route_files:
            be_evidence_bullets.append(f"API route files detected: {be_route_files[0]}")
        if be_entry_points:
            be_evidence_bullets.append(f"Server entry point: {be_entry_points[0]}")
        # Technology label
        be_tech_parts = be_fws[:2] if be_fws else (langs[:2] if langs else [])
        be_tech = " + ".join(be_tech_parts) if be_tech_parts else None

        if be_fws and be_dirs and (be_route_files or be_entry_points):
            be_confidence: str = "high"
        elif be_dirs and (be_route_files or be_entry_points):
            be_confidence = "medium"
        elif be_has_structure:
            be_confidence = "medium"
        else:
            be_confidence = "low"

        components.append({
            "name": "backend/API",
            "description": (
                f"Server-side API layer. "
                f"Languages: {', '.join(langs[:3]) or 'unknown'}. "
                f"Frameworks: {', '.join(be_fws[:3]) or 'none detected'}."
            ),
            "evidence_files": be_evidence_files,
            "technology": be_tech,
            "directories": be_dirs[:5],
            "confidence": be_confidence,
            "evidence": be_evidence_bullets,
        })

    # ── Database / Data Layer ────────────────────────────────────────────────
    # Require: database signal + corroborating file evidence
    db_important = [f["file_path"] for f in evidence.get("important_files", [])
                    if f.get("category") == "database"]
    db_signals_from_files = bool(db_important)  # files categorised as database
    db_signals_from_names = bool(dbs)            # database tech names detected

    if db_signals_from_names or db_signals_from_files:
        db_evidence_files = list(dict.fromkeys(db_important[:5]))
        db_evidence_bullets: list[str] = []
        if dbs:
            db_evidence_bullets.append(f"Database technology detected: {', '.join(dbs[:4])}")
        if db_important:
            db_evidence_bullets.append(f"Database-related files: {db_important[0]}")

        db_tech = ", ".join(dbs[:3]) if dbs else None
        if dbs and db_important:
            db_confidence: str = "high"
        elif dbs or db_important:
            db_confidence = "medium"
        else:
            db_confidence = "low"

        components.append({
            "name": "database/data layer",
            "description": (
                f"Persistence layer. "
                f"Detected: {', '.join(dbs) or 'unknown'}."
            ),
            "evidence_files": db_evidence_files,
            "technology": db_tech,
            "directories": [],
            "confidence": db_confidence,
            "evidence": db_evidence_bullets,
        })

    # ── Authentication ───────────────────────────────────────────────────────
    auth_signals = evidence.get("auth_signals", [])
    auth_important = [f["file_path"] for f in evidence.get("important_files", [])
                      if f.get("category") == "authentication"]
    auth_paths = list(dict.fromkeys(
        [a["file_path"] for a in auth_signals[:5]] + auth_important[:3]
    ))[:5]
    if auth_paths:
        auth_evidence_bullets = [
            f"Authentication file: {p}" for p in auth_paths[:3]
        ]
        components.append({
            "name": "authentication",
            "description": "Authentication / authorisation layer detected in repository.",
            "evidence_files": auth_paths,
            "technology": None,
            "directories": [],
            "confidence": "medium",
            "evidence": auth_evidence_bullets,
        })

    # ── Core Services ────────────────────────────────────────────────────────
    svc_files = [f["file_path"] for f in evidence.get("important_files", [])
                 if f.get("category") == "core service"][:5]
    if svc_files:
        components.append({
            "name": "services",
            "description": "Core business logic / service layer.",
            "evidence_files": svc_files,
            "technology": None,
            "directories": [],
            "confidence": "medium",
            "evidence": [f"Service file detected: {svc_files[0]}"],
        })

    # ── Tests ────────────────────────────────────────────────────────────────
    test_evidence_files = evidence.get("test_files", [])[:5]
    test_dirs = evidence.get("test_directories", [])[:3]
    if test_evidence_files or test_dirs:
        test_bullets: list[str] = []
        if test_dirs:
            test_bullets.append(f"Test directories: {', '.join(test_dirs)}")
        if test_evidence_files:
            test_bullets.append(f"Test files detected: {test_evidence_files[0]}")
        components.append({
            "name": "tests",
            "description": (
                f"Test suite. "
                f"Test directories: {', '.join(test_dirs) if test_dirs else 'see evidence files'}."
            ),
            "evidence_files": list(dict.fromkeys(test_evidence_files + test_dirs))[:5],
            "technology": None,
            "directories": test_dirs,
            "confidence": "high" if test_dirs else "medium",
            "evidence": test_bullets,
        })

    # ── Deployment / Infrastructure ──────────────────────────────────────────
    deploy_files = evidence.get("deployment_files", [])[:5]
    if deploy_files:
        deploy_bullets = [f"Deployment file: {deploy_files[0]}"]
        if len(deploy_files) > 1:
            deploy_bullets.append(f"Additional deployment config: {deploy_files[1]}")
        components.append({
            "name": "deployment/infrastructure",
            "description": "Containerisation, CI/CD, or cloud deployment configuration.",
            "evidence_files": deploy_files,
            "technology": None,
            "directories": [],
            "confidence": "high",
            "evidence": deploy_bullets,
        })

    return components


# ---------------------------------------------------------------------------
# Architecture relationship inference
# ---------------------------------------------------------------------------

def _build_arch_relationships(
    components: list[dict],
    evidence: dict[str, Any],
) -> list[dict]:
    """
    Infer evidence-backed relationships between architecture components.

    Relationships are only added when we have STRONG evidence:
    - directory structure separation (frontend/ vs backend/)
    - API route files (implies frontend calls backend)
    - database files (implies backend writes to database)
    - auth files (implies auth used by backend, and possibly frontend)

    Never fabricates relationships.
    """
    component_names = {c["name"] for c in components}
    relationships: list[dict] = []

    has_frontend = "frontend" in component_names
    has_backend = "backend/API" in component_names
    has_db = "database/data layer" in component_names
    has_auth = "authentication" in component_names
    has_services = "services" in component_names

    # ── Frontend → Backend/API ───────────────────────────────────────────────
    # Evidence: both frontend + backend dirs exist AND api route files detected
    if has_frontend and has_backend:
        api_routes = evidence.get("api_route_files", [])
        fe_dirs = evidence.get("frontend_components", [])
        be_dirs = evidence.get("backend_components", [])
        rel_evidence: list[str] = []
        if fe_dirs and be_dirs:
            rel_evidence.append(
                f"Separate frontend ({fe_dirs[0]}) and backend ({be_dirs[0]}) directories detected"
            )
        if api_routes:
            route_path = api_routes[0]["file_path"] if isinstance(api_routes[0], dict) else api_routes[0]
            rel_evidence.append(f"API route files detected (e.g. {route_path})")
        # Only emit if we have actual directory separation evidence
        if rel_evidence:
            confidence = "high" if (fe_dirs and be_dirs and api_routes) else "medium"
            relationships.append({
                "source": "frontend",
                "target": "backend/API",
                "relationship_type": "calls",
                "evidence": rel_evidence,
                "confidence": confidence,
            })

    # ── Backend/API → Database ───────────────────────────────────────────────
    # Evidence: database signals detected AND backend has API/service files
    if has_backend and has_db:
        dbs = evidence.get("databases", [])
        db_files = [f["file_path"] for f in evidence.get("important_files", [])
                    if f.get("category") == "database"]
        rel_evidence = []
        if dbs:
            rel_evidence.append(f"Database technology detected: {', '.join(dbs[:2])}")
        if db_files:
            rel_evidence.append(f"Database/schema files: {db_files[0]}")
        if rel_evidence:
            confidence = "high" if (dbs and db_files) else "medium"
            relationships.append({
                "source": "backend/API",
                "target": "database/data layer",
                "relationship_type": "reads_from/writes_to",
                "evidence": rel_evidence,
                "confidence": confidence,
            })

    # ── Backend/API → Services ───────────────────────────────────────────────
    # Evidence: service files in backend directory
    if has_backend and has_services:
        svc_files = [f["file_path"] for f in evidence.get("important_files", [])
                     if f.get("category") == "core service"]
        be_dirs = evidence.get("backend_components", [])
        # Only add if services files are in the same root as backend dirs
        svc_in_backend = any(
            any(be_dir in svc for be_dir in be_dirs)
            for svc in svc_files
        )
        if svc_files and (svc_in_backend or be_dirs):
            relationships.append({
                "source": "backend/API",
                "target": "services",
                "relationship_type": "delegates_to",
                "evidence": [f"Service layer files in backend directory: {svc_files[0]}"],
                "confidence": "medium",
            })

    # ── Services → Database ──────────────────────────────────────────────────
    if has_services and has_db and not has_backend:
        # Only when there's no backend component already connecting to DB
        dbs = evidence.get("databases", [])
        if dbs:
            relationships.append({
                "source": "services",
                "target": "database/data layer",
                "relationship_type": "reads_from/writes_to",
                "evidence": [f"Database technology detected: {', '.join(dbs[:2])}"],
                "confidence": "medium",
            })

    # ── Backend/API → Authentication (or Frontend → Authentication) ──────────
    if has_auth and (has_backend or has_frontend):
        auth_files = [f["file_path"] for f in evidence.get("important_files", [])
                      if f.get("category") == "authentication"]
        be_dirs = evidence.get("backend_components", [])
        fe_dirs = evidence.get("frontend_components", [])
        # Determine which component auth lives in
        auth_in_backend = any(
            any(be_dir in af for be_dir in be_dirs)
            for af in auth_files
        ) if (auth_files and be_dirs) else False
        auth_in_frontend = any(
            any(fe_dir in af for fe_dir in fe_dirs)
            for af in auth_files
        ) if (auth_files and fe_dirs) else False

        if has_backend and (auth_in_backend or not auth_in_frontend):
            relationships.append({
                "source": "backend/API",
                "target": "authentication",
                "relationship_type": "uses",
                "evidence": [f"Auth file within backend structure: {auth_files[0]}"] if auth_files else
                            ["Auth signals detected in backend area"],
                "confidence": "medium",
            })
        elif has_frontend and auth_in_frontend:
            relationships.append({
                "source": "frontend",
                "target": "authentication",
                "relationship_type": "uses",
                "evidence": [f"Auth file within frontend structure: {auth_files[0]}"] if auth_files else
                            ["Auth signals detected in frontend area"],
                "confidence": "medium",
            })

    return relationships


# ---------------------------------------------------------------------------
# Architecture summary and reading order
# ---------------------------------------------------------------------------

def _build_architecture_summary(
    components: list[dict],
    evidence: dict[str, Any],
) -> str:
    """Generate a concise plain-text architecture summary from evidence."""
    component_names = {c["name"] for c in components}
    langs = evidence.get("primary_languages", [])
    fws = evidence.get("frameworks", [])
    dbs = evidence.get("databases", [])

    parts: list[str] = []

    if not components:
        return "Insufficient evidence to determine architecture."

    # Count components for opening line
    comp_count = len(components)
    tech_count = len(set(langs + fws + dbs))
    parts.append(
        f"This repository has {comp_count} detected architecture component"
        f"{'s' if comp_count != 1 else ''} "
        f"and {tech_count} detected technology/framework signal"
        f"{'s' if tech_count != 1 else ''}."
    )

    for comp in components:
        name = comp["name"]
        tech = comp.get("technology")
        if tech:
            parts.append(f"{name.title()}: {tech}.")
        elif name in component_names:
            # Pull technology from evidence names
            if name == "database/data layer" and dbs:
                parts.append(f"Database: {', '.join(dbs[:3])}.")
            elif name == "tests":
                test_dirs = evidence.get("test_directories", [])
                if test_dirs:
                    parts.append(f"Testing: test directories at {', '.join(test_dirs[:2])}.")
            elif name == "deployment/infrastructure":
                deploy = evidence.get("deployment_files", [])
                if deploy:
                    parts.append(f"Deployment: {', '.join(deploy[:2])}.")

    return " ".join(parts)


def _build_reading_order(
    components: list[dict],
    evidence: dict[str, Any],
) -> list[str]:
    """
    Generate a deterministic, repository-specific onboarding reading order.
    Uses detected components and entry points to produce tailored guidance.
    """
    component_names = {c["name"] for c in components}
    entry_points = evidence.get("entry_points", [])
    steps: list[str] = []

    has_frontend = "frontend" in component_names
    has_backend = "backend/API" in component_names
    has_db = "database/data layer" in component_names
    has_tests = "tests" in component_names
    has_services = "services" in component_names
    has_deploy = "deployment/infrastructure" in component_names

    # Find specific entry point paths
    frontend_ep = next(
        (ep for ep in entry_points
         if any(ep.get("file_path", "").endswith(ext) for ext in (".tsx", ".jsx", ".ts", ".js"))
         and any(k in ep.get("kind", "").lower() for k in ("react", "typescript", "javascript", "frontend"))),
        None
    )
    backend_ep = next(
        (ep for ep in entry_points
         if any(k in ep.get("kind", "").lower() for k in ("python", "server", "go", "rust", "java"))),
        None
    )

    if has_frontend and has_backend:
        # Full-stack reading order
        if frontend_ep:
            steps.append(
                f"Start with the frontend entry point: {frontend_ep['file_path']} "
                f"({frontend_ep['kind']})"
            )
        else:
            steps.append("Start with the frontend source directory to understand the UI layer.")

        if backend_ep:
            steps.append(
                f"Read the backend entry point: {backend_ep['file_path']} "
                f"({backend_ep['kind']})"
            )
        else:
            steps.append("Read the backend entry point to understand the server layer.")

        steps.append("Follow API route definitions to understand the frontend/backend boundary.")

        if has_services:
            steps.append("Trace API routes into service files to understand business logic.")
        if has_db:
            steps.append("Follow service calls into database/persistence code.")
        if has_tests:
            test_dirs = evidence.get("test_directories", [])
            if test_dirs:
                steps.append(
                    f"Read tests alongside the implementation "
                    f"(test directories: {', '.join(test_dirs[:2])})."
                )
            else:
                steps.append("Read tests alongside the implementation.")
        if has_deploy:
            steps.append("Review deployment configuration to understand how the system runs in production.")

    elif has_backend and not has_frontend:
        # Backend-only
        if backend_ep:
            steps.append(
                f"Start with the application entry point: {backend_ep['file_path']} "
                f"({backend_ep['kind']})"
            )
        else:
            steps.append("Start with the application entry point.")
        steps.append("Follow API routes to understand exposed endpoints.")
        if has_services:
            steps.append("Trace route handlers into service/business logic files.")
        if has_db:
            steps.append("Read database/persistence code to understand data models.")
        if has_tests:
            steps.append("Review tests to understand expected behaviour.")

    elif has_frontend and not has_backend:
        # Frontend-only
        if frontend_ep:
            steps.append(
                f"Start with the frontend entry point: {frontend_ep['file_path']} "
                f"({frontend_ep['kind']})"
            )
        else:
            steps.append("Start with the frontend entry point.")
        steps.append("Follow component imports to understand the component hierarchy.")
        if has_tests:
            steps.append("Review component tests to understand expected behaviour.")

    else:
        # Generic single-component
        if entry_points:
            ep = entry_points[0]
            steps.append(
                f"Start with the entry point: {ep['file_path']} ({ep['kind']})"
            )
        else:
            steps.append("Identify the application entry point from the directory structure.")
        steps.append("Follow imports and module references to understand the code organisation.")
        if has_tests:
            steps.append("Read tests alongside the implementation.")

    return steps


def _build_architecture_data(
    evidence: dict[str, Any],
    evidence_quality: str,
) -> ArchitectureData:
    """
    Assemble the complete ArchitectureData from repository evidence.
    This is the main entry point for the architecture explorer backend.
    """
    component_dicts = _build_arch_components(evidence)
    relationship_dicts = _build_arch_relationships(component_dicts, evidence)
    summary = _build_architecture_summary(component_dicts, evidence)
    reading_order = _build_reading_order(component_dicts, evidence)

    # Overall architecture confidence
    total_files = evidence.get("total_files", 0)
    entry_points = evidence.get("entry_points", [])
    frameworks = evidence.get("frameworks", [])
    runtimes = evidence.get("runtimes", [])
    if (
        len(component_dicts) >= 2
        and entry_points
        and (frameworks or runtimes)
        and total_files >= 5
    ):
        arch_confidence: str = "high"
    elif component_dicts and (entry_points or frameworks):
        arch_confidence = "medium"
    elif component_dicts:
        arch_confidence = "low"
    else:
        arch_confidence = "low"

    _VALID_QUALITY = {"sufficient", "partial", "insufficient"}
    safe_quality = evidence_quality if evidence_quality in _VALID_QUALITY else "partial"

    components = [
        ArchitectureComponent(
            name=c["name"],
            description=c["description"],
            evidence_files=c.get("evidence_files", []),
            technology=c.get("technology"),
            directories=c.get("directories", []),
            confidence=c.get("confidence", "medium"),  # type: ignore[arg-type]
            evidence=c.get("evidence", []),
        )
        for c in component_dicts
    ]

    relationships = [
        ArchitectureRelationship(
            source=r["source"],
            target=r["target"],
            relationship_type=r["relationship_type"],
            evidence=r.get("evidence", []),
            confidence=r.get("confidence", "medium"),  # type: ignore[arg-type]
        )
        for r in relationship_dicts
    ]

    return ArchitectureData(
        components=components,
        relationships=relationships,
        summary=summary,
        reading_order=reading_order,
        confidence=arch_confidence,  # type: ignore[arg-type]
        evidence_quality=safe_quality,  # type: ignore[arg-type]
    )


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
    elif (
        evidence.get("primary_languages")
        and evidence.get("entry_points")
        and (evidence.get("frameworks") or evidence.get("runtimes"))
    ):
        # We have language + entry points + framework/runtime → sufficient
        quality = "sufficient"
    else:
        raw_quality = ai_output.get("evidence_quality", "partial") if not null_provider else "partial"
        quality = raw_quality if raw_quality in _VALID_QUALITY else "partial"

    # Build architecture components from evidence
    arch_component_dicts = _build_arch_components(evidence)
    arch_component_objs = [
        ArchitectureComponent(
            name=c["name"],
            description=c["description"],
            evidence_files=c.get("evidence_files", []),
            technology=c.get("technology"),
            directories=c.get("directories", []),
            confidence=c.get("confidence", "medium"),  # type: ignore[arg-type]
            evidence=c.get("evidence", []),
        )
        for c in arch_component_dicts
    ]

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
        source_directories=evidence.get("source_directories", []),
        test_directories=evidence.get("test_directories", []),
        doc_directories=evidence.get("doc_directories", []),
        arch_components=arch_component_objs,
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
    # Also add manifest files without content as dependency manifests (no fabrication)
    dependencies = _add_manifest_file_references(
        dependencies, evidence.get("important_files", [])
    )

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

    src_dirs = evidence.get("source_directories", [])
    if src_dirs:
        parts.append(f"Source directories: {', '.join(src_dirs[:5])}.")

    test_dirs = evidence.get("test_directories", [])
    if test_dirs:
        parts.append(f"Test directories: {', '.join(test_dirs[:5])}.")

    doc_dirs = evidence.get("doc_directories", [])
    if doc_dirs:
        parts.append(f"Documentation directories: {', '.join(doc_dirs[:3])}.")

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

        elif name == "go.mod":
            # Extract module requires: "require pkg vX.Y.Z" or block-form "pkg vX.Y.Z"
            for line in content.splitlines():
                line = line.strip()
                # Single-line: require github.com/foo/bar v1.2.3
                m = re.match(r"^require\s+(\S+)\s+(v\S+)", line)
                if m:
                    deps.append(Dependency(
                        name=m.group(1), version=m.group(2),
                        kind="runtime", source_file=file_path,
                    ))
                    continue
                # Block body line: github.com/foo/bar v1.2.3
                m2 = re.match(r"^(\S+)\s+(v\S+)", line)
                if m2 and not m2.group(1).startswith("//"):
                    deps.append(Dependency(
                        name=m2.group(1), version=m2.group(2),
                        kind="runtime", source_file=file_path,
                    ))

        elif name == "cargo.toml":
            # Parse [dependencies] section: name = "version" or name = { version = "..." }
            in_deps_section = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[dependencies]"):
                    in_deps_section = True
                    continue
                if stripped.startswith("[dev-dependencies]"):
                    in_deps_section = True
                    continue
                if stripped.startswith("[") and "dependencies" not in stripped:
                    in_deps_section = False
                    continue
                if in_deps_section and "=" in stripped and not stripped.startswith("#"):
                    # name = "version"  or  name = { version = "X" }
                    m = re.match(r'^([A-Za-z0-9_\-]+)\s*=\s*"([^"]+)"', stripped)
                    if m:
                        deps.append(Dependency(
                            name=m.group(1), version=m.group(2),
                            kind="runtime", source_file=file_path,
                        ))

    return deps[:100]  # cap


def _add_manifest_file_references(
    existing_deps: list[Dependency],
    important_files: list[dict],
) -> list[Dependency]:
    """
    For manifest files that are in important_files but whose content was not
    available (so _parse_dependencies produced nothing for them), add a single
    sentinel Dependency entry so the manifest is still reported.

    This avoids fabricating dependency names while still surfacing the manifest.
    """
    _KNOWN_MANIFESTS = {
        "package.json", "requirements.txt", "pyproject.toml",
        "go.mod", "cargo.toml", "pom.xml", "build.gradle",
        "build.gradle.kts", "gemfile", "composer.json",
    }
    # Which source files already have at least one dep?
    covered_sources = {d.source_file for d in existing_deps}

    result = list(existing_deps)
    for f in important_files:
        fp = f.get("file_path", "")
        fname = fp.rsplit("/", 1)[-1].lower()
        if fname in _KNOWN_MANIFESTS and fp not in covered_sources:
            result.append(Dependency(
                name=f"(manifest: {fname})",
                kind="unknown",
                source_file=fp,
            ))
    return result[:100]


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


def get_architecture_data(repository_id: str) -> Optional[ArchitectureData]:
    """
    Re-derive ArchitectureData from stored analysis technologies data.
    Returns None if no analysis exists yet for this repository.

    This re-derives the architecture from stored evidence rather than
    running a fresh analysis, so it is fast and deterministic.
    """
    row = get_analysis(repository_id)
    if not row:
        return None

    technologies = row.get("technologies") or {}
    if not technologies:
        return None

    # Reconstruct evidence dict from stored technologies
    evidence: dict[str, Any] = {
        "primary_languages": technologies.get("languages", []),
        "frameworks": technologies.get("frameworks", []),
        "runtimes": technologies.get("runtimes", []),
        "package_managers": technologies.get("package_managers", []),
        "databases": technologies.get("databases", []),
        "auth_signals": technologies.get("auth_signals", []),
        "test_files": technologies.get("test_files", []),
        "config_files": technologies.get("config_files", []),
        "deployment_files": technologies.get("deployment_files", []),
        "dev_commands": technologies.get("dev_commands", []),
        "api_route_files": [
            {"file_path": r["file_path"], "evidence": r.get("evidence", "")}
            if isinstance(r, dict) else {"file_path": r, "evidence": ""}
            for r in technologies.get("api_routes", [])
        ],
        "backend_components": technologies.get("backend_components", []),
        "frontend_components": technologies.get("frontend_components", []),
        "important_directories": technologies.get("important_directories", []),
        "source_directories": technologies.get("source_directories", []),
        "test_directories": technologies.get("test_directories", []),
        "doc_directories": technologies.get("doc_directories", []),
        # Reconstruct important_files from stored arch_components evidence
        "important_files": _reconstruct_important_files_from_arch_components(
            technologies.get("arch_components", [])
        ),
        "entry_points": row.get("entry_points") or [],
        "total_files": 1,   # non-zero so confidence calc works
        "total_dirs": 0,
        "injection_warnings": [],
        "manifest_snippets": {},
    }

    # Determine evidence quality from the stored analysis
    evidence_quality = _infer_evidence_quality(evidence)

    return _build_architecture_data(evidence, evidence_quality)


def _reconstruct_important_files_from_arch_components(
    arch_components: list[dict],
) -> list[dict]:
    """
    Reconstruct a minimal important_files list from stored arch_components
    so that _build_arch_components can find files by category.
    """
    result: list[dict] = []
    _CATEGORY_MAP = {
        "frontend": "frontend",
        "backend/api": "API",
        "database/data layer": "database",
        "authentication": "authentication",
        "services": "core service",
    }
    for comp in arch_components:
        if not isinstance(comp, dict):
            continue
        comp_name_lower = comp.get("name", "").lower()
        category = _CATEGORY_MAP.get(comp_name_lower, "")
        if not category:
            continue
        for fp in comp.get("evidence_files", [])[:5]:
            if isinstance(fp, str):
                result.append({
                    "file_path": fp,
                    "reason": f"Stored evidence for {comp.get('name')}",
                    "confidence": comp.get("confidence", "medium"),
                    "category": category,
                })
    return result


def _infer_evidence_quality(evidence: dict[str, Any]) -> str:
    """Determine evidence quality from reconstructed evidence dict."""
    has_langs = bool(evidence.get("primary_languages"))
    has_frameworks = bool(evidence.get("frameworks") or evidence.get("runtimes"))
    has_entry_points = bool(evidence.get("entry_points"))
    has_components = bool(evidence.get("backend_components") or evidence.get("frontend_components"))

    if has_langs and has_frameworks and has_entry_points:
        return "sufficient"
    if has_langs or has_components or has_frameworks:
        return "partial"
    return "insufficient"
