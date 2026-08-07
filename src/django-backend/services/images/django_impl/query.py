from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Prefetch

from apps.projects.models import ProjectImage
from services.images.query_interface import ImageQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.articles.models import Article
    from apps.projects.models import Project, UploadStatus


def gallery_images() -> QuerySet[ProjectImage]:
    """Images that describe the project itself.

    Excludes article uploads, which live on the project but belong to an
    article. Moved here from `services/project/django_impl/query.py`: the rule
    is about images, and the row-level lookups that enforce the same rule are
    in this module.
    """
    return (
        ProjectImage.objects.uploaded()
        .filter(article__isnull=True)
        .prefetch_related("variants")
    )


def gallery_prefetch(lookup: str = "images") -> Prefetch:
    return Prefetch(lookup, queryset=gallery_images())


class DjangoImageQuery(ImageQueryInterface):
    def gallery_prefetch(self, lookup: str = "images") -> Prefetch:
        # Module-level function, not this method: query services import each
        # other's module functions directly (see follows/query.py), and only
        # callers holding the container come through here.
        return gallery_prefetch(lookup)

    def get_gallery_image(
        self,
        project: Project,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        qs = ProjectImage.objects.filter(
            pk=image_id, project=project, article__isnull=True
        )
        if status is not None:
            qs = qs.filter(upload_status=status)
        return qs.first()

    def get_article_image(
        self,
        article: Article,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        qs = ProjectImage.objects.filter(pk=image_id, article=article)
        if status is not None:
            qs = qs.filter(upload_status=status)
        return qs.first()
