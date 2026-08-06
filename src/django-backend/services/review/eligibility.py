"""Which of a competition's projects a reviewer may see and rank.

Service-level rather than Django-level: the rule is the same wherever it is
applied, and callers outside the service should not have to reach into
`django_impl` to find it.
"""

from apps.projects.models import ProjectStatus

# A project in either state is off the ballot: it cannot be ranked, it is not
# shown to reviewers, and it takes no part in the tally.
EXCLUDED_PROJECT_STATUSES = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]
