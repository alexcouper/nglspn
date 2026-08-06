from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.articles.models import Article
    from apps.projects.models import Project, ProjectImage

# Upload limits. Article uploads get their own ceiling rather than sharing the
# project's: they are inline figures in a body, not slots in a gallery, so a
# long article needs more of them than a project page ever shows.
MAX_IMAGES_PER_PROJECT = 10
MAX_IMAGES_PER_ARTICLE = 30
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


@dataclass(frozen=True)
class FileMeta:
    """What the browser knows about the file before it uploads it."""

    filename: str
    content_type: str
    file_size: int


@dataclass(frozen=True)
class PreparedUpload:
    """A reserved image row plus the presigned PUT that fills it."""

    image: ProjectImage
    upload_url: str
    method: str
    headers: dict[str, str]
    storage_key: str


class ImageHandlerInterface(ABC):
    """Owns the `ProjectImage` row lifecycle on top of `StorageService`.

    The two `create_*` methods differ in the policy an upload is subject to —
    which cap it counts against, and whether it may become the project's cover.
    Everything after that point is shared, because `complete_upload` and
    `delete_image` read the owner off the row (`image.article_id`) rather than
    being told again by the caller, so the two paths cannot drift apart.
    """

    @abstractmethod
    def create_gallery_upload(
        self, project: Project, meta: FileMeta, *, is_icon: bool = False
    ) -> PreparedUpload:
        """Reserve an image that describes the project itself.

        Raises `InvalidImageError` on a rejected type or size, and
        `ImageCapReachedError` once the gallery is full. Icons are exempt from
        the cap — they do not occupy a gallery slot.
        """

    @abstractmethod
    def create_article_upload(self, article: Article, meta: FileMeta) -> PreparedUpload:
        """Reserve an image that belongs to `article`.

        The row still hangs off the article's project so it shares the storage
        and variant pipeline, but it never counts against the project's gallery
        cap and can never be promoted to the cover image.
        """

    @abstractmethod
    def complete_upload(
        self, image: ProjectImage, *, width: int | None, height: int | None
    ) -> ProjectImage:
        """Mark a reserved row uploaded once its object is in storage.

        Raises `UploadNotCompletedError` if the object is missing, which is how
        a failed or abandoned PUT is reported.
        """

    @abstractmethod
    def delete_image(self, image: ProjectImage) -> None:
        """Remove the row, its variants, and every object they hold in storage."""

    @abstractmethod
    def generate_variants(self, image_id: str) -> None:
        """Render and store the resized WebP variants for an uploaded image."""
