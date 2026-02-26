from datetime import date, timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.emails.models import BroadcastEmail, BroadcastEmailImage
from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    Project,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
)
from apps.tags.models import Tag, TagCategory, TagStatus
from apps.users.models import EmailVerificationCode, PasswordResetCode

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


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    title = factory.Faker("company")
    description = factory.Faker("paragraph")
    website_url = factory.Faker("url")
    owner = factory.SubFactory(UserFactory)
    status = ProjectStatus.PENDING
    submission_month = factory.LazyFunction(lambda: "2025-01")

    @factory.post_generation
    def tags(self, create, extracted, **kwargs) -> None:
        if not create or not extracted:
            return
        self.tags.add(*extracted)


class ProjectImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectImage

    project = factory.SubFactory(ProjectFactory)
    storage_key = factory.Sequence(lambda n: f"projects/images/{n}.jpg")
    original_filename = factory.Sequence(lambda n: f"image_{n}.jpg")
    content_type = "image/jpeg"
    file_size = 1024
    upload_status = "uploaded"


class CompetitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Competition

    name = factory.Sequence(lambda n: f"Competition {n}")
    start_date = factory.LazyFunction(lambda: date(2025, 1, 1))
    end_date = factory.LazyFunction(lambda: date(2025, 1, 31))
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
