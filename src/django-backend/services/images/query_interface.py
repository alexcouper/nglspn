from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import Prefetch

    from apps.articles.models import Article
    from apps.projects.models import Project, ProjectImage, UploadStatus


class ImageQueryInterface(ABC):
    """Reads over `ProjectImage`.

    Two rules live here and nowhere else. A project's own images are the rows
    with no `article` — a project endpoint that forgets that is an
    IDOR-adjacent bug with nothing to catch it. An article's images are the
    rows with that `article`, and nothing else about the project.
    """

    @abstractmethod
    def gallery_prefetch(self, lookup: str = "images") -> Prefetch:
        """`Prefetch` for a project's own images, at any relation depth.

        Use for every prefetch that will reach `resolve_image_by_purpose` or a
        project gallery: it does no filtering of its own and will otherwise
        fall back to an article figure or a row whose PUT never landed.
        `lookup` is the relation path — `"images"`,
        `"article__project__images"`, `"winner__images"`.
        """

    @abstractmethod
    def get_gallery_image(
        self,
        project: Project,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        """One of `project`'s own images. `None` if absent, or an article's."""

    @abstractmethod
    def get_article_image(
        self,
        article: Article,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        """One of `article`'s images. `None` if absent, or another article's."""
