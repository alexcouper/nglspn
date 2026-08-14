"""Domain exceptions for the feed service."""


class FeedError(Exception):
    """Base class for feed-service-specific errors."""


class FeedEventNotFoundError(FeedError):
    """No FeedEvent exists with the given id."""
