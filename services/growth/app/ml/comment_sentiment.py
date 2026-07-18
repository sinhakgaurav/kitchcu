"""Tiny logistic-style comment sentiment model for dish feedback.

No sklearn dependency — features are lexicon + surface signals; weights are
fit once at import via batch gradient descent on an embedded labeled set
(EN + Hinglish food-review phrases). Suitable for owner suggestions at
kitchen scale without an external ML service.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache

_TOKEN_RE = re.compile(r"[a-zA-Z']+")

POSITIVE_LEXICON = frozenset(
    {
        "amazing",
        "awesome",
        "best",
        "delicious",
        "fantastic",
        "fresh",
        "great",
        "homemade",
        "home",
        "love",
        "loved",
        "perfect",
        "tasty",
        "wonderful",
        "yummy",
        "superb",
        "outstanding",
        "flavourful",
        "flavorful",
        "authentic",
        "mast",
        "zabardast",
        "bahut",
        "accha",
        "achha",
        "swadisht",
        "mazedar",
        "perfectly",
        "excellent",
        "heavenly",
        "rich",
        "balanced",
    }
)

NEGATIVE_LEXICON = frozenset(
    {
        "bad",
        "awful",
        "bland",
        "cold",
        "disappointing",
        "dry",
        "horrible",
        "late",
        "oily",
        "overcooked",
        "poor",
        "salty",
        "spicy",
        "stale",
        "terrible",
        "undercooked",
        "worst",
        "waste",
        "burnt",
        "soggy",
        "raw",
        "bekaar",
        "bura",
        "kharaab",
        "kharab",
        "meh",
        "average",
        "okish",
        "overpriced",
    }
)

# (text, label) — 1 = positive, 0 = negative
_TRAINING_EXAMPLES: list[tuple[str, int]] = [
    ("Absolutely delicious, tasted just like homemade!", 1),
    ("Best butter chicken I've had in months — amazing!", 1),
    ("Fresh, flavourful and perfectly spiced. Love it.", 1),
    ("Zabardast taste, bahut accha tha. Will order again.", 1),
    ("Yummy and authentic home style — superb.", 1),
    ("Great portion, rich gravy, outstanding quality.", 1),
    ("Heavenly dessert, my family loved every bite.", 1),
    ("Mazedar and balanced spices. Perfect dinner.", 1),
    ("Excellent packaging and tasty food arrived hot.", 1),
    ("Wonderful — this is our go-to kitchen now.", 1),
    ("Cold and bland, very disappointing.", 0),
    ("Too oily and over-salty. Worst order yet.", 0),
    ("Stale bread, dry sabzi — waste of money.", 0),
    ("Arrived late, food was burnt and terrible.", 0),
    ("Bekaar taste, kharab quality. Not ordering again.", 0),
    ("Undercooked chicken, raw in the middle. Awful.", 0),
    ("Soggy pakora and poor packaging.", 0),
    ("Average at best — meh, overpriced.", 0),
    ("Too spicy and unbalanced. Horrible experience.", 0),
    ("Bura tha, cold delivery and bland dal.", 0),
]


@dataclass(frozen=True)
class SentimentResult:
    """Scored sentiment for one comment or an aggregate of comments."""

    score: float  # P(positive) in [0, 1]
    label: str  # positive | neutral | negative
    comment_count: int
    positive_share: float


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def extract_features(text: str) -> list[float]:
    """Hand-crafted features for the linear sentiment classifier."""
    tokens = _tokenize(text)
    n = max(len(tokens), 1)
    pos = sum(1 for t in tokens if t in POSITIVE_LEXICON)
    neg = sum(1 for t in tokens if t in NEGATIVE_LEXICON)
    bangs = (text or "").count("!")
    length_bucket = min(len(tokens) / 40.0, 1.0)
    return [
        1.0,  # bias
        pos / n,
        neg / n,
        float(pos - neg),
        min(bangs / 3.0, 1.0),
        length_bucket,
        1.0 if pos > neg else 0.0,
        1.0 if neg > pos else 0.0,
    ]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class CommentSentimentModel:
    """Binary logistic model trained on embedded food-review examples."""

    def __init__(self, weights: list[float] | None = None, lr: float = 0.35, epochs: int = 400) -> None:
        if weights is not None:
            self.weights = list(weights)
        else:
            dim = len(extract_features(""))
            self.weights = [0.0] * dim
            self._fit(lr=lr, epochs=epochs)

    def _fit(self, lr: float, epochs: int) -> None:
        xs = [extract_features(t) for t, _ in _TRAINING_EXAMPLES]
        ys = [float(y) for _, y in _TRAINING_EXAMPLES]
        w = self.weights
        n = len(xs)
        for _ in range(epochs):
            grads = [0.0] * len(w)
            for x, y in zip(xs, ys, strict=True):
                pred = _sigmoid(sum(wi * xi for wi, xi in zip(w, x, strict=True)))
                err = pred - y
                for i in range(len(w)):
                    grads[i] += err * x[i]
            for i in range(len(w)):
                w[i] -= lr * (grads[i] / n)
        self.weights = w

    def predict_proba(self, text: str) -> float:
        x = extract_features(text)
        return _sigmoid(sum(wi * xi for wi, xi in zip(self.weights, x, strict=True)))

    def score_comment(self, text: str) -> SentimentResult:
        p = self.predict_proba(text)
        if p >= 0.62:
            label = "positive"
        elif p <= 0.38:
            label = "negative"
        else:
            label = "neutral"
        return SentimentResult(score=round(p, 4), label=label, comment_count=1, positive_share=round(p, 4))

    def score_comments(self, texts: list[str]) -> SentimentResult:
        cleaned = [t.strip() for t in texts if t and t.strip()]
        if not cleaned:
            return SentimentResult(score=0.5, label="neutral", comment_count=0, positive_share=0.5)
        scores = [self.predict_proba(t) for t in cleaned]
        avg = sum(scores) / len(scores)
        pos_share = sum(1 for s in scores if s >= 0.62) / len(scores)
        if avg >= 0.62:
            label = "positive"
        elif avg <= 0.38:
            label = "negative"
        else:
            label = "neutral"
        return SentimentResult(
            score=round(avg, 4),
            label=label,
            comment_count=len(cleaned),
            positive_share=round(pos_share, 4),
        )


@lru_cache(maxsize=1)
def get_sentiment_model() -> CommentSentimentModel:
    return CommentSentimentModel()
