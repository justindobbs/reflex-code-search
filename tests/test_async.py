"""Tests for async Jev scoring and async search methods."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from reflex_search.scorers import AsyncJevScorer
from reflex_search.searcher import ReflexCodeSearcher


# ---------------------------------------------------------------------------
# AsyncJevScorer
# ---------------------------------------------------------------------------

class TestAsyncJevScorer:
    def test_provider_attribute(self):
        assert AsyncJevScorer.provider == "jev-async"

    def test_no_api_key_falls_back_to_local(self):
        scorer = AsyncJevScorer(api_key="")
        result = asyncio.run(scorer.score("auth.py", "auth", "def require_auth(): pass"))
        assert result > 0.0
        assert scorer.last_latency_ms == 0.0

    @patch("reflex_search.scorers.httpx.AsyncClient")
    def test_successful_api_call(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.85}},
            "usage": {"input_tokens": 150, "cost": 0.0001},
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        scorer = AsyncJevScorer(api_key="test-key")
        result = asyncio.run(scorer.score("auth.py", "auth check", "def require_auth(): pass"))

        assert result == 0.85
        assert scorer.last_input_tokens == 150
        assert scorer.last_cost == 0.0001
        assert scorer.last_latency_ms >= 0.0

    @patch("reflex_search.scorers.httpx.AsyncClient")
    def test_api_error_falls_back_to_local(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        scorer = AsyncJevScorer(api_key="test-key")
        result = asyncio.run(scorer.score("auth.py", "auth", "def require_auth(): pass"))
        assert result > 0.0

    @patch("reflex_search.scorers.httpx.AsyncClient")
    def test_401_falls_back(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        scorer = AsyncJevScorer(api_key="bad-key")
        result = asyncio.run(scorer.score("auth.py", "auth", "def require_auth(): pass"))
        assert result > 0.0

    @patch("reflex_search.scorers.httpx.AsyncClient")
    def test_429_falls_back(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        scorer = AsyncJevScorer(api_key="test-key")
        result = asyncio.run(scorer.score("auth.py", "auth", "def require_auth(): pass"))
        assert result > 0.0


# ---------------------------------------------------------------------------
# async_search
# ---------------------------------------------------------------------------

def _mock_async_scorer(noul_value: float = 0.80):
    """Create an AsyncJevScorer mock that returns a fixed noul value."""
    scorer = AsyncJevScorer(api_key="test-key")

    async def fake_score(file_path, query, content):
        scorer.last_latency_ms = 50.0
        scorer.last_cost = 0.0001
        scorer.last_input_tokens = 100
        return noul_value

    scorer.score = fake_score  # type: ignore[assignment]
    return scorer


class TestAsyncSearch:
    def test_async_search_returns_results(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")
        (repo / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.30,
            uncertain_threshold=0.10,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.80)
        session = asyncio.run(
            searcher.async_search("auth", async_scorer=mock_scorer)
        )

        assert session.results
        assert session.query == "auth"

    def test_async_search_audit_trail_has_async_entries(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "handler.py").write_text(
            "def handle_request(req):\n    return check_auth(req)\n",
            encoding="utf-8",
        )

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.95)
        session = asyncio.run(
            searcher.async_search("request handling", async_scorer=mock_scorer)
        )

        async_steps = [s for s in session.audit_trail if s["provider"] == "jev-async"]
        assert async_steps

    def test_async_search_empty_repo(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()

        searcher = ReflexCodeSearcher(repo_root=str(repo))
        session = asyncio.run(searcher.async_search("anything"))

        assert session.results == []

    def test_async_search_telemetry(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.95)
        session = asyncio.run(
            searcher.async_search("auth", async_scorer=mock_scorer)
        )

        t = session.telemetry
        assert t is not None
        assert t.files_scanned > 0


# ---------------------------------------------------------------------------
# async_search_two_pass
# ---------------------------------------------------------------------------

class TestAsyncSearchTwoPass:
    def test_two_pass_returns_results(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(5):
            (repo / f"file_{i}.py").write_text(f"content {i}", encoding="utf-8")

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.30,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.80)
        session = asyncio.run(
            searcher.async_search_two_pass(
                "content",
                async_scorer=mock_scorer,
                shortlist_size=3,
            )
        )

        # Should have prefilter steps for all 5 files
        prefilter = [s for s in session.audit_trail if s["decision"] == "prefilter"]
        assert len(prefilter) == 5

        # Jev-async steps only for shortlisted 3
        jev_steps = [s for s in session.audit_trail if s["provider"] == "jev-async"]
        assert len(jev_steps) == 3

    def test_two_pass_telemetry(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.30,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.85)
        session = asyncio.run(
            searcher.async_search_two_pass(
                "auth",
                async_scorer=mock_scorer,
                shortlist_size=5,
            )
        )

        t = session.telemetry
        assert t is not None
        assert t.files_scanned > 0
        assert t.total_cost > 0

    def test_two_pass_concurrency_limit(self, tmp_path):
        """Verify that concurrency parameter is respected (no crash with limit=1)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(5):
            (repo / f"file_{i}.py").write_text(f"content {i}", encoding="utf-8")

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.30,
            top_k=5,
        )
        mock_scorer = _mock_async_scorer(0.80)
        session = asyncio.run(
            searcher.async_search_two_pass(
                "content",
                async_scorer=mock_scorer,
                shortlist_size=3,
                concurrency=1,
            )
        )

        jev_steps = [s for s in session.audit_trail if s["provider"] == "jev-async"]
        assert len(jev_steps) == 3


# ---------------------------------------------------------------------------
# CLI --async flag
# ---------------------------------------------------------------------------

class TestCliAsync:
    def test_async_requires_live_or_smart_fallback(self):
        from typer.testing import CliRunner

        from reflex_search.cli import app

        result = CliRunner().invoke(app, ["query", ".", "--async"])
        assert result.exit_code == 1
        assert "--async requires" in result.output
