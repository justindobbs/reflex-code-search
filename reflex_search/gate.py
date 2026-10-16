"""Three-way confidence gate for the REFLEX search loop."""

from __future__ import annotations

import math

from reflex_search.models import GateDecision


class ConfidenceGate:
    """Three-way gate for the REFLEX search loop.

    - **accept**: score >= *accept_threshold*
    - **uncertain**: score >= *uncertain_threshold* but below accept
    - **reject**: score < *uncertain_threshold*

    The optional *min_margin* parameter (ported from tracecore-reflex)
    requires the top candidate to lead the runner-up by at least this
    margin before being accepted.  When the margin check fails, the
    decision is downgraded to **uncertain**.
    """

    def __init__(
        self,
        accept_threshold: float = 0.65,
        uncertain_threshold: float = 0.40,
        min_margin: float = 0.0,
    ) -> None:
        values = (accept_threshold, uncertain_threshold, min_margin)
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
            raise ValueError("gate thresholds and min_margin must be finite numbers")
        if not 0.0 <= accept_threshold <= 1.0 or not 0.0 <= uncertain_threshold <= 1.0:
            raise ValueError("thresholds must be between 0 and 1")
        if not 0.0 <= min_margin <= 1.0:
            raise ValueError("min_margin must be between 0 and 1")
        self.accept_threshold = accept_threshold
        self.uncertain_threshold = uncertain_threshold
        self.min_margin = min_margin

    def decide(self, score: float, runner_up: float = 0.0) -> GateDecision:
        if not isinstance(score, (int, float)) or not math.isfinite(score):
            return GateDecision.REJECT
        score = min(max(float(score), 0.0), 1.0)

        if score < self.uncertain_threshold:
            return GateDecision.REJECT

        if score >= self.accept_threshold:
            if self.min_margin > 0.0 and (score - runner_up) < self.min_margin:
                return GateDecision.UNCERTAIN
            return GateDecision.ACCEPT

        return GateDecision.UNCERTAIN
