from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.projects.models import ProjectStatus

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

    @classmethod
    def from_project(cls, project: Any) -> "CompetitionProjectResponse":
        main_image = project.images.filter(
            upload_status="uploaded", is_main=True
        ).first()
        if not main_image:
            main_image = project.images.filter(upload_status="uploaded").first()

        return cls(
            id=project.id,
            title=project.title,
            tags=[
                TagWithCategoryResponse(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    description=tag.description,
                    color=tag.color,
                    category_id=tag.category.id if tag.category else None,
                    category_slug=tag.category.slug if tag.category else None,
                    status=tag.status,
                )
                for tag in project.tags.select_related("category").all()
            ],
            main_image_url=main_image.url if main_image else None,
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
            .prefetch_related("images")
        )
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
                CompetitionProjectResponse.from_project(p) for p in approved_projects
            ],
            winner=(
                CompetitionProjectResponse.from_project(competition.winner)
                if competition.winner
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
