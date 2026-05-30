"""Domain exceptions for the follows service."""


class FollowError(Exception):
    """Base class for follows-service-specific errors."""


class NotFollowingError(FollowError):
    """The user has no Follow row for the targeted project."""


class ChannelNotOnProjectError(FollowError):
    """The channel referenced does not belong to the project."""
