from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI

from api.routers import (
    auth,
    competitions,
    discussions,
    my_projects,
    my_review,
    projects,
    tags,
    users,
)

api = NinjaAPI(
    title="Project Showcase API",
    description="API for developer project showcasing platform",
    version="1.0.0",
)

# Add routers
api.add_router("/auth", auth.router)
api.add_router("/projects", projects.router)
api.add_router("/projects", discussions.router)
api.add_router("/my/projects", my_projects.router)
api.add_router("/my/reviews", my_review.router)
api.add_router("/tags", tags.router)
api.add_router("/competitions", competitions.router)
api.add_router("/users", users.router)


@api.get("/")
def root(request: HttpRequest) -> dict[str, Any]:
    return {"message": "Project Showcase API"}


@api.get("/health")
def health_check(request: HttpRequest) -> dict[str, Any]:
    return {"status": "healthy"}
