"""Backward-compatible re-exports from the split module structure.

New code should import from the specific modules:
    from reflex_search.scorers import LocalScorer, JevScorer
    from reflex_search.gate import ConfidenceGate
    from reflex_search.searcher import ReflexCodeSearcher
    from reflex_search.fallback import default_fallback_scorer
    from reflex_search.file_collector import collect_files, DEFAULT_EXCLUDES, DEFAULT_TEXT_SUFFIXES
"""

from reflex_search.fallback import default_fallback_scorer  # noqa: F401
from reflex_search.file_collector import (  # noqa: F401
    DEFAULT_EXCLUDES,
    DEFAULT_TEXT_SUFFIXES,
)
from reflex_search.gate import ConfidenceGate  # noqa: F401
from reflex_search.scorers import JevScorer, LocalScorer  # noqa: F401
from reflex_search.searcher import ReflexCodeSearcher  # noqa: F401
