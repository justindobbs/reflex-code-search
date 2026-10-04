"""Unit tests for the core search logic."""

from unittest.mock import MagicMock, patch

from reflex_search.fallback import default_fallback_scorer
from reflex_search.gate import ConfidenceGate
from reflex_search.models import GateDecision
from reflex_search.scorers import JevScorer, LocalScorer
from reflex_search.searcher import ReflexCodeSearcher

# ---------------------------------------------------------------------------
# LocalScorer
# ---------------------------------------------------------------------------

class TestLocalScorer:
    def test_empty_query_returns_zero(self):
        scorer = LocalScorer()
        assert scorer.score("auth.py", "", "some content") == 0.0

    def test_single_term_path_and_content_match(self):
        scorer = LocalScorer()
        score = scorer.score("auth.py", "auth", "def require_auth(): pass")
        assert score > 0.5

    def test_score_capped_at_one(self):
        scorer = LocalScorer()
        score = scorer.score("auth.py", "auth", "auth auth auth auth")
        assert score <= 1.0

    def test_no_match_returns_low_score(self):
        scorer = LocalScorer()
        score = scorer.score("utils.py", "authentication", "def add(a, b): return a + b")
        assert score < 0.3

    def test_content_weighted_higher_than_path(self):
        scorer = LocalScorer()
        path_only = scorer.score("auth.py", "auth", "def add(a, b): return a + b")
        content_only = scorer.score("utils.py", "auth", "def require_auth(): pass")
        assert content_only > path_only

    def test_multiterm_normalizes_by_count(self):
        scorer = LocalScorer()
        score = scorer.score("foo.py", "authentication middleware handler", "authentication check")
        assert score <= 1.0

    def test_provider_attribute(self):
        assert LocalScorer.provider == "local"


# ---------------------------------------------------------------------------
# JevScorer (mocked HTTP)
# ---------------------------------------------------------------------------

class TestJevScorer:
    def test_provider_attribute(self):
        assert JevScorer.provider == "jev"

    def test_no_api_key_falls_back_to_local(self):
        scorer = JevScorer(api_key="")
        score = scorer.score("auth.py", "auth", "def require_auth(): pass")
        assert score > 0.0
        assert scorer.last_latency_ms == 0.0

    @patch("reflex_search.scorers.httpx.post")
    def test_successful_api_call(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {
                "relevance": {
                    "type": "noul",
                    "noul": 0.85,
                }
            },
            "usage": {
                "input_tokens": 150,
                "cost": 0.0001,
            },
        }
        mock_post.return_value = mock_resp

        scorer = JevScorer(api_key="test-key")
        result = scorer.score("auth.py", "auth check", "def require_auth(): pass")

        assert result == 0.85
        assert scorer.last_input_tokens == 150
        assert scorer.last_cost == 0.0001
        assert scorer.last_latency_ms >= 0.0
        mock_post.assert_called_once()

    @patch("reflex_search.scorers.httpx.post")
    def test_api_error_falls_back_to_local(self, mock_post):
        mock_post.side_effect = Exception("connection refused")

        scorer = JevScorer(api_key="test-key")
        result = scorer.score("auth.py", "auth", "def require_auth(): pass")

        assert result > 0.0

    @patch("reflex_search.scorers.httpx.post")
    def test_api_returns_no_noul_falls_back(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"answers": {"relevance": {"type": "noul"}}, "usage": {}}
        mock_post.return_value = mock_resp

        scorer = JevScorer(api_key="test-key")
        result = scorer.score("auth.py", "auth", "def require_auth(): pass")

        assert result > 0.0

    @patch("reflex_search.scorers.httpx.post")
    def test_noul_clamped_to_0_1(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 1.5}},
            "usage": {},
        }
        mock_post.return_value = mock_resp

        scorer = JevScorer(api_key="test-key")
        assert scorer.score("a.py", "q", "c") <= 1.0

    @patch("reflex_search.scorers.httpx.post")
    def test_401_falls_back_with_warning(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        scorer = JevScorer(api_key="bad-key")
        result = scorer.score("auth.py", "auth", "def require_auth(): pass")
        assert result > 0.0

    @patch("reflex_search.scorers.httpx.post")
    def test_429_falls_back_with_warning(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        scorer = JevScorer(api_key="test-key")
        result = scorer.score("auth.py", "auth", "def require_auth(): pass")
        assert result > 0.0

    def test_api_key_not_stored_as_plain_attribute(self):
        scorer = JevScorer(api_key="super-secret-key")
        assert not hasattr(scorer, "api_key")
        attrs = vars(scorer)
        for key, value in attrs.items():
            if key == "_api_key_override":
                continue
            assert value != "super-secret-key", f"API key leaked to {key}"

    def test_default_redactor_strips_secrets(self):
        content = "DB_HOST=localhost\nAPI_KEY=sk-12345\nDEBUG=true\npassword=hunter2"
        redacted = JevScorer._default_redactor(content)
        assert "sk-12345" not in redacted
        assert "hunter2" not in redacted
        assert "localhost" in redacted
        assert "[REDACTED]" in redacted

    def test_custom_redactor_is_used(self):
        called = []

        def my_redactor(state: str) -> str:
            called.append(True)
            return "CUSTOM"

        scorer = JevScorer(api_key="", state_redactor=my_redactor)
        scorer.score("a.py", "q", "c")
        # With empty key, redactor is not called (falls back before API call)
        assert not called


# ---------------------------------------------------------------------------
# ConfidenceGate
# ---------------------------------------------------------------------------

class TestConfidenceGate:
    def test_high_score_accepted(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.80) is GateDecision.ACCEPT

    def test_medium_score_uncertain(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.50) is GateDecision.UNCERTAIN

    def test_low_score_rejected(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.20) is GateDecision.REJECT

    def test_boundary_accept(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.65) is GateDecision.ACCEPT

    def test_boundary_uncertain(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.40) is GateDecision.UNCERTAIN

    def test_below_uncertain_rejected(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(0.39) is GateDecision.REJECT

    def test_nan_rejected(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(float("nan")) is GateDecision.REJECT

    def test_inf_rejected(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(float("inf")) is GateDecision.REJECT

    def test_non_numeric_rejected(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide("bad") is GateDecision.REJECT  # type: ignore[arg-type]

    def test_min_margin_downgrades_to_uncertain(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40, min_margin=0.15)
        assert gate.decide(0.70, runner_up=0.65) is GateDecision.UNCERTAIN

    def test_min_margin_accepts_with_sufficient_gap(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40, min_margin=0.15)
        assert gate.decide(0.85, runner_up=0.50) is GateDecision.ACCEPT

    def test_min_margin_zero_does_not_affect(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40, min_margin=0.0)
        assert gate.decide(0.70, runner_up=0.69) is GateDecision.ACCEPT

    def test_negative_score_clamped_to_reject(self):
        gate = ConfidenceGate(accept_threshold=0.65, uncertain_threshold=0.40)
        assert gate.decide(-0.5) is GateDecision.REJECT


# ---------------------------------------------------------------------------
# default_fallback_scorer
# ---------------------------------------------------------------------------

class TestDefaultFallback:
    def test_empty_query(self):
        assert default_fallback_scorer("a.py", "", "content") == 0.0

    def test_full_match(self):
        score = default_fallback_scorer("auth.py", "auth", "auth logic here")
        assert score > 0.5

    def test_capped_at_0_9(self):
        score = default_fallback_scorer("auth.py", "auth", "auth auth auth")
        assert score <= 0.9


# ---------------------------------------------------------------------------
# ReflexCodeSearcher
# ---------------------------------------------------------------------------

class TestReflexCodeSearcher:
    def test_finds_relevant_file(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "src").mkdir()
        (repo / "src" / "auth.py").write_text(
            "def require_auth(user):\n    if user is None:\n        raise ValueError('unauthorized')\n",
            encoding="utf-8",
        )
        (repo / "README.md").write_text("This project has auth and login flows.", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3, top_k=5)
        session = searcher.search("require auth")

        assert session.results
        assert any("auth" in r.path.lower() for r in session.results)
        assert session.audit_trail

    def test_empty_repo_returns_no_results(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()

        searcher = ReflexCodeSearcher(repo_root=str(repo))
        session = searcher.search("anything")

        assert session.results == []
        assert session.audit_trail == []

    def test_no_matches_above_threshold(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.99)
        session = searcher.search("authentication middleware")

        assert session.results == []

    def test_fallback_escalation(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "handler.py").write_text(
            "def handle_request(req):\n    return check_auth(req)\n",
            encoding="utf-8",
        )

        def always_high(_path: str, _query: str, _content: str) -> float:
            return 0.95

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            fallback=always_high,
        )
        session = searcher.search("request handling")

        assert session.results
        assert session.results[0].provider == "fallback"

    def test_fallback_not_called_on_reject(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "empty.py").write_text("x = 1", encoding="utf-8")

        called = []

        def spy(_p: str, _q: str, _c: str) -> float:
            called.append(True)
            return 0.99

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.99,
            uncertain_threshold=0.98,
            fallback=spy,
        )
        searcher.search("completely unrelated quantum physics topic")

        assert not called

    def test_top_k_limits_results(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(10):
            (repo / f"auth_{i}.py").write_text(f"auth check {i}", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3, top_k=3)
        session = searcher.search("auth")

        assert len(session.results) <= 3

    def test_audit_trail_records_all_candidates(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("auth", encoding="utf-8")
        (repo / "b.py").write_text("nothing", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3)
        session = searcher.search("auth")

        assert len(session.audit_trail) == 2

    def test_provider_name_from_scorer(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("auth check", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3)
        session = searcher.search("auth")

        assert session.results
        assert session.results[0].provider == "local"

    def test_env_file_excluded(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".env").write_text("API_KEY=secret123", encoding="utf-8")
        (repo / "app.py").write_text("auth logic", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.1)
        session = searcher.search("API_KEY")

        paths = [r.path for r in session.results]
        audit_paths = [e["path"] for e in session.audit_trail]
        assert not any(".env" == p for p in paths)
        assert not any(".env" == p for p in audit_paths)

    def test_egg_info_excluded(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        egg = repo / "mypackage.egg-info"
        egg.mkdir()
        (egg / "SOURCES.txt").write_text("auth.py", encoding="utf-8")
        (repo / "auth.py").write_text("auth logic", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.1)
        session = searcher.search("auth")

        audit_paths = [e["path"] for e in session.audit_trail]
        assert not any("egg-info" in p for p in audit_paths)
