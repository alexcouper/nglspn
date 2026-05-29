from datetime import date, timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.articles.models import Article, ArticleSource, ArticleState
from apps.discussions.models import Discussion
from apps.emails.models import BroadcastEmail, BroadcastEmailImage
from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.notifications.models import Notification, NotificationCadence
from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    ContributorRole,
    Project,
    ProjectCategory,
    ProjectContributor,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
)
from apps.tags.models import Tag, TagCategory, TagStatus
from apps.users.models import EmailVerificationCode, PasswordResetCode
from services.users.django_impl.query import BROADCAST_CHANNEL_BY_EMAIL_TYPE

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    kennitala = factory.Sequence(lambda n: f"{n:010d}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_verified = True
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "testpassword123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class TagCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TagCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")
    description = factory.Faker("sentence")
    display_order = factory.Sequence(lambda n: n)
    is_active = True


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")
    description = factory.Faker("sentence")
    color = "#FF5733"
    category = factory.SubFactory(TagCategoryFactory)
    status = TagStatus.APPROVED


class ProjectCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"cat-{n}")
    display_order = factory.Sequence(lambda n: n)


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project
        skip_postgeneration_save = True

    title = factory.Faker("company")
    tagline = factory.Faker("catch_phrase")
    description = factory.Faker("paragraph")
    website_url = factory.Faker("url")
    status = ProjectStatus.PENDING
    submission_month = factory.LazyFunction(lambda: "2025-01")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Accept `owner=` as a concept-level alias for `creator=` so existing
        # tests keep reading naturally after the field rename. `creator` is not
        # a class-level SubFactory because that would always populate kwargs and
        # mask the "passed both" case below.
        owner_passed = "owner" in kwargs
        creator_passed = "creator" in kwargs
        if owner_passed and creator_passed:
            msg = "ProjectFactory: pass either creator= or owner=, not both"
            raise TypeError(msg)
        if owner_passed:
            kwargs["creator"] = kwargs.pop("owner")
        elif not creator_passed:
            kwargs["creator"] = UserFactory()
        return super()._create(model_class, *args, **kwargs)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs) -> None:
        if not create or not extracted:
            return
        self.tags.add(*extracted)

    @factory.post_generation
    def _contributor(self, create, extracted, **kwargs) -> None:
        # Mirror the production invariant: every project has at least one
        # OWNER contributor with full_edit. Tests that need a different shape
        # can pass `_contributor=False` and add their own rows.
        if not create or extracted is False or self.creator_id is None:
            return
        ProjectContributor.objects.get_or_create(
            project=self,
            user=self.creator,
            defaults={"role": ContributorRole.OWNER, "full_edit": True},
        )


class ChannelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Channel
        # Project creation auto-seeds an "Updates" channel via post_save —
        # use get_or_create so `ChannelFactory(project=p, name="Updates")`
        # returns the existing seeded row instead of raising on the
        # (project, name) unique constraint.
        django_get_or_create = ("project", "name")

    project = factory.SubFactory(ProjectFactory)
    name = factory.Sequence(lambda n: f"Channel {n}")


def ensure_house_project() -> Project:
    """Return the singleton house project, creating it if absent.

    The DB enforces a single is_house_project row, so tests that need several
    house followers share one project. The creator is made *before* the house
    exists (so the auto-follow signal does not subscribe them) and has the
    legacy opt-in flags cleared, keeping them out of broadcast recipient sets.
    """
    house = Project.objects.filter(is_house_project=True).first()
    if house is not None:
        return house
    creator = UserFactory(
        email_opt_in_platform_updates=False,
        email_opt_in_competition_results=False,
    )
    return ProjectFactory(is_house_project=True, owner=creator)


def make_broadcast_follower(
    email_type: str, *, email_enabled: bool = True, **user_kwargs
):
    """Create a user following the house project with the given email
    preference on the channel that governs `email_type` broadcasts.

    Active non-system users auto-follow the house on creation (post_save
    signal). This sets the follow + channel preference explicitly so the helper
    also covers inactive/system users, and so `email_enabled=False` overrides
    the signal's all-on default.
    """
    house = ensure_house_project()
    channel, _ = Channel.objects.get_or_create(
        project=house, name=BROADCAST_CHANNEL_BY_EMAIL_TYPE[email_type]
    )
    user = UserFactory(**user_kwargs)
    follow, _ = Follow.objects.get_or_create(user=user, project=house)
    FollowChannelPreference.objects.update_or_create(
        follow=follow,
        channel=channel,
        defaults={"email_enabled": email_enabled, "in_app_enabled": True},
    )
    return user


class DiscussionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Discussion

    project = factory.SubFactory(ProjectFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.Faker("paragraph")
    parent = None


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    discussion = factory.SubFactory(DiscussionFactory)
    email_cadence = NotificationCadence.IMMEDIATE


class ProjectImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectImage

    project = factory.SubFactory(ProjectFactory)
    storage_key = factory.Sequence(lambda n: f"projects/images/{n}.jpg")
    original_filename = factory.Sequence(lambda n: f"image_{n}.jpg")
    content_type = "image/jpeg"
    file_size = 1024
    upload_status = "uploaded"


class ArticleFactory(factory.django.DjangoModelFactory):
    """Draft article on the project's "Updates" channel by the project creator.

    Sub-attributes default off the project so common cases work with no
    explicit args: `ArticleFactory()` is a publishable draft. Pass any of
    project, channel, author, hero_image to override.
    """

    class Meta:
        model = Article

    project = factory.SubFactory(ProjectFactory)
    channel = factory.LazyAttribute(
        lambda a: ChannelFactory(project=a.project, name="Updates")
    )
    author = factory.LazyAttribute(lambda a: a.project.creator)
    title = "Hello world"
    body = "A solid body of text"
    hero_image = factory.LazyAttribute(lambda a: ProjectImageFactory(project=a.project))
    source = ArticleSource.INTERNAL
    state = ArticleState.DRAFT


class PublishedArticleFactory(ArticleFactory):
    """An already-published article. Slug is NOT generated by this factory —
    tests that exercise rendering paths should publish through
    `HANDLERS.articles.publish` to get the real slug-assignment behaviour;
    tests that just need a published row for fan-out / queries can use this.
    """

    state = ArticleState.PUBLISHED
    published_at = factory.LazyFunction(timezone.now)


class CompetitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Competition

    name = factory.Sequence(lambda n: f"Competition {n}")
    start_date = factory.LazyFunction(lambda: date(2025, 1, 1))
    submission_deadline = factory.LazyFunction(lambda: date(2025, 1, 31))
    voting_end_date = factory.LazyFunction(lambda: date(2025, 2, 15))
    winner = None

    @factory.post_generation
    def projects(self, create, extracted, **kwargs) -> None:
        if not create or not extracted:
            return
        self.projects.add(*extracted)


class CompetitionReviewerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompetitionReviewer

    user = factory.SubFactory(UserFactory)
    competition = factory.SubFactory(CompetitionFactory)


class ProjectRankingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectRanking

    reviewer = factory.SubFactory(UserFactory)
    competition = factory.SubFactory(CompetitionFactory)
    project = factory.SubFactory(ProjectFactory)
    position = factory.Sequence(lambda n: n + 1)


class BroadcastEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BroadcastEmail

    subject = factory.Sequence(lambda n: f"Broadcast {n}")
    body_markdown = "Hello **world**!\n\nThis is a test broadcast."
    email_type = None
    created_by = factory.SubFactory(UserFactory, is_staff=True, is_superuser=True)

    @factory.post_generation
    def individual_recipients(self, create, extracted, **kwargs) -> None:
        if not create or not extracted:
            return
        self.individual_recipients.add(*extracted)


class BroadcastEmailImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BroadcastEmailImage

    broadcast_email = factory.SubFactory(BroadcastEmailFactory)
    image = factory.django.ImageField(filename="test-image.png")
    original_filename = factory.Sequence(lambda n: f"image_{n}.png")


class EmailVerificationCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailVerificationCode

    user = factory.SubFactory(UserFactory)
    code = factory.Sequence(lambda n: f"{n:06d}")
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=15))


class PasswordResetCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetCode

    user = factory.SubFactory(UserFactory)
    code = factory.Sequence(lambda n: f"{n:06d}")
    attempts = 0
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=15))
