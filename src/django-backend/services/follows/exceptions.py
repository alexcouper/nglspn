"""Domain exceptions for the follows service."""


class FollowError(Exception):
    """Base class for follows-service-specific errors."""


class NotFollowingError(FollowError):
    """The user has no Follow row for the targeted project."""


class ChannelNotOnProjectError(FollowError):
    """The channel referenced does not belong to the follow's target — the
    project, or for a person follow, the person."""


class SelfFollowError(FollowError):
    """A user cannot follow themselves."""
