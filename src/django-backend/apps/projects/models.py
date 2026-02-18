import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.tags.models import Tag

# Icelandic character transliteration for slugs
ICELANDIC_TRANSLITERATION = {
    "á": "a",
    "ð": "d",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ý": "y",
    "þ": "th",
    "æ": "ae",
    "ö": "o",
    "Á": "A",
    "Ð": "D",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "Ý": "Y",
    "Þ": "Th",
    "Æ": "Ae",
    "Ö": "O",
}


def transliterate_icelandic(text: str) -> str:
    """Transliterate Icelandic characters to ASCII equivalents."""
    for icelandic, ascii_equiv in ICELANDIC_TRANSLITERATION.items():
        text = text.replace(icelandic, ascii_equiv)
    return text


class ProjectStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ICE_BOX = "ice_box", "Ice Box"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, db_index=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    long_description = models.TextField(max_length=5000, blank=True, null=True)
    website_url = models.URLField(max_length=2083)
    github_url = models.URLField(max_length=2083, blank=True, null=True)
    demo_url = models.URLField(max_length=2083, blank=True, null=True)
    tech_stack = models.JSONField(default=list, blank=True)
    monthly_visitors = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    submission_month = models.CharField(max_length=7, db_index=True)  # YYYY-MM format
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Foreign Keys
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_projects",
    )

    # Many-to-Many
    tags = models.ManyToManyField(Tag, related_name="projects", blank=True)

    class Meta:
        db_table = "projects"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.submission_month:
            self.submission_month = timezone.now().strftime("%Y-%m")
        super().save(*args, **kwargs)


class ProjectView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="views",
    )
    viewer_ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_views"
        unique_together = ["project", "viewer_ip"]

    def __str__(self) -> str:
        return f"{self.project} - {self.viewer_ip}"


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending Upload"
    UPLOADED = "uploaded", "Uploaded"
    FAILED = "failed", "Upload Failed"


class ProjectImage(models.Model):
    """Tracks images uploaded to a project. Uses UUID for non-guessable URLs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="images",
    )

    # Storage details
    storage_key = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()

    # Image metadata
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Ordering and main image tracking
    is_main = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    # Upload status tracking
    upload_status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "project_images"
        ordering = ["display_order", "created_at"]

    def __str__(self) -> str:
        return f"{self.project.title} - {self.original_filename}"

    @property
    def url(self) -> str:
        """Returns the public URL for this image."""
        return f"{settings.S3_PUBLIC_URL_BASE}/{self.storage_key}"


class CompetitionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTING_APPLICATIONS = "accepting_applications", "Accepting Applications"
    CLOSED = "closed", "Closed"


def competition_image_path(instance: "Competition", filename: str) -> str:
    """Generate upload path for competition images."""
    return f"{instance.id}/{filename}"


class Competition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    quote = models.TextField(blank=True, null=True)
    prize_amount = models.IntegerField(default=50000, null=True, blank=True)
    image = models.ImageField(upload_to=competition_image_path, blank=True, null=True)
    projects = models.ManyToManyField(Project, related_name="competitions", blank=True)
    winner = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_competitions",
    )
    status = models.CharField(
        max_length=30,
        choices=CompetitionStatus.choices,
        default=CompetitionStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "competitions"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(transliterate_icelandic(self.name))
        if self.winner is not None:
            self.status = CompetitionStatus.CLOSED
        super().save(*args, **kwargs)

    @property
    def image_url(self) -> str | None:
        """Returns the public URL for the competition image."""
        if self.image:
            return self.image.url
        return None


class ReviewStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class CompetitionReviewer(models.Model):
    """Links a user to a competition they can review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="competition_assignments",
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="reviewers",
    )
    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.IN_PROGRESS,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "competition_reviewers"
        unique_together = ("user", "competition")

    def __str__(self) -> str:
        return f"{self.user} - {self.competition}"


class ProjectRanking(models.Model):
    """A reviewer's ranking of a project within a competition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_rankings",
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="project_rankings",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="rankings",
    )
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_rankings"
        unique_together = [
            ("reviewer", "competition", "project"),
            ("reviewer", "competition", "position"),
        ]
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.reviewer} - {self.project} #{self.position}"
