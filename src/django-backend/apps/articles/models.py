import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL


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


def delete_author_owned_else_keep(
    collector: Any, field: Any, sub_objs: Any, using: str
) -> None:
    """`on_delete` for `Article.author`.

    Deleting a user takes their author-owned articles with them — nobody else
    may edit those, and a row with neither project nor author is one the check
    constraint rejects. Articles on a project stay and lose their byline, as
    they always have. Decided on the row's shape with queryset filters rather
    than attribute reads: the collector hands over a deferred queryset.
    """
    CASCADE(collector, field, sub_objs.filter(project__isnull=True), using)
    SET_NULL(collector, field, sub_objs.filter(project__isnull=False), using)


def protect_project_channel(
    collector: Any, field: Any, sub_objs: Any, using: str
) -> None:
    """`on_delete` for `Article.channel`.

    A project's channel cannot go while articles sit in it (`PROTECT`, as
    before). A person's channel only goes when the person does, and their
    articles go with them — `PROTECT` here would make the account undeletable.
    """
    on_project = sub_objs.filter(project__isnull=False)
    if on_project.exists():
        PROTECT(collector, field, on_project, using)
    CASCADE(collector, field, sub_objs.filter(project__isnull=True), using)


class Article(models.Model):
    """A piece of writing on a project, or under its author's own name.

    An article with a `project` sits in one of that project's channels. One
    without is author-owned: `author` is required, `channel` is null while it is
    a draft and becomes the author's personal channel on publish (see
    `services.articles`). The constraints below hold the shape; which channel
    an author-owned article may carry is a handler rule, since a CHECK cannot
    join to the channel's own owner.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="articles",
    )
    channel = models.ForeignKey(
        "follows.Channel",
        on_delete=protect_project_channel,
        null=True,
        blank=True,
        related_name="articles",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=delete_author_owned_else_keep,
        null=True,
        blank=True,
        related_name="authored_articles",
    )
    title = models.CharField(max_length=200, default="", blank=True)
    body = models.TextField(default="", blank=True)
    # Optional authored standfirst for listing cards. When blank, listings fall
    # back to services.articles.summary.derive_summary(body).
    summary = models.CharField(max_length=300, default="", blank=True)
    # The cover: the one image an author picks for the article, shown wide at
    # the top of the page and in the email, and on its listing cards. Null is
    # "no cover", which also means a text-only card — nothing is derived from
    # the body on the author's behalf.
    #
    # SET_NULL, not PROTECT: Image.article cascades from this article, so
    # deleting an article collects rows that this column points at. Rather than
    # rely on how the collector orders that cycle, a deleted image simply blanks
    # the card.
    listing_image = models.ForeignKey(
        "projects.Image",
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
                condition=Q(slug__isnull=False, project__isnull=False),
                name="articles_project_slug_uniq",
            ),
            models.UniqueConstraint(
                fields=("author", "slug"),
                condition=Q(slug__isnull=False, project__isnull=True),
                name="articles_author_slug_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source=ArticleSource.INTERNAL, external_url__isnull=True)
                    | Q(source=ArticleSource.EXTERNAL, external_url__isnull=False)
                ),
                name="articles_source_external_url_consistent",
            ),
            # A project article always has a channel; an author-owned one may
            # or may not (draft vs published).
            models.CheckConstraint(
                condition=Q(project__isnull=True) | Q(channel__isnull=False),
                name="articles_project_implies_channel",
            ),
            # Author-owned means someone owns it; `delete_author_owned_else_keep`
            # is what keeps a user delete from producing a row that fails this.
            models.CheckConstraint(
                condition=Q(project__isnull=False) | Q(author__isnull=False),
                name="articles_project_or_author",
            ),
        ]

    def __str__(self) -> str:
        title = self.title or "(untitled draft)"
        if self.project_id:
            return f"{self.project.title}: {title}"
        return f"{self.author}: {title}"

    def save(self, *args: object, **kwargs: object) -> None:
        # SQLite parity: the CHECK constraint above is not enforced identically
        # on SQLite, so guard the source/external_url XOR at save time too.
        if self.source == ArticleSource.INTERNAL and self.external_url:
            msg = "Internal articles MUST NOT carry an external_url."
            raise ValidationError({"external_url": msg})
        if self.source == ArticleSource.EXTERNAL and not self.external_url:
            msg = "External articles MUST carry an external_url."
            raise ValidationError({"external_url": msg})
        # An author-owned article's channel is the author's own or nothing. A
        # CHECK cannot see the channel's owner, so this is the one place the
        # rule is enforced on the row itself; the handler rejects it earlier.
        if self.project_id is None and self.channel_id is not None:
            channel_project_id = (
                type(self.channel)
                .objects.filter(pk=self.channel_id)
                .values_list("project_id", flat=True)
                .first()
            )
            if channel_project_id is not None:
                msg = "An author-owned article cannot sit in a project's channel."
                raise ValidationError({"channel": msg})
        super().save(*args, **kwargs)

    @property
    def is_author_owned(self) -> bool:
        return self.project_id is None

    @property
    def is_globally_visible(self) -> bool:
        return (
            self.state == ArticleState.PUBLISHED
            and self.global_visibility in GLOBALLY_VISIBLE_STATES
        )
