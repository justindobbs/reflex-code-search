"""Tests for the MCP server module.

These tests validate the tool schema and result structure without requiring
the ``mcp`` package to be installed — the server import is guarded and
tested for a clean ImportError when the dependency is missing.
"""

from __future__ import annotations

import importlib

import pytest


def _mcp_available() -> bool:
    """Check whether the mcp package is installed."""
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# ImportError when mcp is not installed
# ---------------------------------------------------------------------------

class TestMcpImportGuard:
    def test_import_error_without_mcp(self):
        """Importing mcp_server raises ImportError with guidance when mcp is missing."""
        if _mcp_available():
            pytest.skip("mcp is installed — cannot test missing-dep path")

        with pytest.raises(ImportError, match="pip install reflex-code-search\\[mcp\\]"):
            importlib.import_module("reflex_search.mcp_server")


# ---------------------------------------------------------------------------
# Tool function tests (only when mcp is installed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _mcp_available(), reason="mcp not installed")
class TestSearchCodebaseTool:
    def test_returns_dict_with_expected_keys(self, tmp_path):
        from reflex_search.mcp_server import search_codebase

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text(
            "def require_auth(): pass", encoding="utf-8"
        )

        result = search_codebase(
            query="auth",
            repo_root=str(repo),
            top_k=5,
            threshold=0.30,
        )

        assert isinstance(result, dict)
        assert "query" in result
        assert "repo_root" in result
        assert "results" in result
        assert "telemetry" in result
        assert result["query"] == "auth"

    def test_results_have_correct_shape(self, tmp_path):
        from reflex_search.mcp_server import search_codebase

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text(
            "def require_auth(): pass", encoding="utf-8"
        )

        result = search_codebase(
            query="auth",
            repo_root=str(repo),
            threshold=0.30,
        )

        for r in result["results"]:
            assert "path" in r
            assert "score" in r
            assert "provider" in r
            assert "reason" in r
            assert "excerpt" in r
            assert isinstance(r["score"], float)

    def test_telemetry_fields(self, tmp_path):
        from reflex_search.mcp_server import search_codebase

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text(
            "def require_auth(): pass", encoding="utf-8"
        )

        result = search_codebase(
            query="auth",
            repo_root=str(repo),
            threshold=0.30,
        )

        t = result["telemetry"]
        assert t is not None
        assert "files_scanned" in t
        assert "accepted" in t
        assert "rejected" in t
        assert "fallback_calls" in t

    def test_empty_repo_returns_no_results(self, tmp_path):
        from reflex_search.mcp_server import search_codebase

        repo = tmp_path / "empty"
        repo.mkdir()

        result = search_codebase(
            query="anything",
            repo_root=str(repo),
        )

        assert result["results"] == []

    def test_live_and_smart_fallback_mutual_exclusion(self, tmp_path):
        from reflex_search.mcp_server import search_codebase

        result = search_codebase(
            query="test",
            repo_root=str(tmp_path),
            live=True,
            smart_fallback=True,
        )

        assert "error" in result
