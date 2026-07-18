"""Small in-process ML helpers for growth intelligence."""

from app.ml.comment_sentiment import CommentSentimentModel, SentimentResult, get_sentiment_model

__all__ = ["CommentSentimentModel", "SentimentResult", "get_sentiment_model"]
