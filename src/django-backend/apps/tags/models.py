import hashlib
import uuid
from typing import Any

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

# Color palettes per category slug
CATEGORY_COLOR_PALETTES: dict[str, list[str]] = {
    "tech-stack": [
        "#3B82F6",  # Blue
        "#06B6D4",  # Cyan
        "#0EA5E9",  # Sky
        "#6366F1",  # Indigo
        "#8B5CF6",  # Violet
        "#14B8A6",  # Teal
        "#2563EB",  # Blue darker
        "#0891B2",  # Cyan darker
    ],
    "project-status": [
        "#22C55E",  # Green
        "#EAB308",  # Yellow
        "#F97316",  # Orange
        "#EF4444",  # Red
        "#84CC16",  # Lime
        "#10B981",  # Emerald
    ],
    "funding-status": [
        "#A855F7",  # Purple
        "#EC4899",  # Pink
        "#D946EF",  # Fuchsia
        "#8B5CF6",  # Violet
        "#F472B6",  # Pink light
        "#C084FC",  # Purple light
    ],
    "dev-stack": [
        "#F97316",  # Orange
        "#EA580C",  # Orange dark
        "#D97706",  # Amber
        "#CA8A04",  # Yellow dark
        "#92400E",  # Amber dark
        "#B45309",  # Amber medium
    ],
}

# Fallback palette for uncategorized tags or unknown categories
DEFAULT_COLOR_PALETTE = [
    "#6B7280",  # Gray
    "#71717A",  # Zinc
    "#737373",  # Neutral
    "#78716C",  # Stone
    "#64748B",  # Slate
]


def generate_tag_color(tag_name: str, category_slug: str | None) -> str:
    """Generate a consistent color for a tag based on its name and category."""
    palette = CATEGORY_COLOR_PALETTES.get(category_slug or "", DEFAULT_COLOR_PALETTE)
    # Use hash of tag name to pick a color consistently (not for security)
    name_hash = int(
        hashlib.md5(tag_name.lower().encode(), usedforsecurity=False).hexdigest(), 16
    )
    return palette[name_hash % len(palette)]


class TagCategory(models.Model):
    """Categories for organizing tags (e.g., Tech Stack, Project Status)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tag_categories"
        ordering = ["display_order", "name"]
        verbose_name_plural = "Tag categories"

    def __str__(self) -> str:
        return self.name


class TagStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=200, blank=True, null=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a valid hex color.")],
        help_text="Hex color code (e.g., #FF5733)",
    )
    category = models.ForeignKey(
        TagCategory,
        on_delete=models.PROTECT,
        related_name="tags",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=TagStatus.choices,
        default=TagStatus.APPROVED,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tags",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_tags",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Auto-assign color if not set
        if not self.color:
            category_slug = self.category.slug if self.category else None
            self.color = generate_tag_color(self.name, category_slug)
        super().save(*args, **kwargs)
