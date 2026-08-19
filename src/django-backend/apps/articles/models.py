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


class ListingImageMode(models.TextChoices):
    """How an article's listing image was decided.

    A nullable ``listing_image`` cannot tell "not chosen yet" from "deliberately
    removed", so removal would not survive the next save.
    """

    AUTO = "auto", "First image uploaded to the article"
    CHOSEN = "chosen", "Author's choice"
    NONE = "none", "No image"


class ArticleGlobalVisibility(models.TextChoices):
    AUTO = "auto", "Auto-approved (trusted author)"
    PENDING = "pending", "Pending admin review"
    APPROVED = "approved", "Admin-approved"
    DEMOTED = "demoted", "Demoted"


# The visibility states that render globally. One tuple, read by the
# per-instance property, the queryset method and the feed's join filter, so a
# fifth state is added here and nowhere else.
GLOBALLY_VISIBLE_STATES = (
    ArticleGlobalVisibility.AUTO,
    ArticleGlobalVisibility.APPROVED,
)


def globally_visible_q(prefix: str = "") -> Q:
    """``Article.is_globally_visible`` as a queryset condition.

    ``prefix`` walks the rule across a relation: ``globally_visible_q("article__")``
    is what ``apps.feed``'s ``visible_subject()`` needs, since it filters
    FeedEvent rows by the article hanging off them. Without the prefix that
    module would have to spell the rule out a second time, somewhere a change
    here would not reach.
    """
    return Q(
        **{
            f"{prefix}state": ArticleState.PUBLISHED,
            f"{prefix}global_visibility__in": GLOBALLY_VISIBLE_STATES,
        }
    )


class ArticleQuerySet(models.QuerySet):
    def globally_visible(self) -> "ArticleQuerySet":
        """The articles the site shows to everyone.

        Drafts, articles awaiting admin review and demoted articles are all
        excluded — every public read path goes through here, and the author's
        own views opt out explicitly rather than by forgetting to filter.
        """
        return self.filter(globally_visible_q())


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
    # SET_NULL, not PROTECT: ProjectImage.article cascades from this article, so
    # deleting an article collects rows that this column points at. Rather than
    # rely on how the collector orders that cycle, a deleted image simply blanks
    # the card.
    listing_image = models.ForeignKey(
        "projects.ProjectImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_for_articles",
    )
    # Framing for the listing image, as {"x", "y", "w", "h", "ratio"} with
    # x/y/w/h normalised 0-1 against the source image and always 16:9. `ratio`
    # is derivable from the rect and the source dimensions, but is stored so a
    # listing card can reserve its box without being told the source's pixel
    # size. Null means the default: 16:9, centred.
    listing_crop = models.JSONField(null=True, blank=True)
    listing_image_mode = models.CharField(
        max_length=20,
        choices=ListingImageMode.choices,
        default=ListingImageMode.AUTO,
    )
    # The platform event this article is written about, if any. Publishing a
    # linked article supersedes that event so the feed shows one entry, not the
    # bare event and its write-up side by side. SET_NULL rather than CASCADE:
    # losing the event should orphan the link, not delete the article.
    #
    # Set from Django admin only, and deliberately not on the publish API:
    # superseding hides someone else's entry from the feed, which is an
    # editorial act rather than something an author does to their own article.
    # A missed link costs two entries where one would do — visible, harmless,
    # and correctable after the fact.
    about_feed_event = models.ForeignKey(
        "feed.FeedEvent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="written_up_by",
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
    # When this article became visible to everyone — the same instant as
    # `published_at` for an author the site already trusts, and the moment an
    # admin approved it for one it does not.
    #
    # It exists because the two are not interchangeable for deciding whether to
    # notify followers. `published_at` answers "when does this article claim to
    # be from", which an importer backdates freely; only this answers "how long
    # ago did this become news", which is the question the fan-out asks. Reset
    # on each transition into visibility, so a re-approval after a demotion is
    # judged on when it came back rather than when it first went out.
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArticleQuerySet.as_manager()

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
        return (
            self.state == ArticleState.PUBLISHED
            and self.global_visibility in GLOBALLY_VISIBLE_STATES
        )
