import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ArticleSource(models.TextChoices):
    INTERNAL = "internal", "Internal"
    EXTERNAL = "external", "External"


class ArticleState(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class ArticleGlobalVisibility(models.TextChoices):
    AUTO = "auto", "Auto-approved (trusted author)"
    PENDING = "pending", "Pending admin review"
    APPROVED = "approved", "Admin-approved"
    DEMOTED = "demoted", "Demoted"


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="articles",
    )
    channel = models.ForeignKey(
        "follows.Channel",
        on_delete=models.PROTECT,
        related_name="articles",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_articles",
    )
    title = models.CharField(max_length=200, default="", blank=True)
    body = models.TextField(default="", blank=True)
    # Optional authored standfirst for listing cards. When blank, listings fall
    # back to services.articles.summary.derive_summary(body).
    summary = models.CharField(max_length=300, default="", blank=True)
    hero_image = models.ForeignKey(
        "projects.ProjectImage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hero_for_articles",
    )
    slug = models.SlugField(max_length=200, null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=ArticleSource.choices,
        default=ArticleSource.INTERNAL,
    )
    external_url = models.URLField(null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=ArticleState.choices,
        default=ArticleState.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    global_visibility = models.CharField(
        max_length=20,
        choices=ArticleGlobalVisibility.choices,
        default=ArticleGlobalVisibility.AUTO,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "articles"
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("project", "slug"),
                condition=Q(slug__isnull=False),
                name="articles_project_slug_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source=ArticleSource.INTERNAL, external_url__isnull=True)
                    | Q(source=ArticleSource.EXTERNAL, external_url__isnull=False)
                ),
                name="articles_source_external_url_consistent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.title}: {self.title or '(untitled draft)'}"

    def save(self, *args: object, **kwargs: object) -> None:
        # SQLite parity: the CHECK constraint above is not enforced identically
        # on SQLite, so guard the source/external_url XOR at save time too.
        if self.source == ArticleSource.INTERNAL and self.external_url:
            msg = "Internal articles MUST NOT carry an external_url."
            raise ValidationError({"external_url": msg})
        if self.source == ArticleSource.EXTERNAL and not self.external_url:
            msg = "External articles MUST carry an external_url."
            raise ValidationError({"external_url": msg})
        super().save(*args, **kwargs)

    @property
    def is_globally_visible(self) -> bool:
        return self.state == ArticleState.PUBLISHED and self.global_visibility in {
            ArticleGlobalVisibility.AUTO,
            ArticleGlobalVisibility.APPROVED,
        }
