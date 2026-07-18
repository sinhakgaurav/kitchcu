"""Unit tests for the small comment-sentiment model (no DB)."""

from app.ml.comment_sentiment import CommentSentimentModel, extract_features, get_sentiment_model


def test_extract_features_has_bias_and_fixed_dim():
    feats = extract_features("Amazing homemade taste!")
    assert feats[0] == 1.0
    assert len(feats) == 8
    assert feats[1] > 0  # positive density


def test_model_scores_positive_comments_high():
    model = get_sentiment_model()
    result = model.score_comment("Absolutely delicious, tasted just like homemade!")
    assert result.score >= 0.62
    assert result.label == "positive"


def test_model_scores_negative_comments_low():
    model = get_sentiment_model()
    result = model.score_comment("Cold and bland, very disappointing.")
    assert result.score <= 0.38
    assert result.label == "negative"


def test_aggregate_empty_is_neutral():
    model = CommentSentimentModel(weights=[0.0] * 8)
    result = model.score_comments([])
    assert result.comment_count == 0
    assert result.label == "neutral"
    assert result.score == 0.5


def test_training_separates_held_examples():
    model = get_sentiment_model()
    pos = model.predict_proba("Best butter chicken — amazing and authentic!")
    neg = model.predict_proba("Worst order — stale and oily waste.")
    assert pos > neg
    assert pos - neg >= 0.25
