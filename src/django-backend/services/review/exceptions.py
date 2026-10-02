"""Domain exceptions for the review service."""


class ReviewError(Exception):
    """Base class for review-service-specific errors."""


class ReviewerNotAssignedError(ReviewError):
    """The user may not review the competition and has no review in it."""


class ReviewClosedError(ReviewError):
    """The user's review is fixed: completed, or its competition left voting."""


class DuplicateProjectError(ReviewError):
    """The submitted ballot lists the same project more than once."""


class ProjectNotInCompetitionError(ReviewError):
    """The ballot references a project that is not eligible in this competition."""
