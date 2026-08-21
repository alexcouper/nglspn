#!/usr/bin/env python
"""Seed script that mirrors live production data locally.

Fetches projects, tags, categories, and competitions from
api.naglasupan.is, then downloads each referenced image from the prod
CDN and uploads it to local MinIO so the listing renders real
artwork. Re-running picks up new prod projects (idempotent per record).

Projects keep their production UUIDs, so a taxonomy report exported from prod
(docs/taxonomy/) can be applied against this database with `apply_taxonomy`.

Usage:
    uv run python scripts/seed_prod_copy.py
    # or
    make seed-prod-copy
"""

import json
import os
import secrets
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))
DEFAULT_PASSWORD = "123"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from django.utils import timezone
from django.utils.text import slugify

from apps.projects.models import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    EntrySource,
    ImageVariant,
    Project,
    ProjectCategory,
    ProjectImage,
    ProjectStatus,
    UploadStatus,
    VariantSize,
    transliterate_icelandic,
)
from apps.tags.models import Tag, TagStatus
from apps.users.models import User
from services.storage import storage_service

PROD_API_BASE = "https://api.naglasupan.is/api"
PROD_CDN_BASE = "https://cdn.naglasupan.is"

# Fake users to own the projects (creator names aren't shown on listing cards)
USERS = [
    {
        "email": "prodcopy-a@example.com",
        "first_name": "Guðrún",
        "last_name": "Jónsdóttir",
    },
    {
        "email": "prodcopy-b@example.com",
        "first_name": "Ólafur",
        "last_name": "Sigurðsson",
    },
    {
        "email": "prodcopy-c@example.com",
        "first_name": "Helga",
        "last_name": "Þorsteinsdóttir",
    },
    {
        "email": "prodcopy-d@example.com",
        "first_name": "Bjarki",
        "last_name": "Gunnarsson",
    },
    {
        "email": "prodcopy-e@example.com",
        "first_name": "Katrín",
        "last_name": "Magnúsdóttir",
    },
    {
        "email": "prodcopy-f@example.com",
        "first_name": "Einar",
        "last_name": "Haraldsson",
    },
    {
        "email": "prodcopy-g@example.com",
        "first_name": "Sigrún",
        "last_name": "Ólafsdóttir",
    },
]


def _open(url: str, timeout: int) -> Any:
    if not url.startswith(("http://", "https://")):
        msg = f"Refusing to fetch non-http URL: {url}"
        raise ValueError(msg)
    # Percent-encode non-ASCII path/query so urllib doesn't choke (e.g. yrða.is).
    parts = urllib.parse.urlsplit(url)
    safe_path = urllib.parse.quote(parts.path, safe="/%")
    safe_query = urllib.parse.quote(parts.query, safe="=&%")
    encoded = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, safe_path, safe_query, parts.fragment)
    )
    return urllib.request.urlopen(encoded, timeout=timeout)  # noqa: S310


def fetch_json(url: str) -> Any:
    with _open(url, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_bytes(url: str) -> bytes:
    with _open(url, timeout=60) as r:
        return r.read()


def fetch_prod_data() -> tuple[list[dict], list[dict], list[dict], dict[str, str]]:
    """Pull categories, projects, competitions, and project→category map."""
    print("Fetching live data from api.naglasupan.is...")
    categories = fetch_json(f"{PROD_API_BASE}/projects/categories")
    print(f"  Got {len(categories)} categories")

    projects = fetch_json(f"{PROD_API_BASE}/projects?per_page=500")["projects"]
    print(f"  Got {len(projects)} projects")

    competitions = fetch_json(f"{PROD_API_BASE}/competitions")["competitions"]
    print(f"  Got {len(competitions)} competitions")

    project_category: dict[str, str] = {}
    for cat in categories:
        items = fetch_json(f"{PROD_API_BASE}/projects/by-category/{cat['slug']}")
        for it in items:
            project_category[it["id"]] = cat["slug"]
        print(f"    Category {cat['slug']!r}: {len(items)} projects")

    return categories, projects, competitions, project_category


def generate_kennitala() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(10))


def create_users() -> list[User]:
    print("\nCreating users...")
    created = []
    for u in USERS:
        user, was_created = User.objects.get_or_create(
            email=u["email"],
            defaults={
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "kennitala": generate_kennitala(),
                "is_verified": True,
            },
        )
        if was_created:
            user.set_password(DEFAULT_PASSWORD)
            user.save()
            print(f"  Created user: {user.email}")
        else:
            print(f"  User already exists: {user.email}")
        created.append(user)
    return created


def create_categories(categories: list[dict]) -> dict[str, ProjectCategory]:
    print("\nCreating categories...")
    by_slug: dict[str, ProjectCategory] = {}
    for i, c in enumerate(categories):
        cat, was_created = ProjectCategory.objects.get_or_create(
            slug=c["slug"],
            defaults={"name": c["name"], "display_order": i},
        )
        if cat.name != c["name"] or cat.display_order != i:
            cat.name = c["name"]
            cat.display_order = i
            cat.save(update_fields=["name", "display_order"])
        by_slug[c["slug"]] = cat
        print(f"  {'Created' if was_created else 'Exists '}: {cat.name}")
    return by_slug


def get_or_create_tag(tag_data: dict) -> Tag | None:
    """Match tag by name; create with prod slug + color if missing."""
    name = tag_data["name"]
    found = Tag.objects.filter(name=name).first()
    if found:
        return found

    slug = tag_data.get("slug") or slugify(transliterate_icelandic(name))
    if Tag.objects.filter(slug=slug).exists():
        print(f"    Skipping tag {name!r}: slug {slug!r} already taken")
        return None
    return Tag.objects.create(
        name=name,
        slug=slug,
        color=tag_data.get("color") or "#888888",
        status=TagStatus.APPROVED,
    )


def derive_website_url(prod: dict) -> str:
    """Best-effort website URL when prod listing only gives us a slug/title."""
    title = prod["title"]
    if "." in title and " " not in title:
        return f"https://{title.lower()}"
    return f"https://example.com/{prod['slug']}"


def create_projects(
    project_data: list[dict],
    project_category: dict[str, str],
    categories_by_slug: dict[str, ProjectCategory],
    users: list[User],
    admin: User | None,
) -> dict[str, Project]:
    print("\nCreating projects...")
    by_prod_id: dict[str, Project] = {}

    for i, pd in enumerate(project_data):
        creator = users[i % len(users)]

        cat_slug = project_category.get(pd["id"])
        category = categories_by_slug.get(cat_slug) if cat_slug else None

        # Keep the prod UUID as the local primary key. `apply_taxonomy` matches
        # a report's projects on `id` and aborts on any it cannot find, so a
        # copy with fresh ids is a copy no taxonomy report can be applied to.
        prod_id = UUID(pd["id"])
        existing = Project.objects.filter(pk=prod_id).first()
        if existing:
            project = existing
            print(f"  Exists : {project.title}")
        else:
            created_at = datetime.fromisoformat(pd["created_at"])
            project = Project.objects.create(
                id=prod_id,
                title=pd["title"],
                tagline=pd.get("tagline") or "",
                description=pd.get("tagline")
                or f"{pd['title']} — an Icelandic community project.",
                website_url=derive_website_url(pd),
                tech_stack=[],
                status=ProjectStatus.APPROVED,
                submission_month=created_at.strftime("%Y-%m"),
                category=category,
                creator=creator,
                approved_by=admin,
                approved_at=created_at,
                published_at=created_at,
            )
            for tag_data in pd.get("tags") or []:
                tag = get_or_create_tag(tag_data)
                if tag:
                    project.tags.add(tag)
            print(f"  Created: {project.title}")

        # Make category assignment idempotent (re-run picks up prod re-categorisations).
        new_cat_id = category.id if category else None
        if project.category_id != new_cat_id:
            project.category = category
            project.save(update_fields=["category"])

        by_prod_id[pd["id"]] = project

    return by_prod_id


def guess_content_type(url: str) -> str:
    ext = url.rsplit(".", 1)[-1].lower()
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "application/octet-stream")


def mirror_image(cdn_url: str) -> tuple[str | None, bool]:
    """Download from prod CDN and upload to MinIO if missing.

    Returns (storage_key, uploaded_now). storage_key is None when the URL
    is unreachable; uploaded_now is False when the object already existed.
    """
    if not cdn_url.startswith(f"{PROD_CDN_BASE}/"):
        return None, False
    storage_key = cdn_url[len(PROD_CDN_BASE) + 1 :]
    if storage_service.object_exists(storage_key):
        return storage_key, False
    try:
        data = fetch_bytes(cdn_url)
    except urllib.error.URLError as e:
        print(f"    download failed {cdn_url}: {e}")
        return None, False
    storage_service.upload_object(storage_key, data, guess_content_type(cdn_url))
    return storage_key, True


def create_project_images(
    project_data: list[dict], by_prod_id: dict[str, Project]
) -> int:
    """Mirror main image + thumb to MinIO and create DB records."""
    print("\nMirroring project images to MinIO...")
    count = 0

    for pd in project_data:
        project = by_prod_id.get(pd["id"])
        if not project:
            continue

        main_url = pd.get("main_image_url")
        thumb_url = pd.get("main_image_thumb_url")
        if not main_url or not thumb_url:
            continue

        parent_key, parent_uploaded = mirror_image(main_url)
        thumb_key, thumb_uploaded = mirror_image(thumb_url)
        if not parent_key or not thumb_key:
            continue

        filename = parent_key.rsplit("/", 1)[-1]
        image, image_created = ProjectImage.objects.get_or_create(
            project=project,
            storage_key=parent_key,
            defaults={
                "original_filename": filename,
                "content_type": guess_content_type(main_url),
                "file_size": 0,
                "is_main": True,
                "display_order": 0,
                "upload_status": UploadStatus.UPLOADED,
                "uploaded_at": timezone.now(),
            },
        )
        _, variant_created = ImageVariant.objects.get_or_create(
            image=image,
            size=VariantSize.THUMB,
            defaults={
                "storage_key": thumb_key,
                "width": 384,
                "height": 216,
                "file_size": 0,
            },
        )
        if image_created or parent_uploaded or thumb_uploaded or variant_created:
            count += 1
            print(f"  Mirrored: {project.title}")

    return count


def create_competitions(
    competitions_data: list[dict],
    project_data: list[dict],
    by_prod_id: dict[str, Project],
) -> None:
    """Recreate competitions for projects flagged as winners on prod."""
    print("\nCreating competitions for winners...")
    by_slug = {c["slug"]: c for c in competitions_data}

    for pd in project_data:
        project = by_prod_id.get(pd["id"])
        if not project:
            continue
        for w in pd.get("won_competitions") or []:
            comp_data = by_slug.get(w["slug"])
            if not comp_data:
                continue

            comp, was_created = Competition.objects.get_or_create(
                name=comp_data["name"],
                defaults={
                    "start_date": comp_data["start_date"],
                    "submission_deadline": comp_data["submission_deadline"],
                    "voting_end_date": comp_data.get("voting_end_date"),
                    "prize_amount": int(comp_data.get("prize_amount") or 50000),
                    "status": CompetitionStatus.CLOSED,
                    "winner": project,
                },
            )
            if not was_created and comp.winner_id != project.id:
                comp.winner = project
                comp.status = CompetitionStatus.CLOSED
                comp.save(update_fields=["winner", "status"])
            CompetitionEntry.objects.get_or_create(
                competition=comp,
                project=project,
                defaults={"entered_via": EntrySource.BACKFILL},
            )
            verb = "Created" if was_created else "Exists "
            print(f"  {verb}: {comp.name} (winner: {project.title})")


def main() -> None:
    print("=== Seeding database with production-like data ===\n")

    categories_data, projects_data, competitions_data, project_category = (
        fetch_prod_data()
    )

    admin = User.objects.filter(is_staff=True).first()
    users = create_users()
    categories_by_slug = create_categories(categories_data)
    by_prod_id = create_projects(
        projects_data, project_category, categories_by_slug, users, admin
    )
    image_count = create_project_images(projects_data, by_prod_id)
    create_competitions(competitions_data, projects_data, by_prod_id)

    print("\n=== Prod-copy seed complete ===")
    print(f"  Categories: {len(categories_by_slug)}")
    print(f"  Users:      {len(users)}")
    print(f"  Projects:   {len(by_prod_id)}")
    print(f"  Images:     {image_count}")
    print(f"\nAll seed users have password: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
