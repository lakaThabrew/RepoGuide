"""
setup_service.py — Evidence-grounded Repository Setup Assistant.

Flow:
  1. Fetch repository record from Supabase
  2. Fetch stored analysis from Supabase
  3. Validate evidence quality
  4. Run deterministic section builders against analysis evidence
  5. Compute overall confidence and warnings
  6. Persist the guide back to analyses.setup_guide (JSON)
  7. Return a SetupGuide

DESIGN PRINCIPLES:
  - Every command or note references actual evidence files from the analysis.
  - No commands are invented for repositories without manifest evidence.
  - Version numbers are never fabricated; if absent, state so explicitly.
  - Secrets, .env contents, and private keys are never read or surfaced.
  - Repository metadata is treated as untrusted DATA throughout.
  - Prompt-injection patterns in repository text cannot alter guide structure.

SECURITY:
  - FORBIDDEN_SETUP_FILES are never referenced in output.
  - All repository-derived text is sanitised before display.
  - No repository commands are executed.
  - No package installation is performed.
  - No migrations are executed.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.database.supabase import get_supabase
from app.schemas.setup import (
    SetupCommand,
    SetupConfidence,
    SetupGuide,
    SetupGuideResponse,
    SetupPrerequisite,
    SetupSection,
    SetupWarning,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

# Files that must NEVER be referenced in setup output under any circumstances
_FORBIDDEN_SETUP_FILES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".env.test", ".secret", "secrets.yml",
    "secrets.yaml", "id_rsa", "id_ed25519", ".npmrc", ".pypirc",
})

_FORBIDDEN_FILE_RE = re.compile(
    r"(^|[/\\])(\.env(\.(local|production|staging|development|test))?|\.secret|secrets\.(yml|yaml)"
    r"|id_rsa|id_ed25519|\.npmrc|\.pypirc)$",
    re.IGNORECASE,
)

# Prompt-injection detection
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


def _is_forbidden(path: str) -> bool:
    """Return True if this file path must never appear in setup output."""
    name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    return name in _FORBIDDEN_SETUP_FILES or bool(_FORBIDDEN_FILE_RE.search(path))


def _safe_text(text: str) -> str:
    """
    Sanitise a string derived from repository metadata before output.

    Replaces prompt-injection patterns with [REDACTED] so repository content
    cannot alter the guide text structure.
    The setup section structure (confidence, commands list) is always
    computed programmatically — never derived from raw repository text.
    """
    if _INJECTION_RE.search(text):
        return _INJECTION_RE.sub("[REDACTED]", text)
    return text


def _filter_paths(paths: list[str]) -> list[str]:
    """Remove forbidden file paths."""
    return [p for p in paths if not _is_forbidden(p)]


# ---------------------------------------------------------------------------
# Evidence accessors — operate on the stored analysis dict
# ---------------------------------------------------------------------------

def _tech(analysis: dict) -> dict:
    return analysis.get("technologies") or {}


def _languages(analysis: dict) -> list[str]:
    return _tech(analysis).get("languages") or []


def _frameworks(analysis: dict) -> list[str]:
    return _tech(analysis).get("frameworks") or []


def _runtimes(analysis: dict) -> list[str]:
    return _tech(analysis).get("runtimes") or []


def _package_managers(analysis: dict) -> list[str]:
    return _tech(analysis).get("package_managers") or []


def _databases(analysis: dict) -> list[str]:
    return _tech(analysis).get("databases") or []


def _dev_commands(analysis: dict) -> list[str]:
    return _tech(analysis).get("dev_commands") or []


def _config_files(analysis: dict) -> list[str]:
    return _filter_paths(_tech(analysis).get("config_files") or [])


def _deployment_files(analysis: dict) -> list[str]:
    return _filter_paths(_tech(analysis).get("deployment_files") or [])


def _entry_points(analysis: dict) -> list[dict]:
    return analysis.get("entry_points") or []


def _important_files(analysis: dict) -> list[dict]:
    return [
        f for f in (analysis.get("important_files") or [])
        if isinstance(f, dict) and not _is_forbidden(f.get("file_path", ""))
    ]


def _dependencies(analysis: dict) -> list[dict]:
    return analysis.get("dependencies") or []


def _arch_components(analysis: dict) -> list[dict]:
    return _tech(analysis).get("arch_components") or []


def _dep_manifest_files(analysis: dict) -> list[str]:
    """Return names of detected dependency manifest files."""
    result: list[str] = []
    seen: set[str] = set()
    for dep in _dependencies(analysis):
        if not isinstance(dep, dict):
            continue
        sf = dep.get("source_file", "")
        if sf and sf not in seen and not _is_forbidden(sf):
            result.append(sf)
            seen.add(sf)
    return result


def _has_manifest(analysis: dict, *names: str) -> Optional[str]:
    """Return the file path of the first matching manifest if it exists."""
    for f in _important_files(analysis):
        fp = f.get("file_path", "")
        fname = fp.rsplit("/", 1)[-1].lower()
        if fname in {n.lower() for n in names}:
            return fp
    # Also check dependency source files
    for sf in _dep_manifest_files(analysis):
        fname = sf.rsplit("/", 1)[-1].lower()
        if fname in {n.lower() for n in names}:
            return sf
    return None


def _env_config_files(analysis: dict) -> list[str]:
    """Return config files that relate to environment config (safe only)."""
    safe = []
    for cf in _config_files(analysis):
        name = cf.rsplit("/", 1)[-1].lower()
        # .env.example is safe; actual .env files are forbidden
        if name == ".env.example" or name.endswith(".example"):
            safe.append(cf)
        # Exclude actual env files
        elif not name.startswith(".env") and not _is_forbidden(cf):
            if any(kw in name for kw in ("config", ".yml", ".yaml", ".toml", ".ini", ".cfg")):
                safe.append(cf)
    return safe


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_prerequisites(analysis: dict) -> list[SetupPrerequisite]:
    """
    Build the list of prerequisites from language/runtime/framework evidence.

    Only emits a prerequisite when evidence supports it.
    Never fabricates version numbers.
    """
    prereqs: list[SetupPrerequisite] = []
    seen_names: set[str] = set()

    def _add(name: str, version_note: str, evidence: list[str]) -> None:
        if name not in seen_names:
            prereqs.append(SetupPrerequisite(
                name=name,
                version_note=version_note,
                evidence=evidence,
            ))
            seen_names.add(name)

    langs = _languages(analysis)
    runtimes = _runtimes(analysis)
    frameworks = _frameworks(analysis)
    package_managers = _package_managers(analysis)

    # --- Python ---
    if "Python" in langs or "Python" in runtimes:
        ev: list[str] = []
        # Check for .python-version or pyproject.toml for version hint
        python_version_file = _has_manifest(analysis, ".python-version")
        pyproject = _has_manifest(analysis, "pyproject.toml")
        if python_version_file:
            ev.append(python_version_file)
            note = f"Version file detected at {python_version_file} — check it for the required version."
        elif pyproject:
            ev.append(pyproject)
            note = "Version not specified in indexed repository metadata."
        else:
            req = _has_manifest(analysis, "requirements.txt")
            if req:
                ev.append(req)
            note = "Version not specified in indexed repository metadata."
        _add("Python", note, ev)

    # --- Node.js ---
    node_evidence = (
        "Node.js" in runtimes
        or "TypeScript" in runtimes
        or bool(_has_manifest(analysis, "package.json"))
        or any(pm in package_managers for pm in ("npm", "Yarn", "pnpm"))
    )
    if node_evidence:
        ev = []
        nvmrc = _has_manifest(analysis, ".nvmrc", ".node-version")
        pkg = _has_manifest(analysis, "package.json")
        if nvmrc:
            ev.append(nvmrc)
            note = f"Version file detected at {nvmrc} — check it for the required version."
        else:
            if pkg:
                ev.append(pkg)
            note = "Version not specified in indexed repository metadata."
        _add("Node.js", note, ev)

    # --- Go ---
    if "Go" in langs or "Go" in runtimes:
        ev = []
        go_mod = _has_manifest(analysis, "go.mod")
        if go_mod:
            ev.append(go_mod)
        note = "Version not specified in indexed repository metadata."
        _add("Go", note, ev)

    # --- Rust ---
    if "Rust" in langs or "Rust" in runtimes:
        ev = []
        cargo = _has_manifest(analysis, "Cargo.toml")
        if cargo:
            ev.append(cargo)
        note = "Version not specified in indexed repository metadata."
        _add("Rust", note, ev)

    # --- Java ---
    if "Java" in langs or "Java" in runtimes or "Java/Maven" in runtimes or "Java/Gradle" in runtimes:
        ev = []
        pom = _has_manifest(analysis, "pom.xml")
        gradle = _has_manifest(analysis, "build.gradle", "build.gradle.kts")
        if pom:
            ev.append(pom)
        elif gradle:
            ev.append(gradle)
        note = "Version not specified in indexed repository metadata."
        _add("Java", note, ev)

    # --- Docker (when Dockerfile or docker-compose present) ---
    docker_files = [f for f in _deployment_files(analysis)
                    if "dockerfile" in f.lower() or "docker-compose" in f.lower()]
    if docker_files:
        _add(
            "Docker",
            "Version not specified in indexed repository metadata.",
            docker_files[:2],
        )

    # --- Package managers ---
    for pm in package_managers:
        if pm in ("npm", "Yarn", "pnpm"):
            # Already covered by Node.js
            continue
        if pm == "Pipenv":
            _add("Pipenv", "Version not specified in indexed repository metadata.",
                 [_has_manifest(analysis, "Pipfile") or "Pipfile"])
        elif pm == "Poetry":
            _add("Poetry", "Version not specified in indexed repository metadata.",
                 [_has_manifest(analysis, "pyproject.toml") or "pyproject.toml"])
        elif pm == "uv":
            _add("uv", "Version not specified in indexed repository metadata.",
                 [_has_manifest(analysis, "pyproject.toml") or "pyproject.toml"])

    return prereqs


def _build_install_section(analysis: dict) -> Optional[SetupSection]:
    """
    Build the dependency installation section.

    Only produces a section when manifest evidence supports known install commands.
    Never invents commands.
    """
    commands: list[SetupCommand] = []
    evidence_files: list[str] = []
    notes: list[str] = []

    package_managers = _package_managers(analysis)
    langs = _languages(analysis)
    runtimes = _runtimes(analysis)
    frameworks = _frameworks(analysis)

    # --- Python ---
    python_present = "Python" in langs or "Python" in runtimes

    requirements_file = _has_manifest(analysis, "requirements.txt")
    pipfile = _has_manifest(analysis, "Pipfile")
    pyproject = _has_manifest(analysis, "pyproject.toml")

    if "Pipenv" in package_managers and pipfile:
        commands.append(SetupCommand(
            command="pipenv install",
            explanation="Install Python dependencies using Pipenv.",
            evidence=[pipfile],
        ))
        evidence_files.append(pipfile)
    elif "Poetry" in package_managers and pyproject:
        commands.append(SetupCommand(
            command="poetry install",
            explanation="Install Python dependencies using Poetry.",
            evidence=[pyproject],
        ))
        evidence_files.append(pyproject)
    elif "uv" in package_managers and pyproject:
        commands.append(SetupCommand(
            command="uv sync",
            explanation="Install Python dependencies using uv.",
            evidence=[pyproject],
        ))
        evidence_files.append(pyproject)
    elif requirements_file and python_present:
        commands.append(SetupCommand(
            command="pip install -r requirements.txt",
            explanation="Install Python dependencies from requirements.txt.",
            evidence=[requirements_file],
        ))
        evidence_files.append(requirements_file)
    elif pyproject and python_present:
        commands.append(SetupCommand(
            command="pip install -e .",
            explanation="Install Python package in editable mode from pyproject.toml.",
            evidence=[pyproject],
        ))
        evidence_files.append(pyproject)

    # --- Node / JavaScript / TypeScript ---
    package_json = _has_manifest(analysis, "package.json")
    if package_json:
        if "Yarn" in package_managers:
            commands.append(SetupCommand(
                command="yarn install",
                explanation="Install Node.js dependencies using Yarn.",
                evidence=[package_json],
            ))
        elif "pnpm" in package_managers:
            commands.append(SetupCommand(
                command="pnpm install",
                explanation="Install Node.js dependencies using pnpm.",
                evidence=[package_json],
            ))
        else:
            commands.append(SetupCommand(
                command="npm install",
                explanation="Install Node.js dependencies from package.json.",
                evidence=[package_json],
            ))
        evidence_files.append(package_json)

    # --- Go ---
    go_mod = _has_manifest(analysis, "go.mod")
    if go_mod:
        commands.append(SetupCommand(
            command="go mod download",
            explanation="Download Go module dependencies.",
            evidence=[go_mod],
        ))
        evidence_files.append(go_mod)

    # --- Rust ---
    cargo_toml = _has_manifest(analysis, "Cargo.toml")
    if cargo_toml:
        commands.append(SetupCommand(
            command="cargo build",
            explanation="Build the Rust project and fetch dependencies.",
            evidence=[cargo_toml],
        ))
        evidence_files.append(cargo_toml)

    # --- Java/Maven ---
    pom_xml = _has_manifest(analysis, "pom.xml")
    if pom_xml:
        commands.append(SetupCommand(
            command="mvn install -DskipTests",
            explanation="Build the Maven project and install dependencies (skipping tests for setup).",
            evidence=[pom_xml],
        ))
        evidence_files.append(pom_xml)

    # --- Java/Gradle ---
    build_gradle = _has_manifest(analysis, "build.gradle", "build.gradle.kts")
    if build_gradle:
        commands.append(SetupCommand(
            command="./gradlew build -x test",
            explanation="Build the Gradle project and install dependencies (skipping tests for setup).",
            evidence=[build_gradle],
        ))
        evidence_files.append(build_gradle)

    if not commands:
        return None

    return SetupSection(
        title="Install Dependencies",
        description="Install the project's dependencies using the detected package manager.",
        commands=commands,
        notes=notes,
        evidence=list(dict.fromkeys(evidence_files)),
    )


def _build_env_section(analysis: dict) -> Optional[SetupSection]:
    """
    Build the environment configuration section.

    SECURITY: Never reads or exposes .env file contents.
    Only surfaces the filename and a safe note.
    """
    notes: list[str] = []
    evidence_files: list[str] = []
    commands: list[SetupCommand] = []

    # .env.example is the only env file we can safely reference
    env_example = None
    for f in _important_files(analysis):
        fp = f.get("file_path", "")
        name = fp.rsplit("/", 1)[-1].lower()
        if name == ".env.example" or name.endswith(".example"):
            if not _is_forbidden(fp):
                env_example = fp
                break

    # Also check config_files for .env.example
    if not env_example:
        for cf in _config_files(analysis):
            name = cf.rsplit("/", 1)[-1].lower()
            if name == ".env.example" or name.endswith(".example"):
                env_example = cf
                break

    # Check if there is ANY env-related evidence (without reading the files)
    has_env_evidence = any(
        cf.rsplit("/", 1)[-1].lower().startswith(".env")
        for cf in (analysis.get("technologies") or {}).get("config_files", [])
        if not _is_forbidden(cf)
    )

    if env_example:
        evidence_files.append(env_example)
        commands.append(SetupCommand(
            command=f"cp {env_example} .env",
            explanation="Copy the example environment file as a starting point.",
            evidence=[env_example],
        ))
        notes.append(
            f"An example environment file was detected at {env_example}. "
            "Copy it to .env and fill in the required values. "
            "Required variables cannot be safely determined from the indexed metadata — "
            "consult the project documentation."
        )
        notes.append(
            "SECURITY: Never commit .env files containing real secrets to version control."
        )
    elif has_env_evidence:
        notes.append(
            "This repository appears to use environment configuration. "
            "Required variables cannot be safely determined from the indexed metadata. "
            "Create a .env file based on the project documentation."
        )
        notes.append(
            "SECURITY: Never commit .env files containing real secrets to version control."
        )
    else:
        # Check for other config file types
        other_configs = _env_config_files(analysis)
        if other_configs:
            evidence_files.extend(other_configs[:3])
            notes.append(
                "Configuration files are present. Review the following for required settings: "
                + ", ".join(other_configs[:3])
            )

    if not notes and not evidence_files:
        return None

    return SetupSection(
        title="Environment Configuration",
        description=(
            "Configure environment variables and secrets required by the application. "
            "RepoGuide never reads or exposes .env file contents or secrets."
        ),
        commands=commands,
        notes=notes,
        evidence=list(dict.fromkeys(evidence_files)),
    )


def _build_database_section(analysis: dict) -> Optional[SetupSection]:
    """
    Build the database setup section when database evidence exists.

    Never executes migrations. Never invents migration commands.
    """
    databases = _databases(analysis)
    if not databases:
        return None

    notes: list[str] = []
    evidence_files: list[str] = []

    # Find migration-related files from the analysis
    migration_files = [
        f.get("file_path", "")
        for f in _important_files(analysis)
        if any(kw in f.get("file_path", "").lower()
               for kw in ("migrat", "schema", "alembic", "prisma"))
        and not _is_forbidden(f.get("file_path", ""))
    ]
    if migration_files:
        evidence_files.extend(migration_files[:3])

    db_list = ", ".join(databases)
    notes.append(
        f"Detected database technology: {db_list}. "
        "Ensure the required database service is running and accessible."
    )

    if "SQLAlchemy (Alembic)" in databases or any("alembic" in mf.lower() for mf in migration_files):
        notes.append(
            "Alembic migration files detected. "
            "Once the database is configured, migrations can be applied — "
            "consult the project documentation for the correct migration command."
        )

    if "Prisma ORM" in databases:
        # Prisma schema file is safe to reference
        prisma_schema = next(
            (f.get("file_path", "") for f in _important_files(analysis)
             if "prisma" in f.get("file_path", "").lower()
             and not _is_forbidden(f.get("file_path", ""))),
            None,
        )
        if prisma_schema:
            evidence_files.append(prisma_schema)
            notes.append(
                f"Prisma schema detected at {prisma_schema}. "
                "Refer to Prisma documentation for database push/migrate commands."
            )

    if "Supabase" in databases:
        notes.append(
            "Supabase detected. Configure SUPABASE_URL and the appropriate key "
            "in your environment file. The Supabase dashboard manages migrations."
        )

    if "SQLite" in databases:
        notes.append(
            "SQLite detected — typically no separate database service is required. "
            "The database file will be created locally."
        )

    notes.append(
        "RepoGuide does not execute migrations. "
        "Run the project's migration commands as documented in its README."
    )

    return SetupSection(
        title="Database Setup",
        description=f"Configure and initialise the database layer. Detected: {db_list}.",
        commands=[],
        notes=notes,
        evidence=list(dict.fromkeys(evidence_files)),
    )


def _build_run_section(analysis: dict) -> Optional[SetupSection]:
    """
    Build the run application section from detected dev commands and entry points.

    Only provides commands when evidence supports them.
    """
    commands: list[SetupCommand] = []
    evidence_files: list[str] = []
    notes: list[str] = []

    dev_cmds = _dev_commands(analysis)
    entry_pts = _entry_points(analysis)
    package_json = _has_manifest(analysis, "package.json")
    langs = _languages(analysis)
    runtimes = _runtimes(analysis)
    deployment_files = _deployment_files(analysis)
    frameworks = _frameworks(analysis)

    # --- npm/yarn/pnpm scripts from dev_commands ---
    for raw_cmd in dev_cmds:
        # dev_commands are already formatted like: "npm run dev  # vite"
        cmd_lower = raw_cmd.lower()
        # Only surface start/dev/serve/watch scripts — not test, build, etc.
        if any(kw in cmd_lower for kw in ("run dev", "run start", "run serve",
                                           "run watch", "run preview")):
            # Sanitise in case repository metadata contains injection text
            cmd_clean = _safe_text(raw_cmd.split("#")[0].strip())
            explanation = (
                "Start the development server (detected from package.json scripts)."
                if "dev" in cmd_lower or "watch" in cmd_lower
                else "Start the application (detected from package.json scripts)."
            )
            commands.append(SetupCommand(
                command=cmd_clean,
                explanation=explanation,
                evidence=[package_json] if package_json else [],
            ))
            if package_json:
                evidence_files.append(package_json)

    # --- Python entry points ---
    python_present = "Python" in langs or "Python" in runtimes
    if python_present:
        # FastAPI / uvicorn
        if "FastAPI" in frameworks:
            for ep in entry_pts:
                fp = ep.get("file_path", "")
                if not _is_forbidden(fp) and fp.endswith(".py"):
                    module = fp.replace("/", ".").removesuffix(".py")
                    commands.append(SetupCommand(
                        command=f"uvicorn {module}:app --reload",
                        explanation=(
                            f"Start the FastAPI development server. "
                            f"Entry point detected at {fp}."
                        ),
                        evidence=[fp],
                    ))
                    evidence_files.append(fp)
                    break
        # Flask
        elif "Flask" in frameworks:
            for ep in entry_pts:
                fp = ep.get("file_path", "")
                if not _is_forbidden(fp) and fp.endswith(".py"):
                    commands.append(SetupCommand(
                        command="flask run",
                        explanation=(
                            f"Start the Flask development server. "
                            f"Entry point detected at {fp}."
                        ),
                        evidence=[fp],
                    ))
                    evidence_files.append(fp)
                    break
        # Django
        elif "Django" in frameworks or "Django/WSGI" in frameworks:
            manage_py = next(
                (ep.get("file_path", "") for ep in entry_pts
                 if "manage.py" in ep.get("file_path", "")
                 and not _is_forbidden(ep.get("file_path", ""))),
                None,
            )
            if manage_py:
                commands.append(SetupCommand(
                    command="python manage.py runserver",
                    explanation="Start the Django development server.",
                    evidence=[manage_py],
                ))
                evidence_files.append(manage_py)
        # Generic Python
        elif not commands:
            for ep in entry_pts[:1]:
                fp = ep.get("file_path", "")
                if not _is_forbidden(fp) and fp.endswith(".py"):
                    commands.append(SetupCommand(
                        command=f"python {fp}",
                        explanation=(
                            f"Run the Python application. "
                            f"Entry point detected at {fp}."
                        ),
                        evidence=[fp],
                    ))
                    evidence_files.append(fp)

    # --- Go ---
    if "Go" in langs or "Go" in runtimes:
        go_mod = _has_manifest(analysis, "go.mod")
        if go_mod and not commands:
            commands.append(SetupCommand(
                command="go run .",
                explanation="Run the Go application from the module root.",
                evidence=[go_mod],
            ))
            evidence_files.append(go_mod)

    # --- Rust ---
    if "Rust" in langs or "Rust" in runtimes:
        cargo = _has_manifest(analysis, "Cargo.toml")
        if cargo and not any("cargo" in c.command for c in commands):
            commands.append(SetupCommand(
                command="cargo run",
                explanation="Build and run the Rust application.",
                evidence=[cargo],
            ))
            evidence_files.append(cargo)

    # --- Docker ---
    docker_compose = next(
        (f for f in deployment_files if "docker-compose" in f.lower()), None
    )
    dockerfile = next(
        (f for f in deployment_files if "dockerfile" == f.rsplit("/", 1)[-1].lower()), None
    )
    if docker_compose:
        commands.append(SetupCommand(
            command="docker compose up",
            explanation="Start the application using Docker Compose.",
            evidence=[docker_compose],
        ))
        evidence_files.append(docker_compose)
    elif dockerfile and not commands:
        commands.append(SetupCommand(
            command="docker build -t app . && docker run -p 8080:8080 app",
            explanation="Build and run the Docker container.",
            evidence=[dockerfile],
        ))
        evidence_files.append(dockerfile)

    if not commands:
        if not entry_pts and not dev_cmds:
            return None
        notes.append(
            "RepoGuide could not determine a specific run command from the indexed "
            "repository metadata. Check the README for startup instructions."
        )

    # Note if frontend and backend appear to require separate startup
    frontend_comps = _tech(analysis).get("frontend_components") or []
    backend_comps = _tech(analysis).get("backend_components") or []
    if frontend_comps and backend_comps and len(commands) >= 2:
        notes.append(
            "This repository appears to have both frontend and backend components. "
            "You may need to start them in separate terminal sessions."
        )

    return SetupSection(
        title="Run the Application",
        description="Start the application using the commands detected from repository evidence.",
        commands=commands,
        notes=notes,
        evidence=list(dict.fromkeys(evidence_files)),
    )


def _build_verify_section(analysis: dict) -> Optional[SetupSection]:
    """
    Build safe verification steps from repository evidence.

    Only references tests, API endpoints, or build steps actually evidenced.
    Does NOT execute any commands.
    """
    notes: list[str] = []
    commands: list[SetupCommand] = []
    evidence_files: list[str] = []

    langs = _languages(analysis)
    runtimes = _runtimes(analysis)
    frameworks = _frameworks(analysis)
    test_files = _filter_paths(_tech(analysis).get("test_files") or [])
    test_dirs = _filter_paths(_tech(analysis).get("test_directories") or [])
    package_json = _has_manifest(analysis, "package.json")
    dev_cmds = _dev_commands(analysis)

    # --- Run test suite ---
    has_tests = bool(test_files or test_dirs)

    if has_tests:
        # Python
        if "Python" in langs or "Python" in runtimes:
            ev = test_files[:2] + test_dirs[:1]
            commands.append(SetupCommand(
                command="pytest",
                explanation="Run the Python test suite to verify the setup.",
                evidence=ev,
            ))
            evidence_files.extend(ev)

        # Node — look for test script in dev_commands
        test_script = next(
            (raw.split("#")[0].strip() for raw in dev_cmds
             if "run test" in raw.lower() or "run vitest" in raw.lower()),
            None,
        )
        if test_script and package_json:
            cmd_clean = _safe_text(test_script)
            commands.append(SetupCommand(
                command=cmd_clean,
                explanation="Run the Node.js test suite to verify the setup.",
                evidence=[package_json] + test_files[:1],
            ))
            evidence_files.append(package_json)

        # Go
        if "Go" in langs or "Go" in runtimes:
            go_mod = _has_manifest(analysis, "go.mod")
            ev_go = [go_mod] if go_mod else []
            commands.append(SetupCommand(
                command="go test ./...",
                explanation="Run the Go test suite to verify the setup.",
                evidence=ev_go,
            ))
            if go_mod:
                evidence_files.append(go_mod)

        # Rust
        if "Rust" in langs or "Rust" in runtimes:
            cargo = _has_manifest(analysis, "Cargo.toml")
            ev_rs = [cargo] if cargo else []
            commands.append(SetupCommand(
                command="cargo test",
                explanation="Run the Rust test suite to verify the setup.",
                evidence=ev_rs,
            ))
            if cargo:
                evidence_files.append(cargo)

    # --- Build verification (Node only) ---
    build_script = next(
        (raw.split("#")[0].strip() for raw in dev_cmds
         if "run build" in raw.lower()),
        None,
    )
    if build_script and package_json:
        cmd_clean = _safe_text(build_script)
        commands.append(SetupCommand(
            command=cmd_clean,
            explanation="Verify the production build compiles successfully.",
            evidence=[package_json],
        ))
        evidence_files.append(package_json)

    # --- Notes when no test evidence ---
    if not has_tests:
        notes.append(
            "No test files were detected in the indexed repository metadata. "
            "Verify the setup manually by running the application and confirming it starts."
        )

    if not commands and not notes:
        return None

    return SetupSection(
        title="Verify Your Setup",
        description="Run these steps to verify the project is set up correctly.",
        commands=commands,
        notes=notes,
        evidence=list(dict.fromkeys(evidence_files)),
    )


# ---------------------------------------------------------------------------
# Confidence and warnings
# ---------------------------------------------------------------------------

def _compute_confidence(analysis: dict, guide: SetupGuide) -> SetupConfidence:
    """
    Compute overall setup confidence from actual evidence.

    high   — manifest + package manager + run commands or entry points detected
    medium — partial evidence (e.g. manifest but no run commands, or runtime but no manifest)
    low    — very little evidence; guide mostly contains notes rather than commands
    """
    has_manifest = bool(
        _has_manifest(analysis, "requirements.txt", "package.json",
                      "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Pipfile")
    )
    has_pkg_manager = bool(_package_managers(analysis))
    has_run_cmds = bool(
        guide.run_application and guide.run_application.commands
    )
    has_install_cmds = bool(
        guide.install_dependencies and guide.install_dependencies.commands
    )
    has_prereqs = bool(guide.prerequisites)

    score = sum([
        has_manifest,
        has_pkg_manager,
        has_run_cmds,
        has_install_cmds,
        has_prereqs,
    ])

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _build_warnings(analysis: dict, guide: SetupGuide) -> list[SetupWarning]:
    """
    Generate warnings when evidence supports them. No unsupported claims.
    """
    warnings: list[SetupWarning] = []

    env_config = _env_config_files(analysis)
    has_env_evidence = any(
        cf.rsplit("/", 1)[-1].lower().startswith(".env")
        for cf in (analysis.get("technologies") or {}).get("config_files", [])
    )

    # 1. Environment variables appear necessary
    if has_env_evidence or guide.environment_configuration:
        ev = []
        if guide.environment_configuration:
            ev = guide.environment_configuration.evidence[:2]
        warnings.append(SetupWarning(
            message=(
                "Environment variables appear to be required by this repository. "
                "Ensure all required variables are configured before running the application."
            ),
            evidence=ev,
        ))

    # 2. Docker configuration exists
    docker_files = [f for f in _deployment_files(analysis)
                    if "dockerfile" in f.lower() or "docker-compose" in f.lower()]
    if docker_files:
        warnings.append(SetupWarning(
            message=(
                "Docker configuration detected. "
                "You can run the application with Docker Compose or build a Docker image "
                "as an alternative to running it directly."
            ),
            evidence=docker_files[:2],
        ))

    # 3. Multiple package managers detected
    pkg_managers = _package_managers(analysis)
    if len(pkg_managers) > 1:
        warnings.append(SetupWarning(
            message=(
                f"Multiple package managers detected: {', '.join(pkg_managers)}. "
                "Use the appropriate one for each component of the repository."
            ),
            evidence=_dep_manifest_files(analysis)[:2],
        ))

    # 4. Database configuration exists
    if guide.database_setup:
        warnings.append(SetupWarning(
            message=(
                "A database configuration is required. "
                "Ensure the database service is running and the connection is configured "
                "before starting the application."
            ),
            evidence=guide.database_setup.evidence[:2],
        ))

    # 5. Frontend and backend appear to require separate startup
    frontend = _tech(analysis).get("frontend_components") or []
    backend = _tech(analysis).get("backend_components") or []
    if frontend and backend:
        warnings.append(SetupWarning(
            message=(
                "This repository appears to have both frontend and backend components. "
                "You may need to run setup and start commands for each separately."
            ),
            evidence=[],
        ))

    # 6. Confidence is low — setup guide is incomplete
    if guide.confidence == "low":
        warnings.append(SetupWarning(
            message=(
                "RepoGuide could not find sufficient setup evidence in the indexed "
                "repository metadata. Check the repository README for complete setup instructions."
            ),
            evidence=[],
        ))

    return warnings


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_setup_guide(repository_id: str, guide: SetupGuide) -> None:
    """
    Persist the setup guide JSON into the analyses.setup_guide column.

    Uses upsert on the analyses row for this repository.
    Errors are logged but do not propagate — persistence is best-effort here.
    """
    try:
        supabase = get_supabase()
        guide_json = guide.model_dump_json()

        supabase.table("analyses").update(
            {"setup_guide": guide_json}
        ).eq("repository_id", repository_id).execute()

    except Exception as exc:
        logger.warning(
            "Could not persist setup guide for %s: %s", repository_id, exc
        )


def _load_persisted_guide(repository_id: str) -> Optional[str]:
    """
    Load the setup_guide JSON string from analyses for this repository.

    Returns the raw JSON string or None.
    """
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("analyses")
            .select("setup_guide")
            .eq("repository_id", repository_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            return rows[0].get("setup_guide")
        return None
    except Exception as exc:
        logger.warning(
            "Could not load setup guide for %s: %s", repository_id, exc
        )
        return None


def _load_analysis(repository_id: str) -> Optional[dict]:
    """Load the stored analysis row for this repository."""
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("analyses")
            .select("*")
            .eq("repository_id", repository_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("Failed to fetch analysis for %s: %s", repository_id, exc)
        return None


def _load_repository(repository_id: str) -> Optional[dict]:
    """Load the repository record."""
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("repositories")
            .select("id,name,description,github_url")
            .eq("id", repository_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("Failed to fetch repository %s: %s", repository_id, exc)
        return None


# ---------------------------------------------------------------------------
# Evidence quality check
# ---------------------------------------------------------------------------

def _has_sufficient_evidence(analysis: dict) -> bool:
    """
    Return True when we have enough evidence to produce a useful guide.

    Requires at least one of: language, framework, runtime, package manager,
    manifest file, or entry point.
    """
    langs = _languages(analysis)
    frameworks = _frameworks(analysis)
    runtimes = _runtimes(analysis)
    pkg_managers = _package_managers(analysis)
    entry_pts = _entry_points(analysis)
    manifests = _dep_manifest_files(analysis)

    return bool(langs or frameworks or runtimes or pkg_managers or entry_pts or manifests)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_setup_guide(repository_id: str) -> SetupGuideResponse:
    """
    Generate a repository-grounded setup guide.

    Fetches the stored analysis, builds the guide from deterministic evidence
    extractors, persists the result, and returns a SetupGuideResponse.

    Does NOT raise — all errors are captured in the response.
    """
    # 1. Validate repository exists
    repo = _load_repository(repository_id)
    if repo is None:
        return SetupGuideResponse(
            repository_id=repository_id,
            status="error",
            error="Repository not found.",
        )

    # 2. Fetch analysis
    analysis = _load_analysis(repository_id)
    if analysis is None:
        return SetupGuideResponse(
            repository_id=repository_id,
            status="no_analysis",
            error=(
                "No analysis found for this repository. "
                "Run repository analysis before generating a setup guide."
            ),
        )

    # 3. Check evidence quality
    if not _has_sufficient_evidence(analysis):
        return SetupGuideResponse(
            repository_id=repository_id,
            status="insufficient_evidence",
            error=(
                "RepoGuide could not determine setup steps from the indexed "
                "repository metadata. The repository may be empty or have too few files."
            ),
        )

    # 4. Build sections
    prerequisites = _build_prerequisites(analysis)
    install_section = _build_install_section(analysis)
    env_section = _build_env_section(analysis)
    db_section = _build_database_section(analysis)
    run_section = _build_run_section(analysis)
    verify_section = _build_verify_section(analysis)

    # 5. Assemble guide (partial — without confidence yet)
    guide = SetupGuide(
        repository_id=repository_id,
        generated_at=datetime.now(timezone.utc),
        prerequisites=prerequisites,
        install_dependencies=install_section,
        environment_configuration=env_section,
        database_setup=db_section,
        run_application=run_section,
        verify_setup=verify_section,
        confidence="low",   # placeholder — computed next
        warnings=[],
        is_deterministic=True,
    )

    # 6. Compute confidence and warnings now that guide is assembled
    guide.confidence = _compute_confidence(analysis, guide)
    guide.warnings = _build_warnings(analysis, guide)

    # 7. Persist
    _persist_setup_guide(repository_id, guide)

    return SetupGuideResponse(
        repository_id=repository_id,
        guide=guide,
        status="ok",
        generated_at=guide.generated_at,
    )


def get_setup_guide(repository_id: str) -> SetupGuideResponse:
    """
    Retrieve the setup guide for a repository.

    Tries the persisted guide first; falls back to live generation.
    """
    # Validate repository exists first
    repo = _load_repository(repository_id)
    if repo is None:
        return SetupGuideResponse(
            repository_id=repository_id,
            status="error",
            error="Repository not found.",
        )

    # Try loading persisted guide
    raw_json = _load_persisted_guide(repository_id)
    if raw_json:
        try:
            guide = SetupGuide.model_validate_json(raw_json)
            return SetupGuideResponse(
                repository_id=repository_id,
                guide=guide,
                status="ok",
                generated_at=guide.generated_at,
            )
        except Exception as exc:
            logger.warning(
                "Could not deserialise persisted setup guide for %s, regenerating: %s",
                repository_id,
                exc,
            )

    # Fall back to live generation
    return generate_setup_guide(repository_id)
