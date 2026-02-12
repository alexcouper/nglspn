import hashlib

from django.db import migrations
from django.utils.text import slugify

# Color palettes per category slug (same as in models.py)
CATEGORY_COLOR_PALETTES = {
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
    "project-type": [
        "#F97316",  # Orange
        "#EA580C",  # Orange dark
        "#D97706",  # Amber
        "#CA8A04",  # Yellow dark
        "#92400E",  # Amber dark
        "#B45309",  # Amber medium
    ],
}

DEFAULT_COLOR_PALETTE = [
    "#6B7280",  # Gray
    "#71717A",  # Zinc
    "#737373",  # Neutral
    "#78716C",  # Stone
    "#64748B",  # Slate
]

# Default tags per category
DEFAULT_TAGS = {
    "tech-stack": [
        "React",
        "Next.js",
        "Vue",
        "Svelte",
        "Angular",
        "Django",
        "Rails",
        "Node.js",
        "Python",
        "TypeScript",
        "Go",
        "Rust",
        "PostgreSQL",
        "MongoDB",
        "Redis",
        "GraphQL",
        "REST API",
        "AWS",
        "Vercel",
        "Docker",
    ],
    "project-status": [
        "Idea",
        "In Development",
        "MVP",
        "Beta",
        "Live",
        "Mature",
        "Abandoned",
    ],
    "funding-status": [
        "Bootstrapped",
        "Side Project",
        "Pre-seed",
        "Seed",
        "Series A+",
        "Profitable",
        "Open Source",
    ],
    "project-type": [
        "Web App",
        "Mobile App",
        "API",
        "Library",
        "Tool",
        "Community Booster",
        "Society Impact",
    ],
}


def generate_tag_color(tag_name, category_slug):
    """Generate a consistent color for a tag based on its name and category."""
    palette = CATEGORY_COLOR_PALETTES.get(category_slug or "", DEFAULT_COLOR_PALETTE)
    name_hash = int(hashlib.md5(tag_name.lower().encode()).hexdigest(), 16)
    return palette[name_hash % len(palette)]


def assign_colors_and_create_default_tags(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    TagCategory = apps.get_model("tags", "TagCategory")

    # 1. Assign colors to existing tags without colors
    for tag in Tag.objects.filter(color__isnull=True):
        category_slug = tag.category.slug if tag.category else None
        tag.color = generate_tag_color(tag.name, category_slug)
        tag.save()

    # Also update tags with empty string colors
    for tag in Tag.objects.filter(color=""):
        category_slug = tag.category.slug if tag.category else None
        tag.color = generate_tag_color(tag.name, category_slug)
        tag.save()

    # 2. Create default tags for each category
    for category_slug, tag_names in DEFAULT_TAGS.items():
        try:
            category = TagCategory.objects.get(slug=category_slug)
        except TagCategory.DoesNotExist:
            continue

        for tag_name in tag_names:
            tag_slug = slugify(tag_name)
            # Skip if tag already exists
            if Tag.objects.filter(slug=tag_slug).exists():
                continue

            Tag.objects.create(
                name=tag_name,
                slug=tag_slug,
                category=category,
                color=generate_tag_color(tag_name, category_slug),
                status="approved",
            )


def remove_default_tags(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")

    # Remove default tags (by slug)
    all_default_slugs = []
    for tag_names in DEFAULT_TAGS.values():
        all_default_slugs.extend([slugify(name) for name in tag_names])

    Tag.objects.filter(slug__in=all_default_slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tags", "0003_initial_categories"),
    ]

    operations = [
        migrations.RunPython(
            assign_colors_and_create_default_tags,
            remove_default_tags,
        ),
    ]
