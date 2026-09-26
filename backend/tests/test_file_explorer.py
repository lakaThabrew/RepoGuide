"""
Tests for the Session-13 repository file explorer.

Covers:
  1. validate_file_path — path security rules
  2. get_github_file_content — content retrieval, binary detection, size limits
  3. GET /files — file tree endpoint
  4. GET /files/content — file content endpoint
  5. Secret safety — tokens never in responses
  6. Repository isolation — repository_id gates access
"""

from __future__ import annotations

import base64
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so the app can be imported without real credentials
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

from app.services.github_service import (  # noqa: E402
    validate_file_path,
    get_github_file_content,
    _CONTENT_FORBIDDEN_FILENAMES,
    BINARY_EXTENSIONS,
)
from app.api import files as files_api  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ID = "repo-uuid-test"
FAKE_REPO = {
    "id": REPO_ID,
    "owner": "testowner",
    "name": "testrepo",
    "github_url": "https://github.com/testowner/testrepo",
    "status": "scanned",
}

_B64 = base64.b64encode(b"print('hello')\n").decode() + "\n"


def _mock_github_200(content_b64: str, size: int = 100):
    """Fake a GitHub API 200 response for a text file."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "encoding": "base64",
        "content": content_b64,
        "size": size,
    }
    return mock


def _supabase_files_mock(rows: list[dict]):
    """Return a Supabase mock that yields `rows` from the repository_files table."""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.execute.return_value = MagicMock(data=rows)
    return mock


# ===========================================================================
# 1. Path security — validate_file_path
# ===========================================================================

class TestValidateFilePath:

    # --- Happy paths --------------------------------------------------------

    def test_normal_path_accepted(self):
        ok, _ = validate_file_path("backend/app/main.py")
        assert ok

    def test_root_level_file_accepted(self):
        ok, _ = validate_file_path("README.md")
        assert ok

    def test_nested_path_accepted(self):
        ok, _ = validate_file_path("src/services/auth/token.py")
        assert ok

    def test_dotfile_configuration_accepted(self):
        ok, _ = validate_file_path(".gitignore")
        assert ok

    # --- Traversal attacks --------------------------------------------------

    def test_unix_traversal_rejected(self):
        ok, reason = validate_file_path("../etc/passwd")
        assert not ok
        assert reason  # non-empty reason

    def test_double_traversal_rejected(self):
        ok, _ = validate_file_path("../../secret")
        assert not ok

    def test_windows_traversal_rejected(self):
        ok, _ = validate_file_path("..\\etc\\passwd")
        assert not ok

    def test_absolute_unix_path_rejected(self):
        ok, _ = validate_file_path("/etc/passwd")
        assert not ok

    def test_absolute_windows_path_rejected(self):
        ok, _ = validate_file_path("C:\\Windows\\system32\\cmd.exe")
        assert not ok

    def test_null_byte_rejected(self):
        ok, _ = validate_file_path("file\x00name.py")
        assert not ok

    def test_url_encoded_traversal_rejected(self):
        ok, _ = validate_file_path("%2e%2e%2fetc%2fpasswd")
        assert not ok

    def test_double_encoded_traversal_rejected(self):
        ok, _ = validate_file_path("%252e%252e/etc/passwd")
        assert not ok

    def test_url_encoded_null_byte_rejected(self):
        ok, _ = validate_file_path("file%00name.py")
        assert not ok

    def test_empty_path_rejected(self):
        ok, _ = validate_file_path("")
        assert not ok

    def test_whitespace_only_rejected(self):
        ok, _ = validate_file_path("   ")
        assert not ok

    # --- Forbidden files ----------------------------------------------------

    def test_env_file_rejected(self):
        ok, reason = validate_file_path(".env")
        assert not ok
        assert "cannot be previewed" in reason

    def test_env_local_rejected(self):
        ok, _ = validate_file_path(".env.local")
        assert not ok

    def test_env_production_rejected(self):
        ok, _ = validate_file_path(".env.production")
        assert not ok

    def test_env_custom_rejected(self):
        ok, _ = validate_file_path(".env.custom")
        assert not ok

    def test_id_rsa_rejected(self):
        ok, _ = validate_file_path("id_rsa")
        assert not ok

    def test_id_rsa_in_subdir_rejected(self):
        ok, _ = validate_file_path("home/user/.ssh/id_rsa")
        assert not ok

    def test_id_ed25519_rejected(self):
        ok, _ = validate_file_path("id_ed25519")
        assert not ok

    def test_npmrc_rejected(self):
        ok, _ = validate_file_path(".npmrc")
        assert not ok

    def test_pypirc_rejected(self):
        ok, _ = validate_file_path(".pypirc")
        assert not ok

    def test_pem_extension_rejected(self):
        ok, _ = validate_file_path("cert.pem")
        assert not ok

    def test_key_extension_rejected(self):
        ok, _ = validate_file_path("server.key")
        assert not ok

    def test_secrets_yml_rejected(self):
        ok, _ = validate_file_path("secrets.yml")
        assert not ok

    def test_secrets_yaml_rejected(self):
        ok, _ = validate_file_path("secrets.yaml")
        assert not ok


# ===========================================================================
# 2. get_github_file_content
# ===========================================================================

class TestGetGithubFileContent:

    def test_text_file_returned(self):
        content = "def hello(): pass\n"
        b64 = base64.b64encode(content.encode()).decode() + "\n"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": b64,
            "size": len(content),
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "src/main.py")

        assert result["content"] == content
        assert result["is_binary"] is False
        assert result["error"] is None
        assert result["truncated"] is False

    def test_missing_file_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "nonexistent.py")

        assert result["content"] is None
        assert result["error"] == "File not found in repository."

    def test_private_repo_403_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "main.py")

        assert result["content"] is None
        assert "denied" in result["error"].lower() or "private" in result["error"].lower()

    def test_oversized_file_rejected(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": base64.b64encode(b"x" * 100).decode(),
            "size": 600_000,  # > 500 KB
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "bigfile.py")

        assert result["content"] is None
        assert "too large" in result["error"].lower()
        assert result["is_binary"] is False

    def test_binary_file_detected_by_null_bytes(self):
        binary_content = b"\x00\x01\x02\x03binary data"
        b64 = base64.b64encode(binary_content).decode() + "\n"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": b64,
            "size": len(binary_content),
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "data.bin")

        assert result["is_binary"] is True
        assert result["content"] is None

    def test_invalid_base64_handled(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": "this is not valid base64!!!@@@",
            "size": 50,
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "weird.py")

        assert result["content"] is None
        assert result["is_binary"] is True

    def test_empty_file_returns_empty_string(self):
        b64 = base64.b64encode(b"").decode() + "\n"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": b64,
            "size": 0,
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "empty.py")

        assert result["content"] == ""
        assert result["is_binary"] is False
        assert result["error"] is None

    def test_malformed_json_response_handled(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not JSON")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "main.py")

        assert result["content"] is None
        assert result["error"]

    def test_directory_path_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # GitHub returns a list for directories
        mock_resp.json.return_value = [{"name": "file.py", "type": "file"}]

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "src")

        assert result["content"] is None
        assert "directory" in result["error"].lower()

    def test_network_timeout_handled(self):
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "main.py")

        assert result["content"] is None
        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()

    def test_non_utf8_file_detected_as_binary(self):
        # Latin-1 content that is not valid UTF-8
        raw = bytes([0x80, 0x81, 0x82, 0x83, 0x84])
        b64 = base64.b64encode(raw).decode() + "\n"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": b64,
            "size": len(raw),
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = None
                result = get_github_file_content("owner", "repo", "latin1.txt")

        assert result["is_binary"] is True
        assert result["content"] is None

    # --- Secret safety -------------------------------------------------------

    def test_github_token_never_in_content_response(self):
        """The GitHub token must not appear anywhere in the returned dict."""
        content = "some source code\n"
        b64 = base64.b64encode(content.encode()).decode() + "\n"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "encoding": "base64",
            "content": b64,
            "size": len(content),
        }

        fake_token = "ghp_supersecrettoken123"

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = fake_token
                result = get_github_file_content("owner", "repo", "src/main.py")

        result_str = str(result)
        assert fake_token not in result_str

    def test_github_token_never_in_error_response(self):
        """Token must not leak even when GitHub returns an error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        fake_token = "ghp_anothersecrettoken456"

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with patch("app.services.github_service.get_settings") as mock_settings:
                mock_settings.return_value.github_token = fake_token
                result = get_github_file_content("owner", "repo", "main.py")

        result_str = str(result)
        assert fake_token not in result_str


# ===========================================================================
# 3. File tree endpoint — GET /files
# ===========================================================================

class TestListRepositoryFiles:

    def _call(self, repository_id: str, supabase_rows: list[dict], repo: dict = None):
        """Call list_repository_files with a mocked Supabase."""
        repo = repo or FAKE_REPO

        def mock_get_supabase():
            return _supabase_files_mock(supabase_rows)

        with patch.object(files_api, "get_repository", return_value=repo), \
             patch.object(files_api, "get_supabase", mock_get_supabase), \
             patch.object(files_api, "_get_analysis_categories", return_value={}):
            return files_api.list_repository_files(repository_id)

    def test_returns_file_tree(self):
        rows = [
            {"file_path": "src/main.py", "file_name": "main.py", "extension": ".py",
             "language": "Python", "file_size": 1234, "is_directory": False},
            {"file_path": "README.md", "file_name": "README.md", "extension": ".md",
             "language": "Markdown", "file_size": 500, "is_directory": False},
        ]
        result = self._call(REPO_ID, rows)
        assert result.repository_id == REPO_ID
        assert len(result.files) == 2
        paths = [f.path for f in result.files]
        assert "src/main.py" in paths
        assert "README.md" in paths

    def test_forbidden_files_excluded(self):
        rows = [
            {"file_path": "src/app.py", "file_name": "app.py", "extension": ".py",
             "language": "Python", "file_size": 100, "is_directory": False},
            {"file_path": ".env", "file_name": ".env", "extension": "",
             "language": None, "file_size": 50, "is_directory": False},
            {"file_path": "id_rsa", "file_name": "id_rsa", "extension": "",
             "language": None, "file_size": 1700, "is_directory": False},
            {"file_path": ".npmrc", "file_name": ".npmrc", "extension": "",
             "language": None, "file_size": 100, "is_directory": False},
        ]
        result = self._call(REPO_ID, rows)
        names = [f.file_name for f in result.files]
        assert ".env" not in names
        assert "id_rsa" not in names
        assert ".npmrc" not in names
        assert "app.py" in names

    def test_binary_extensions_excluded(self):
        rows = [
            {"file_path": "src/main.py", "file_name": "main.py", "extension": ".py",
             "language": "Python", "file_size": 100, "is_directory": False},
            {"file_path": "assets/logo.png", "file_name": "logo.png", "extension": ".png",
             "language": None, "file_size": 5000, "is_directory": False},
            {"file_path": "dist/app.exe", "file_name": "app.exe", "extension": ".exe",
             "language": None, "file_size": 100000, "is_directory": False},
        ]
        result = self._call(REPO_ID, rows)
        names = [f.file_name for f in result.files]
        assert "logo.png" not in names
        assert "app.exe" not in names
        assert "main.py" in names

    def test_repository_not_found_raises_404(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                files_api.list_repository_files("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_total_files_count_correct(self):
        rows = [
            {"file_path": f"file{i}.py", "file_name": f"file{i}.py",
             "extension": ".py", "language": "Python", "file_size": 100,
             "is_directory": False}
            for i in range(5)
        ]
        result = self._call(REPO_ID, rows)
        assert result.total_files == 5

    def test_empty_repository_returns_empty_list(self):
        result = self._call(REPO_ID, [])
        assert result.files == []
        assert result.total_files == 0

    def test_analysis_category_merged(self):
        rows = [
            {"file_path": "backend/app/main.py", "file_name": "main.py",
             "extension": ".py", "language": "Python", "file_size": 500,
             "is_directory": False},
        ]
        categories = {"backend/app/main.py": "entry_point"}

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO), \
             patch.object(files_api, "get_supabase", return_value=_supabase_files_mock(rows)), \
             patch.object(files_api, "_get_analysis_categories", return_value=categories):
            result = files_api.list_repository_files(REPO_ID)

        assert result.files[0].category == "entry_point"

    def test_env_local_excluded(self):
        rows = [
            {"file_path": ".env.local", "file_name": ".env.local", "extension": "",
             "language": None, "file_size": 50, "is_directory": False},
        ]
        result = self._call(REPO_ID, rows)
        assert len(result.files) == 0


# ===========================================================================
# 4. File content endpoint — GET /files/content
# ===========================================================================

class TestGetFileContent:

    def _call(self, repository_id: str, path: str, repo: dict = None,
              github_result: dict = None):
        repo = repo or FAKE_REPO
        if github_result is None:
            content = "print('hello')\n"
            github_result = {
                "content": content,
                "file_size": len(content),
                "is_binary": False,
                "truncated": False,
                "error": None,
            }

        with patch.object(files_api, "get_repository", return_value=repo), \
             patch.object(files_api, "get_github_file_content", return_value=github_result):
            return files_api.get_file_content(repository_id, path)

    def test_text_file_returned(self):
        result = self._call(REPO_ID, "backend/app/main.py")
        assert result.path == "backend/app/main.py"
        assert result.file_name == "main.py"
        assert result.content == "print('hello')\n"
        assert result.is_binary is False
        assert result.error is None

    def test_language_detected(self):
        result = self._call(REPO_ID, "backend/app/main.py")
        assert result.language == "Python"

    def test_typescript_language_detected(self):
        result = self._call(REPO_ID, "frontend/src/App.tsx")
        assert result.language == "TypeScript"

    def test_traversal_path_rejected(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content(REPO_ID, "../etc/passwd")

        assert exc_info.value.status_code == 400

    def test_env_file_rejected(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content(REPO_ID, ".env")

        assert exc_info.value.status_code == 400

    def test_id_rsa_rejected(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content(REPO_ID, "id_rsa")

        assert exc_info.value.status_code == 400

    def test_pem_file_rejected(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content(REPO_ID, "cert.pem")

        assert exc_info.value.status_code == 400

    def test_binary_extension_rejected_early(self):
        """Binary extensions never reach GitHub API."""
        with patch.object(files_api, "get_repository", return_value=FAKE_REPO), \
             patch.object(files_api, "get_github_file_content") as mock_gh:
            result = files_api.get_file_content(REPO_ID, "image.png")

        assert result.is_binary is True
        mock_gh.assert_not_called()

    def test_png_rejected(self):
        result = self._call.__wrapped__(REPO_ID, "logo.png") if hasattr(
            self._call, "__wrapped__") else None

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO), \
             patch.object(files_api, "get_github_file_content") as mock_gh:
            result = files_api.get_file_content(REPO_ID, "logo.png")

        assert result.is_binary is True
        mock_gh.assert_not_called()

    def test_repository_not_found_raises_404(self):
        from fastapi import HTTPException

        with patch.object(files_api, "get_repository", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content("nonexistent", "main.py")

        assert exc_info.value.status_code == 404

    def test_missing_file_returns_error_not_exception(self):
        github_result = {
            "content": None,
            "file_size": 0,
            "is_binary": False,
            "truncated": False,
            "error": "File not found in repository.",
        }
        result = self._call(REPO_ID, "no/such/file.py", github_result=github_result)
        assert result.error == "File not found in repository."
        assert result.content is None

    def test_oversized_file_returns_error(self):
        github_result = {
            "content": None,
            "file_size": 600_000,
            "is_binary": False,
            "truncated": False,
            "error": "File too large to preview.",
        }
        result = self._call(REPO_ID, "huge.py", github_result=github_result)
        assert result.error == "File too large to preview."

    def test_binary_content_from_github_handled(self):
        github_result = {
            "content": None,
            "file_size": 1024,
            "is_binary": True,
            "truncated": False,
            "error": "Binary or unsupported file type.",
        }
        result = self._call(REPO_ID, "data.wasm", github_result=github_result)
        assert result.is_binary is True
        assert result.content is None

    # --- Repository isolation ------------------------------------------------

    def test_repo_owner_name_used_for_github_request(self):
        """The GitHub request uses owner/name from the stored repo record, not from path."""
        call_args = {}

        def capture_call(owner, repo, path):
            call_args["owner"] = owner
            call_args["repo"] = repo
            call_args["path"] = path
            return {
                "content": "# code\n", "file_size": 7,
                "is_binary": False, "truncated": False, "error": None,
            }

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO), \
             patch.object(files_api, "get_github_file_content", side_effect=capture_call):
            files_api.get_file_content(REPO_ID, "src/app.py")

        assert call_args["owner"] == "testowner"
        assert call_args["repo"] == "testrepo"

    def test_arbitrary_owner_cannot_be_injected_via_path(self):
        """The path param cannot override the repository owner derived from the DB record."""
        call_args = {}

        def capture_call(owner, repo, path):
            call_args["owner"] = owner
            call_args["repo"] = repo
            return {
                "content": "# code\n", "file_size": 7,
                "is_binary": False, "truncated": False, "error": None,
            }

        with patch.object(files_api, "get_repository", return_value=FAKE_REPO), \
             patch.object(files_api, "get_github_file_content", side_effect=capture_call):
            files_api.get_file_content(REPO_ID, "src/app.py")

        # Must always use the stored owner, never user-supplied data
        assert call_args["owner"] == FAKE_REPO["owner"]
        assert call_args["repo"] == FAKE_REPO["name"]

    def test_missing_owner_raises_500(self):
        from fastapi import HTTPException

        incomplete_repo = {**FAKE_REPO, "owner": "", "name": ""}

        with patch.object(files_api, "get_repository", return_value=incomplete_repo):
            with pytest.raises(HTTPException) as exc_info:
                files_api.get_file_content(REPO_ID, "main.py")

        assert exc_info.value.status_code == 500


# ===========================================================================
# 5. _get_analysis_categories helper
# ===========================================================================

class TestGetAnalysisCategories:

    def test_returns_empty_dict_when_no_analysis(self):
        supabase = _supabase_files_mock([])
        with patch.object(files_api, "get_supabase", return_value=supabase):
            result = files_api._get_analysis_categories(REPO_ID)
        assert result == {}

    def test_returns_categories_from_important_files(self):
        analysis_row = {
            "important_files": [
                {"file_path": "src/main.py", "category": "entry_point"},
                {"file_path": "config.yml", "category": "configuration"},
            ],
            "entry_points": [],
        }
        supabase = _supabase_files_mock([analysis_row])
        with patch.object(files_api, "get_supabase", return_value=supabase):
            result = files_api._get_analysis_categories(REPO_ID)
        assert result["src/main.py"] == "entry_point"
        assert result["config.yml"] == "configuration"

    def test_entry_points_fallback_category(self):
        analysis_row = {
            "important_files": [],
            "entry_points": [
                {"file_path": "main.go", "kind": "web server"},
            ],
        }
        supabase = _supabase_files_mock([analysis_row])
        with patch.object(files_api, "get_supabase", return_value=supabase):
            result = files_api._get_analysis_categories(REPO_ID)
        assert result["main.go"] == "entry_point"

    def test_returns_empty_dict_on_error(self):
        supabase = MagicMock()
        supabase.table.side_effect = Exception("db error")
        with patch.object(files_api, "get_supabase", return_value=supabase):
            result = files_api._get_analysis_categories(REPO_ID)
        assert result == {}


# ===========================================================================
# 6. Security invariants
# ===========================================================================

class TestSecurityInvariants:

    def test_forbidden_filenames_set_completeness(self):
        """_CONTENT_FORBIDDEN_FILENAMES includes all critical secret files."""
        critical = {".env", "id_rsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc"}
        missing = critical - _CONTENT_FORBIDDEN_FILENAMES
        assert not missing, f"Missing from _CONTENT_FORBIDDEN_FILENAMES: {missing}"

    def test_binary_extensions_includes_common_media(self):
        expected = {".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".wasm",
                    ".mp3", ".mp4", ".zip", ".tar", ".gz", ".pdf"}
        missing = expected - BINARY_EXTENSIONS
        assert not missing, f"Missing from BINARY_EXTENSIONS: {missing}"

    def test_validate_file_path_is_deterministic(self):
        """Same input always produces same output."""
        for _ in range(10):
            ok1, _ = validate_file_path("src/main.py")
            ok2, _ = validate_file_path("../bad")
            assert ok1 is True
            assert ok2 is False
