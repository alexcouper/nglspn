"""Which of a competition's projects a reviewer may see and rank, and how a
review's status reads to its reviewer.

Service-level rather than Django-level: the rule is the same wherever it is
applied, and callers outside the service should not have to reach into
`django_impl` to find it.
"""

from apps.projects.models import CompetitionStatus, ProjectStatus, ReviewStatus

# A project in either state is off the ballot: it cannot be ranked, it is not
# shown to reviewers, and it takes no part in the tally.
EXCLUDED_PROJECT_STATUSES = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]

# Never stored. A review reads as ended once its competition has left voting
# without the reviewer completing it.
REVIEW_ENDED = "ended"


def effective_status(row_status: str | None, competition_status: str) -> str:
    """The status a reviewer sees; a missing row is a review not yet started."""
    status = row_status or ReviewStatus.IN_PROGRESS
    if (
        competition_status != CompetitionStatus.VOTING
        and status != ReviewStatus.COMPLETED
    ):
        return REVIEW_ENDED
    return status
