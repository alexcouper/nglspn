from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from django.db.models import Prefetch
from ninja import Schema

from apps.projects.models import ProjectImage, ProjectStatus
from services.project.django_impl import to_list_item

from .tag import TagWithCategoryResponse


class CompetitionStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTING_APPLICATIONS = "accepting_applications"
    CLOSED = "closed"


class CompetitionProjectResponse(Schema):
    id: UUID
    title: str
    tags: list[TagWithCategoryResponse]
    main_image_url: str | None = None
    main_image_thumb_url: str | None = None

    @classmethod
    def from_list_item(cls, item: Any) -> "CompetitionProjectResponse":
        return cls(
            id=item.project.id,
            title=item.project.title,
            tags=item.tags,
            main_image_url=item.main_image_url,
            main_image_thumb_url=item.main_image_thumb_url,
        )


class CompetitionResponse(Schema):
    id: UUID
    name: str
    slug: str
    start_date: date
    end_date: date
    quote: str | None = None
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    project_count: int
    projects: list[CompetitionProjectResponse]
    winner: CompetitionProjectResponse | None = None
    pending_projects_count: int

    @classmethod
    def from_competition(cls, competition: Any) -> "CompetitionResponse":
        approved_projects = list(
            competition.projects.filter(status=ProjectStatus.APPROVED)
            .order_by("title")
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProjectImage.objects.filter(
                        upload_status="uploaded"
                    ).prefetch_related("variants"),
                ),
                "tags__category",
                "won_competitions",
            )
        )
        project_items = [to_list_item(p) for p in approved_projects]
        winner_item = to_list_item(competition.winner) if competition.winner else None
        return cls(
            id=competition.id,
            name=competition.name,
            slug=competition.slug,
            start_date=competition.start_date,
            end_date=competition.end_date,
            quote=competition.quote,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            project_count=competition.projects.count(),
            projects=[
                CompetitionProjectResponse.from_list_item(item)
                for item in project_items
            ],
            winner=(
                CompetitionProjectResponse.from_list_item(winner_item)
                if winner_item
                else None
            ),
            pending_projects_count=competition.projects.filter(
                status=ProjectStatus.PENDING
            ).count(),
        )


class CompetitionOverviewResponse(Schema):
    id: UUID
    name: str
    slug: str
    start_date: date
    end_date: date
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    project_count: int
    pending_projects_count: int

    @classmethod
    def from_competition(cls, competition: Any) -> "CompetitionOverviewResponse":
        return cls(
            id=competition.id,
            name=competition.name,
            slug=competition.slug,
            start_date=competition.start_date,
            end_date=competition.end_date,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            project_count=competition.projects.count(),
            pending_projects_count=competition.projects.filter(
                status=ProjectStatus.PENDING
            ).count(),
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
    end_date: date
    prize_amount: Decimal | None = None
    status: CompetitionStatusEnum
    image_url: str | None = None
    project_count: int

    @classmethod
    def from_competition(cls, competition: Any) -> "CompetitionSummaryResponse":
        return cls(
            name=competition.name,
            slug=competition.slug,
            end_date=competition.end_date,
            prize_amount=competition.prize_amount,
            status=competition.status,
            image_url=competition.image_url,
            project_count=competition.project_count,
        )


class ActiveOrRecentResponse(Schema):
    active: CompetitionSummaryResponse | None = None
    recent: CompetitionSummaryResponse | None = None
