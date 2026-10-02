from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from apps.projects.models import Competition, Project
from services.review.tally import (
    MarginMatrix,
    ProjectId,
    ProjectSupport,
    TieBreak,
)


@dataclass(frozen=True)
class CompetitionTally:
    """The computed ordering plus everything needed to distrust it."""

    counted_ballots: int = 0
    projects: dict[ProjectId, Project] = field(default_factory=dict)
    tiers: list[list[ProjectId]] = field(default_factory=list)
    support: dict[ProjectId, ProjectSupport] = field(default_factory=dict)
    margins: MarginMatrix = field(default_factory=dict)
    # Populated only for projects whose rank came from the tie-break ladder.
    tie_breaks: dict[ProjectId, TieBreak] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewProjectItem:
    """A project as it appears on a ballot, with its images already resolved.

    Resolution happens here rather than in the router because it is only
    correct against a queryset that filtered `images` to uploaded ones — the
    rule and the prefetch it depends on belong in the same place.
    """

    project: Project
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    category_name: str | None = None


@dataclass(frozen=True)
class ReviewerProjects:
    """One reviewer's ballot: what they ranked, and what is left to consider."""

    ranked: list[ReviewProjectItem] = field(default_factory=list)
    pool: list[ReviewProjectItem] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewCompetition:
    """A competition as one user sees it from the review side."""

    competition: Competition
    # As `effective_status` reports it, so it may be "ended".
    status: str
    # False once the competition has left voting, or for a past reviewer who
    # has since lost access; such a user may only read.
    can_write: bool


class ReviewQueryInterface(ABC):
    @abstractmethod
    def get_competition_tally(self, competition_id: UUID) -> CompetitionTally:
        """Tally the completed ballots for a competition.

        Counts only reviewers whose review is completed, over projects that are
        neither rejected nor in the ice box.
        """

    @abstractmethod
    def get_reviewer_projects(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewerProjects:
        """Split a competition's eligible projects for one reviewer.

        `ranked` is in saved position order; `pool` is in an order that is
        stable for this reviewer and uncorrelated with any other reviewer's.
        """

    @abstractmethod
    def can_review(self, user_id: UUID, competition_id: UUID) -> bool:
        """Whether the user may rank and set status in the competition now.

        True when the competition is in voting, the user is active and not a
        system user, and the user is a member of its reviewer group.
        """

    @abstractmethod
    def review_competitions_for(self, user_id: UUID) -> list[ReviewCompetition]:
        """Competitions the user can review now, plus any they have a review in.

        Newest first by start date.
        """

    @abstractmethod
    def get_review_competition(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewCompetition | None:
        """One competition from the review side, or None if the user can
        neither review it nor has a review in it."""

    @abstractmethod
    def can_view_review_project(self, user_id: UUID, project_id: UUID) -> bool:
        """Whether the project is in a competition the user can review or has
        a review in."""
