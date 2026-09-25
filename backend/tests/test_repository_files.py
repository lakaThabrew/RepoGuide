"""
Tests for repository file persistence pipeline.

Covers:
  1. Successful file persistence
  2. Excluded files (forbidden names, ignored dirs, ignored extensions)
  3. Repeated ingestion / idempotency (no duplicate rows)
  4. Empty repository (zero files)
  5. GitHub clone failure
  6. Malicious / path-traversal filename
  7. Secret / .env exclusion
"""

from __future__ import annotations

import sys
import types
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Stubs — installed before any app import so no real credentials are needed
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
# Imports under test (after stubs)
# ---------------------------------------------------------------------------

from app.services import repository_service  # noqa: E402
from app.services import github_service       # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file(path, name, ext, size=100, is_dir=False):
    return {
        "file_path": path,
        "file_name": name,
        "extension": ext,
        "file_size": size,
        "is_directory": is_dir,
    }


def _make_supabase_mock():
    """Return a MagicMock that chains .table().delete().eq().execute() etc."""
    mock = MagicMock()
    # Make every attribute access return the same mock so chaining works
    mock.table.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.insert.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


REPO_ID = "repo-uuid-1234"

SAMPLE_FILES = [
    _make_file("src/main.py",          "main.py",          ".py",   800),
    _make_file("src/utils.py",         "utils.py",         ".py",   400),
    _make_file("README.md",            "README.md",        ".md",   200),
    _make_file("package.json",         "package.json",     ".json", 300),
    _make_file("src",                  "src",              "",      0, True),
]


# ---------------------------------------------------------------------------
# 1. Successful file persistence
# ---------------------------------------------------------------------------

class TestPersistRepositoryFiles:

    def test_inserts_correct_number_of_rows(self):
        """All sample files are inserted as rows."""
        supabase = _make_supabase_mock()
        with patch.object(repository_service, "get_supabase", return_value=supabase):
            count = repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)

        assert count == len(SAMPLE_FILES)

    def test_deletes_existing_rows_before_insert(self):
        """Existing rows are deleted to ensure idempotency."""
        supabase = _make_supabase_mock()
        with patch.object(repository_service, "get_supabase", return_value=supabase):
            repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)

        # delete() must have been called with the correct repository_id
        supabase.table.assert_any_call("repository_files")
        supabase.delete.assert_called()
        supabase.eq.assert_any_call("repository_id", REPO_ID)

    def test_language_populated_for_code_files(self):
        """Python files get language='Python'; directories get language=None."""
        captured_rows = []

        def _fake_insert(rows):
            captured_rows.extend(rows)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[])
            return m

        supabase = _make_supabase_mock()
        supabase.insert.side_effect = _fake_insert

        with patch.object(repository_service, "get_supabase", return_value=supabase):
            repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)

        py_rows = [r for r in captured_rows if r["extension"] == ".py"]
        assert all(r["language"] == "Python" for r in py_rows), py_rows

        dir_rows = [r for r in captured_rows if r["is_directory"]]
        assert all(r["language"] is None for r in dir_rows), dir_rows

    def test_repository_id_on_every_row(self):
        """Every inserted row carries the correct repository_id."""
        captured_rows = []

        def _fake_insert(rows):
            captured_rows.extend(rows)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[])
            return m

        supabase = _make_supabase_mock()
        supabase.insert.side_effect = _fake_insert

        with patch.object(repository_service, "get_supabase", return_value=supabase):
            repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)

        assert all(r["repository_id"] == REPO_ID for r in captured_rows)


# ---------------------------------------------------------------------------
# 2. Excluded files
# ---------------------------------------------------------------------------

class TestExcludedFiles:

    def test_ignored_dirs_not_scanned(self):
        """scan_repository_files skips IGNORE_DIRS."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create a real Python file
            (Path(tmp) / "main.py").write_text("print('hello')")
            # Create an ignored directory with a file inside
            (Path(tmp) / "node_modules").mkdir()
            (Path(tmp) / "node_modules" / "lodash.js").write_text("// lodash")

            files = github_service.scan_repository_files(tmp)

        paths = [f["file_path"] for f in files]
        assert any("main.py" in p for p in paths)
        assert not any("node_modules" in p for p in paths)

    def test_ignored_extensions_not_scanned(self):
        """scan_repository_files skips IGNORE_EXTENSIONS."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "app.py").write_text("# ok")
            (Path(tmp) / "data.bin").write_bytes(b"\x00\x01")
            (Path(tmp) / "image.jpg").write_bytes(b"\xff\xd8")

            files = github_service.scan_repository_files(tmp)

        paths = [f["file_path"] for f in files]
        assert any("app.py" in p for p in paths)
        assert not any("data.bin" in p for p in paths)
        assert not any("image.jpg" in p for p in paths)

    def test_forbidden_filenames_excluded_by_clone_and_scan(self):
        """clone_and_scan_repository removes forbidden filenames post-scan."""
        normal_files = [
            _make_file("src/main.py", "main.py", ".py"),
            _make_file(".env", ".env", ""),
            _make_file("secrets.yml", "secrets.yml", ".yml"),
        ]
        with patch.object(
            github_service, "scan_repository_files", return_value=normal_files
        ), patch("git.Repo.clone_from"):
            with patch("tempfile.mkdtemp", return_value="/tmp/fakerepo"):
                with patch("shutil.rmtree"):
                    # Manually call the post-filter logic by running the function
                    # with a patched clone (no real network)
                    import git
                    with patch.object(git.Repo, "clone_from", return_value=MagicMock()):
                        result = github_service.clone_and_scan_repository(
                            "https://github.com/owner/repo"
                        )

        paths = [f["file_path"] for f in result]
        assert not any(p in (".env", "secrets.yml") for p in paths), \
            f"Forbidden files found in scan result: {paths}"


# ---------------------------------------------------------------------------
# 3. Repeated ingestion / idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_second_persist_replaces_first(self):
        """Calling persist_repository_files twice results in exactly one set of rows."""
        insert_calls = []

        def _track_insert(rows):
            insert_calls.append(list(rows))
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[])
            return m

        supabase = _make_supabase_mock()
        supabase.insert.side_effect = _track_insert

        with patch.object(repository_service, "get_supabase", return_value=supabase):
            repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)
            repository_service.persist_repository_files(REPO_ID, SAMPLE_FILES)

        # delete() must have been called twice (once per persist call)
        assert supabase.delete.call_count == 2

    def test_ingest_repository_calls_persist_once(self):
        """ingest_repository calls persist_repository_files exactly once."""
        fake_repo = {
            "id": REPO_ID,
            "name": "myrepo",
            "owner": "owner",
            "github_url": "https://github.com/owner/myrepo",
        }

        with patch.object(repository_service, "get_repository", return_value=fake_repo), \
             patch.object(repository_service, "update_repository_status"), \
             patch.object(
                 repository_service.github_service if hasattr(repository_service, "github_service") else repository_service,
                 "get_github_repo_info", return_value=None, create=True,
             ) if False else patch("app.services.github_service.get_github_repo_info", return_value=None), \
             patch("app.services.github_service.clone_and_scan_repository", return_value=SAMPLE_FILES), \
             patch.object(repository_service, "persist_repository_files", return_value=len(SAMPLE_FILES)) as mock_persist:

            result = repository_service.ingest_repository(REPO_ID)

        mock_persist.assert_called_once_with(REPO_ID, SAMPLE_FILES)
        assert result["files_scanned"] == len(SAMPLE_FILES)


# ---------------------------------------------------------------------------
# 4. Empty repository
# ---------------------------------------------------------------------------

class TestEmptyRepository:

    def test_persist_empty_files_returns_zero(self):
        supabase = _make_supabase_mock()
        with patch.object(repository_service, "get_supabase", return_value=supabase):
            count = repository_service.persist_repository_files(REPO_ID, [])

        assert count == 0
        # delete should still have run (to clear any leftover rows)
        supabase.delete.assert_called()

    def test_ingest_empty_repo_returns_zero_files(self):
        """An empty repository (clone succeeds, no files) returns files_scanned=0."""
        fake_repo = {
            "id": REPO_ID,
            "name": "empty",
            "owner": "owner",
            "github_url": "https://github.com/owner/empty",
        }

        with patch.object(repository_service, "get_repository", return_value=fake_repo), \
             patch.object(repository_service, "update_repository_status"), \
             patch("app.services.github_service.get_github_repo_info", return_value=None), \
             patch("app.services.github_service.clone_and_scan_repository", return_value=[]), \
             patch.object(repository_service, "get_supabase", return_value=_make_supabase_mock()):

            result = repository_service.ingest_repository(REPO_ID)

        assert result["status"] == "scanned"
        assert result["files_scanned"] == 0


# ---------------------------------------------------------------------------
# 5. GitHub clone failure
# ---------------------------------------------------------------------------

class TestGitHubFailure:

    def test_clone_failure_returns_empty_list(self):
        """clone_and_scan_repository returns [] when clone fails."""
        import git

        with patch.object(git.Repo, "clone_from", side_effect=Exception("network error")):
            result = github_service.clone_and_scan_repository(
                "https://github.com/owner/repo"
            )

        assert result == []

    def test_ingest_repository_handles_clone_failure(self):
        """ingest_repository captures clone failure and sets status=error."""
        fake_repo = {
            "id": REPO_ID,
            "name": "repo",
            "owner": "owner",
            "github_url": "https://github.com/owner/repo",
        }

        def _boom(*a, **kw):
            raise RuntimeError("clone failed")

        with patch.object(repository_service, "get_repository", return_value=fake_repo), \
             patch.object(repository_service, "update_repository_status"), \
             patch("app.services.github_service.get_github_repo_info", return_value=None), \
             patch("app.services.github_service.clone_and_scan_repository", side_effect=_boom):

            result = repository_service.ingest_repository(REPO_ID)

        assert result["status"] == "error"
        assert "error" in result

    def test_ingest_repository_not_found(self):
        with patch.object(repository_service, "get_repository", return_value=None):
            result = repository_service.ingest_repository("nonexistent")

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# 6. Malicious / path-traversal filename
# ---------------------------------------------------------------------------

class TestPathTraversal:

    def test_path_traversal_excluded(self):
        """Files with path-traversal sequences are excluded by clone_and_scan_repository."""
        traversal_files = [
            _make_file("src/main.py", "main.py", ".py"),
            # Simulated traversal path (relative, but resolves outside base)
            {"file_path": "../../../etc/passwd", "file_name": "passwd",
             "extension": "", "file_size": 0, "is_directory": False},
        ]

        import git

        with patch.object(git.Repo, "clone_from", return_value=MagicMock()):
            with patch.object(
                github_service, "scan_repository_files", return_value=traversal_files
            ):
                result = github_service.clone_and_scan_repository(
                    "https://github.com/owner/repo"
                )

        paths = [f["file_path"] for f in result]
        assert "../../../etc/passwd" not in paths, \
            f"Path traversal entry was NOT excluded: {paths}"

    def test_is_safe_path_rejects_traversal(self):
        """_is_safe_path returns False for paths that escape the base directory."""
        from app.services.github_service import _is_safe_path

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # A normal child path
            assert _is_safe_path(base, base / "src" / "main.py")
            # An escaping path
            assert not _is_safe_path(base, base / ".." / ".." / "etc" / "passwd")


# ---------------------------------------------------------------------------
# 7. Secret / .env exclusion
# ---------------------------------------------------------------------------

class TestSecretExclusion:

    def test_env_file_excluded_from_clone_scan(self):
        """.env files are excluded even if the scanner returns them."""
        files_with_env = [
            _make_file("src/app.py",  "app.py",  ".py"),
            _make_file(".env",        ".env",     ""),
            _make_file(".env.local",  ".env.local", ""),
            _make_file("id_rsa",      "id_rsa",   ""),
        ]

        import git

        with patch.object(git.Repo, "clone_from", return_value=MagicMock()):
            with patch.object(
                github_service, "scan_repository_files", return_value=files_with_env
            ):
                result = github_service.clone_and_scan_repository(
                    "https://github.com/owner/repo"
                )

        names = [f["file_name"] for f in result]
        assert ".env" not in names,        f".env found in scan: {names}"
        assert ".env.local" not in names,  f".env.local found in scan: {names}"
        assert "id_rsa" not in names,      f"id_rsa found in scan: {names}"
        assert "app.py" in names,          f"app.py should be present: {names}"

    def test_forbidden_names_set_is_complete(self):
        """_FORBIDDEN_FILENAMES includes the most critical secret files."""
        critical = {".env", "id_rsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc"}
        missing = critical - github_service._FORBIDDEN_FILENAMES
        assert not missing, f"Missing from _FORBIDDEN_FILENAMES: {missing}"
