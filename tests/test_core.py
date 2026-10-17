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

    def test_exact_symbols_boost_implementation_matches(self):
        scorer = LocalScorer()
        query = "Where are Group and resolve_command implemented?"
        exact_match = scorer.score(
            "core.py",
            query,
            "class Group:\n    def resolve_command(self):\n        pass\n",
        )
        incidental_match = scorer.score(
            "helpers.py",
            query,
            "def group_related_command():\n    return 'resolve command'\n",
        )
        assert exact_match > incidental_match

    def test_exact_symbol_references_boost_implementation_usage(self):
        scorer = LocalScorer()
        query = "Where is HelpFormatter implemented and used?"
        usage_match = scorer.score(
            "core.py",
            query,
            "class Command:\n    formatter = HelpFormatter()\n",
        )
        unrelated = scorer.score(
            "core.py",
            query,
            "class Command:\n    formatter = TextFormatter()\n",
        )
        assert usage_match > unrelated

    def test_multiterm_normalizes_by_count(self):
        scorer = LocalScorer()
        score = scorer.score("foo.py", "authentication middleware handler", "authentication check")
        assert score <= 1.0

    def test_provider_attribute(self):
        assert LocalScorer.provider == "local"

    def test_synonym_expansion_adds_related_terms(self):
        scorer = LocalScorer()
        expanded = scorer._expand_synonyms(["collect"])
        assert "discover" in expanded
        assert "walk" in expanded
        assert "scan" in expanded
        assert "collect" in expanded

    def test_synonym_expansion_no_duplicates(self):
        scorer = LocalScorer()
        expanded = scorer._expand_synonyms(["collect", "discover"])
        assert len(expanded) == len(set(expanded))

    def test_synonym_expansion_unknown_term_unchanged(self):
        scorer = LocalScorer()
        expanded = scorer._expand_synonyms(["foobar"])
        assert expanded == ["foobar"]

    def test_synonym_expansion_improves_conceptual_query(self):
        scorer = LocalScorer()
        # "collected" contains "collect" which expands to walk/scan/discover/find
        # file_collector.py's content uses "walk" and "scan" concepts
        content = '"""File discovery for repository scanning."""\ndef collect_files(repo_root):\n    pass\n'
        score_with_synonyms = scorer.score("file_collector.py", "How are files collected", content)
        assert score_with_synonyms > 0.3, f"Expected >0.3, got {score_with_synonyms}"

    def test_docstring_boosting_increases_score(self):
        scorer = LocalScorer()
        content_with_doc = '"""File discovery for repository scanning."""\ndef other_func():\n    pass\n'
        content_without_doc = "def other_func():\n    pass\n"
        score_with = scorer.score("utils.py", "file discovery scanning", content_with_doc)
        score_without = scorer.score("utils.py", "file discovery scanning", content_without_doc)
        assert score_with > score_without

    def test_docstring_boosting_python_module_docstring(self):
        scorer = LocalScorer()
        content = '"""Three-way confidence gate for the REFLEX search loop."""\nclass ConfidenceGate:\n    pass\n'
        score = scorer.score("gate.py", "confidence gate", content)
        assert score > 0.4, f"Expected >0.4, got {score}"

    def test_content_preview_8000_chars(self):
        scorer = LocalScorer()
        # Place relevant content at position 5000 (beyond old 4000 limit)
        content = "x = 1\n" * 800 + "authentication middleware check\n"
        score = scorer.score("deep.py", "authentication middleware", content)
        assert score > 0.0


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

class TestJevFallback:
    @patch("reflex_search.scorers.httpx.post")
    def test_delegates_to_jev_scorer(self, mock_post):
        from reflex_search.fallback import JevFallback

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.90}},
            "usage": {"input_tokens": 200, "cost": 0.0002},
        }
        mock_post.return_value = mock_resp

        fb = JevFallback(api_key="test-key")
        score = fb("auth.py", "auth check", "def require_auth(): pass")

        assert score == 0.9
        assert fb.last_input_tokens == 200
        assert fb.last_cost == 0.0002
        assert fb.last_latency_ms >= 0.0
        mock_post.assert_called_once()

    def test_no_api_key_falls_back_to_local(self):
        from reflex_search.fallback import JevFallback

        fb = JevFallback(api_key="")
        score = fb("auth.py", "auth", "def require_auth(): pass")
        assert score > 0.0
        assert fb.last_latency_ms == 0.0

    def test_provider_attribute(self):
        from reflex_search.fallback import JevFallback

        assert JevFallback.provider == "jev-fallback"

    @patch("reflex_search.scorers.httpx.post")
    def test_only_called_for_uncertain_candidates(self, mock_post, tmp_path):
        from reflex_search.fallback import JevFallback

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.95}},
            "usage": {"input_tokens": 100, "cost": 0.0001},
        }
        mock_post.return_value = mock_resp

        repo = tmp_path / "repo"
        repo.mkdir()
        # File that will score high locally (accepted, no fallback)
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")
        # File that will score zero locally (rejected, no fallback)
        (repo / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

        fb = JevFallback(api_key="test-key")
        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            fallback=fb,
        )
        session = searcher.search("require auth")

        # auth.py should be uncertain (local score < 0.90) → fallback called
        # math.py should be rejected (local score ~ 0) → fallback NOT called
        fb_steps = [s for s in session.audit_trail if s["provider"] == "jev-fallback"]
        reject_steps = [s for s in session.audit_trail if s["decision"] == "reject" and s["provider"] == "local"]
        assert len(fb_steps) >= 1
        assert len(reject_steps) >= 1

    @patch("reflex_search.scorers.httpx.post")
    def test_telemetry_in_audit_trail(self, mock_post, tmp_path):
        from reflex_search.fallback import JevFallback

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.80}},
            "usage": {"input_tokens": 150, "cost": 0.00015},
        }
        mock_post.return_value = mock_resp

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "handler.py").write_text(
            "def handle_request(req):\n    return check_auth(req)\n",
            encoding="utf-8",
        )

        fb = JevFallback(api_key="test-key")
        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            fallback=fb,
        )
        session = searcher.search("request handling")

        fb_steps = [s for s in session.audit_trail if s["provider"] == "jev-fallback"]
        assert fb_steps
        step = fb_steps[0]
        assert "latency_ms" in step
        assert "cost" in step
        assert "input_tokens" in step
        assert step["cost"] == 0.00015
        assert step["input_tokens"] == 150


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

    def test_telemetry_local_only(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")
        (repo / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3)
        session = searcher.search("auth")

        t = session.telemetry
        assert t is not None
        assert t.files_scanned == 2
        assert t.accepted + t.uncertain + t.rejected == 2
        assert t.fallback_calls == 0
        assert t.total_cost == 0.0
        assert t.total_tokens == 0

    def test_telemetry_with_fallback(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "handler.py").write_text(
            "def handle_request(req):\n    return check_auth(req)\n",
            encoding="utf-8",
        )

        def always_high(_p: str, _q: str, _c: str) -> float:
            return 0.95

        searcher = ReflexCodeSearcher(
            repo_root=str(repo),
            accept_threshold=0.90,
            uncertain_threshold=0.01,
            fallback=always_high,
        )
        session = searcher.search("request handling")

        t = session.telemetry
        assert t is not None
        assert t.fallback_calls >= 1

    def test_telemetry_empty_repo(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()

        searcher = ReflexCodeSearcher(repo_root=str(repo))
        session = searcher.search("anything")

        t = session.telemetry
        assert t is not None
        assert t.files_scanned == 0
        assert t.accepted == 0
        assert t.rejected == 0

    @patch("reflex_search.scorers.httpx.post")
    def test_two_pass_calls_jev_only_for_shortlist(self, mock_post, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.80}},
            "usage": {"input_tokens": 100, "cost": 0.0001},
        }
        mock_post.return_value = mock_resp

        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(10):
            (repo / f"file_{i}.py").write_text(f"content {i}", encoding="utf-8")

        from reflex_search.scorers import JevScorer

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3)
        session = searcher.search_two_pass(
            "content",
            jev_scorer=JevScorer(api_key="test-key"),
            shortlist_size=3,
        )

        # Jev should only be called for 3 shortlisted files, not all 10
        jev_steps = [s for s in session.audit_trail if s["provider"] == "jev"]
        assert len(jev_steps) == 3
        # All 10 should appear in prefilter
        prefilter_steps = [s for s in session.audit_trail if s["decision"] == "prefilter"]
        assert len(prefilter_steps) == 10

    @patch("reflex_search.scorers.httpx.post")
    def test_two_pass_telemetry(self, mock_post, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "answers": {"relevance": {"type": "noul", "noul": 0.85}},
            "usage": {"input_tokens": 120, "cost": 0.00012},
        }
        mock_post.return_value = mock_resp

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text("def require_auth(): pass", encoding="utf-8")
        (repo / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

        from reflex_search.scorers import JevScorer

        searcher = ReflexCodeSearcher(repo_root=str(repo), accept_threshold=0.3)
        session = searcher.search_two_pass(
            "auth",
            jev_scorer=JevScorer(api_key="test-key"),
            shortlist_size=2,
        )

        t = session.telemetry
        assert t is not None
        assert t.files_scanned > 0
        assert t.total_cost > 0
        assert t.total_tokens > 0
