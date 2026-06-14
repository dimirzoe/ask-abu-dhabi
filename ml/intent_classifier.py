"""Optional ML intent classifier with a deterministic keyword fallback.

The orchestrator's gating uses :func:`core.intent.is_on_topic` (pure, offline).
This module offers an *optional*, self-contained scikit-learn classifier that can
be used to corroborate that decision. It degrades gracefully: if scikit-learn is
not installed, :class:`IntentClassifier` falls back to keyword matching so the
package still imports and tests run offline.
"""

from __future__ import annotations

import logging

from core.intent import ON_TOPIC_TERMS

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import guard
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    _SKLEARN_AVAILABLE = True
except Exception:  # noqa: BLE001 - any import failure means fallback mode
    _SKLEARN_AVAILABLE = False


# Small, illustrative training corpus. On-topic (1) vs off-topic (0).
_TRAIN_TEXTS: list[str] = [
    "what are the opening hours of sheikh zayed grand mosque",
    "how much is a ticket to louvre abu dhabi",
    "best family beaches in abu dhabi",
    "how do i get from the airport to downtown abu dhabi",
    "do i need a visa to visit the uae",
    "what is the dress code for visiting a mosque",
    "things to do on yas island with kids",
    "tell me about qasr al watan palace tours",
    "what is the capital of france",
    "write me a python function to sort a list",
    "who won the football world cup last year",
    "what is the weather like in tokyo today",
    "recommend a stock to invest in",
    "how do i bake chocolate chip cookies",
]
_TRAIN_LABELS: list[int] = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]


class IntentClassifier:
    """Classify whether a query is on-topic for Abu Dhabi tourism."""

    def __init__(self) -> None:
        """Train the TF-IDF + logistic-regression pipeline if sklearn is present."""
        self._model = None
        if _SKLEARN_AVAILABLE:
            self._model = Pipeline(
                steps=[
                    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                    ("clf", LogisticRegression(max_iter=1000)),
                ]
            )
            self._model.fit(_TRAIN_TEXTS, _TRAIN_LABELS)
        else:
            logger.info("scikit-learn unavailable; using keyword fallback.")

    @property
    def uses_ml(self) -> bool:
        """Whether a trained ML model backs predictions (vs keyword fallback)."""
        return self._model is not None

    def predict(self, query: str) -> bool:
        """Predict whether ``query`` is on-topic.

        Args:
            query: Raw user query.

        Returns:
            True when the query is classified as Abu Dhabi tourism related.
        """
        if self._model is not None:
            return bool(self._model.predict([query])[0] == 1)
        return self._keyword_fallback(query)

    @staticmethod
    def _keyword_fallback(query: str) -> bool:
        """Keyword-based on-topic heuristic used when sklearn is absent."""
        lowered = query.lower()
        return any(term in lowered for term in ON_TOPIC_TERMS)
