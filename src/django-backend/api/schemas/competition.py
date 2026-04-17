from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from ninja import Schema

from .project import ImageVariantResponse
from .tag import TagWithCategoryResponse


class CompetitionStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTING_APPLICATIONS = "accepting_applications"
    VOTING = "voting"
    CLOSED = "closed"


class CompetitionProjectResponse(Schema):
    id: UUID
    title: str
    tags: list[TagWithCategoryResponse]
    main_image_url: str | None = None
    main_image_thumb_url: str | None = None
    main_image_variants: list[ImageVariantResponse] = []

    @classmethod
    def from_list_item(cls, item: Any) -> "CompetitionProjectResponse":
        return cls(
            id=item.project.id,
            title=item.project.title,
            tags=item.tags,
            main_image_url=item.main_image_url,
            main_image_thumb_url=item.main_image_thumb_url,
            main_image_variants=item.main_image_variants,
        )


class CompetitionResponse(Schema):
    id: UUID
    name: str
    slug: str
    start_date: date
    submission_deadline: date
    voting_end_date: date | None = None
    quote: str | None = None
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    image_wide_url: str | None = None
    image_wide_winner_url: str | None = None
    project_count: int
    projects: list[CompetitionProjectResponse]
    winner: CompetitionProjectResponse | None = None
    pending_projects_count: int

    @classmethod
    def from_competition(
        cls,
        competition: Any,
        *,
        approved_project_items: list[Any],
        winner_item: Any | None,
        project_count: int,
        pending_projects_count: int,
    ) -> "CompetitionResponse":
        return cls(
            id=competition.id,
            name=competition.name,
            slug=competition.slug,
            start_date=competition.start_date,
            submission_deadline=competition.submission_deadline,
            voting_end_date=competition.voting_end_date,
            quote=competition.quote,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            image_wide_url=competition.image_wide_url,
            image_wide_winner_url=competition.image_wide_winner_url,
            project_count=project_count,
            projects=[
                CompetitionProjectResponse.from_list_item(item)
                for item in approved_project_items
            ],
            winner=(
                CompetitionProjectResponse.from_list_item(winner_item)
                if winner_item
                else None
            ),
            pending_projects_count=pending_projects_count,
        )


class CompetitionOverviewResponse(Schema):
    id: UUID
    name: str
    slug: str
    start_date: date
    submission_deadline: date
    voting_end_date: date | None = None
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    image_wide_url: str | None = None
    image_wide_winner_url: str | None = None
    project_count: int
    pending_projects_count: int

    @classmethod
    def from_competition(
        cls,
        competition: Any,
        *,
        project_count: int,
        pending_projects_count: int,
    ) -> "CompetitionOverviewResponse":
        return cls(
            id=competition.id,
            name=competition.name,
            slug=competition.slug,
            start_date=competition.start_date,
            submission_deadline=competition.submission_deadline,
            voting_end_date=competition.voting_end_date,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            image_wide_url=competition.image_wide_url,
            image_wide_winner_url=competition.image_wide_winner_url,
            project_count=project_count,
            pending_projects_count=pending_projects_count,
        )


class CompetitionOverviewListResponse(Schema):
    competitions: list[CompetitionOverviewResponse]
    pending_projects_count: int


class CompetitionListResponse(Schema):
    competitions: list[CompetitionResponse]
    pending_projects_count: int


class CompetitionSummaryResponse(Schema):
    name: str
    slug: str
    submission_deadline: date
    voting_end_date: date | None = None
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    project_count: int

    @classmethod
    def from_highlight(cls, highlight: Any) -> "CompetitionSummaryResponse":
        competition = highlight.competition
        return cls(
            name=competition.name,
            slug=competition.slug,
            submission_deadline=competition.submission_deadline,
            voting_end_date=competition.voting_end_date,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            project_count=highlight.project_count,
        )


class CompetitionHighlightsResponse(Schema):
    competitions: list[CompetitionSummaryResponse]
