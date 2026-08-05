"""Domain exceptions for the review service."""


class ReviewError(Exception):
    """Base class for review-service-specific errors."""


class ReviewerNotAssignedError(ReviewError):
    """The user is not assigned as a reviewer for the competition."""


class ReviewClosedError(ReviewError):
    """The reviewer's review is completed or ended, so the ballot is fixed."""


class DuplicateProjectError(ReviewError):
    """The submitted ballot lists the same project more than once."""


class ProjectNotInCompetitionError(ReviewError):
    """The ballot references a project that is not eligible in this competition."""
