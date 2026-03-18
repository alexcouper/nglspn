#!/usr/bin/env python
"""Seed script that replicates production project data locally.

Creates projects matching what's visible on naglasupan.is/projects,
using real titles, taglines, tags, and CDN image references so the
project listing looks identical to production.

Temporary script for UI development — not intended to be kept long-term.

Usage:
    uv run python scripts/seed_prod_copy.py
    # or
    make seed-prod-copy
"""

import os
import secrets
import string
import sys
from pathlib import Path

DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))
DEFAULT_PASSWORD = "123"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from django.utils import timezone

from apps.projects.models import (
    Competition,
    CompetitionStatus,
    ImageVariant,
    Project,
    ProjectImage,
    ProjectStatus,
    UploadStatus,
    VariantSize,
)
from apps.tags.models import Tag
from apps.users.models import User

SEED_MARKER_EMAIL = "prod-copy-marker@naglasupan.is"

# Fake users to own the projects (owner names aren't shown on listing cards)
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

# Production projects as seen on naglasupan.is/projects (March 2026).
# Image storage keys are derived from the CDN thumb URLs.
# Each entry has the thumb variant storage key (what the listing actually uses)
# and we derive the parent image storage key from it.
PROJECTS = [
    {
        "title": "Accessibility Scanner",
        "tagline": "",
        "tag_names": ["Library", "Open Source", "Society Impact"],
        "thumb_storage_key": None,
    },
    {
        "title": "boardroomkids.vercel.app",
        "tagline": "Tiny tools for big thinkers",
        "tag_names": ["In Development", "Live", "Next.js", "Vercel"],
        "thumb_storage_key": "projects/ed4369f2-6a56-4057-9d26-92f6d908fb92/e7ae67d8e815/IMG_8621/thumb.webp",
    },
    {
        "title": "Clusters",
        "tagline": "",
        "tag_names": [
            "Live",
            "Next.js",
            "React",
            "REST API",
            "Side Project",
            "Supabase",
        ],
        "thumb_storage_key": None,
    },
    {
        "title": "codeclip.link",
        "tagline": "",
        "tag_names": [
            "Next.js",
            "PostgreSQL",
            "React",
            "Side Project",
            "Supabase",
            "Tailwind",
            "TypeScript",
            "Vercel",
            "Web App",
        ],
        "thumb_storage_key": "projects/e904525f-f27d-4c6b-99f9-83ecfb2be87a/262962d035c5/Screenshot2026-02-10at19.56.49/thumb.webp",
    },
    {
        "title": "Code Snippet Manager",
        "tagline": "Your code, always findable.",
        "tag_names": [
            "Developer tool",
            "In Development",
            "Neon",
            "Next.js",
            "PostgreSQL",
            "React",
            "Render",
            "Side Project",
            "Tailwind",
            "TypeScript",
            "Vercel",
            "Web App",
        ],
        "thumb_storage_key": "projects/f97d1047-5952-4ae0-8b68-61fa6c53d0f0/746014345242/Screenshot2026-03-03at12.09.38/thumb.webp",
    },
    {
        "title": "digitalmap.atli.io",
        "tagline": "",
        "tag_names": ["Society Impact", "Web App"],
        "thumb_storage_key": "projects/0e9fae2a-815a-43fc-a8a6-73c71a54f432/f89bd5eab16c/Screenshot2026-02-10144530/thumb.webp",
    },
    {
        "title": "eventa.is",
        "tagline": "Stafrænt viðburðartorg á Íslandi",
        "tag_names": [
            "In Development",
            "Live",
            "Mobile App",
            "Side Project",
            "Web App",
        ],
        "thumb_storage_key": "projects/39e1b712-5e23-4499-b3bd-2426e24e86df/56794122dd32/548044085_10236021217248061_8795799132438416102_n/thumb.webp",
    },
    {
        "title": "Gasvaktin",
        "tagline": "",
        "tag_names": ["Open Source", "Society Impact", "Web App"],
        "thumb_storage_key": "projects/d4afe752-200a-49fc-a0c2-ef95e1bc50f0/c930f1695243/68747470733a2f2f67617376616b74696e2e69732f696d616765732f67617376616b74696e2e706e67/thumb.webp",
    },
    {
        "title": "keep.is",
        "tagline": "A private timeline for your life.",
        "tag_names": [
            "In Development",
            "Mature",
            "Nuxt",
            "Supabase",
            "Tailwind",
            "Vercel",
            "Vue",
            "Web App",
        ],
        "thumb_storage_key": "projects/52c0f1d3-dc82-4faa-a546-02cf627c54e0/b20868a85824/keep/thumb.webp",
    },
    {
        "title": "leiksvæði.is",
        "tagline": "",
        "tag_names": [
            "Live",
            "Next.js",
            "Node.js",
            "Supabase",
            "Tailwind",
            "TypeScript",
            "Vercel",
            "Web App",
        ],
        "thumb_storage_key": "projects/200773b6-84dc-44a0-826f-ab7b722da705/385e1cb8dae1/1000019353/thumb.webp",
    },
    {
        "title": "Loka-Orð",
        "tagline": "",
        "tag_names": ["Library", "Open Source", "Society Impact"],
        "thumb_storage_key": "projects/a4d9ed43-8b3f-4983-8a80-e2b7a8478d21/727f2b33700d/ScreenshotFrom2026-01-2412-14-38/thumb.webp",
    },
    {
        "title": "minskimun.is",
        "tagline": "",
        "tag_names": ["Community Booster", "In Development", "React", "Vite"],
        "thumb_storage_key": "projects/87ee8849-cdb9-48b5-9df6-1d62d07fba92/2be42cdcec17/Screenshot2026-03-09at21.06.41/thumb.webp",
    },
    {
        "title": "morphvox.net",
        "tagline": "",
        "tag_names": ["Open Source", "Web App"],
        "thumb_storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/313c1c7241b8/10/thumb.webp",
    },
    {
        "title": "Naglasúpan",
        "tagline": "Byggjum, deilum, vöxum saman.",
        "tag_names": [
            "Bootstrapped",
            "Community Booster",
            "Django",
            "Live",
            "Next.js",
            "Open Source",
            "PostgreSQL",
            "Web App",
        ],
        "thumb_storage_key": "projects/f44fcbf5-8737-4beb-bdaf-94a3f8c15446/4a0024564ec7/banner/thumb.webp",
    },
    {
        "title": "open.mannvaen.is",
        "tagline": "",
        "tag_names": [
            "Community Booster",
            "Idea",
            "Neon",
            "Next.js",
            "PostgreSQL",
            "Side Project",
            "Tailwind",
            "TypeScript",
            "Vercel",
            "Web App",
        ],
        "thumb_storage_key": "projects/49a7092e-ac25-4631-bc69-7831f0a3dd40/7d757df7fa1b/Screenshot2026-02-10144530/thumb.webp",
    },
    {
        "title": "postwall.app",
        "tagline": "A collaborative whiteboard for your stickies!",
        "tag_names": [
            "Firebase",
            "Firestore",
            "Live",
            "React",
            "Side Project",
            "Tool",
            "Vite",
            "Web App",
        ],
        "thumb_storage_key": "projects/b7c0d4d4-6a3b-486a-985b-e8267b65163c/ea19e8907008/Screenshot2026-03-05at10.40.52/thumb.webp",
    },
    {
        "title": "Prótó",
        "tagline": "",
        "tag_names": ["Community Booster", "Web App"],
        "thumb_storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/e791028885a6/1-frontpage/thumb.webp",
    },
    {
        "title": "rastimar.golf.is",
        "tagline": "",
        "tag_names": [
            "Live",
            "Node.js",
            "PostgreSQL",
            "Remix",
            "Side Project",
            "Society Impact",
            "Tailwind",
            "Vercel",
            "Web App",
        ],
        "thumb_storage_key": "projects/1beac070-fc4e-46c0-91e5-57744b6167bc/7f3221e40377/Screenshot2026-02-08at14.20.07/thumb.webp",
    },
    {
        "title": "rocketleague.is",
        "tagline": "",
        "tag_names": [
            "Live",
            "Next.js",
            "PostgreSQL",
            "Side Project",
            "Supabase",
            "Tailwind",
            "Web App",
        ],
        "thumb_storage_key": "projects/90a6adb3-63f6-49fb-ad4a-d75bae4fc397/b851a3ce3a9a/Screenshot2026-02-06132051/thumb.webp",
    },
    {
        "title": "roommate",
        "tagline": "",
        "tag_names": [],
        "thumb_storage_key": None,
    },
]

# Projects that won competitions (visible as trophy on listing)
COMPETITION_WINNERS = {
    "keep.is": "Sellerí",
    "morphvox.net": "Laukur",
    "rastimar.golf.is": "Gulrót",
}


def generate_kennitala() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(10))


def create_users() -> list[User]:
    print("Creating users...")
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


def create_projects(users: list[User], admin: User | None) -> list[Project]:
    print("\nCreating projects...")
    created = []
    tag_cache: dict[str, Tag] = {}

    for i, p in enumerate(PROJECTS):
        owner = users[i % len(users)]

        if Project.objects.filter(title=p["title"]).exists():
            project = Project.objects.get(title=p["title"])
            print(f"  Project already exists: {project.title}")
            created.append(project)
            continue

        project = Project.objects.create(
            title=p["title"],
            tagline=p.get("tagline", ""),
            description=p.get("tagline", "")
            or f"{p['title']} — an Icelandic community project.",
            website_url=f"https://{p['title'].lower().replace(' ', '')}"
            if "." not in p["title"]
            else f"https://{p['title'].lower()}",
            tech_stack=[],
            status=ProjectStatus.APPROVED,
            submission_month=f"2026-{(i % 3) + 1:02d}",
            owner=owner,
            approved_by=admin,
            approved_at=timezone.now(),
        )

        for tag_name in p.get("tag_names", []):
            if tag_name not in tag_cache:
                tag = Tag.objects.filter(name=tag_name).first()
                if tag:
                    tag_cache[tag_name] = tag
                else:
                    print(f"    Tag not found: {tag_name}")
            if tag_name in tag_cache:
                project.tags.add(tag_cache[tag_name])

        print(f"  Created project: {project.title}")
        created.append(project)

    return created


def create_project_images(projects: list[Project]) -> int:
    """Create ProjectImage + ImageVariant records using production CDN keys.

    The listing page uses main_image_thumb_url which comes from the
    ImageVariant (size=thumb). We create both the parent ProjectImage
    and the thumb variant so the listing renders real images from the CDN.
    """
    print("\nCreating project images...")
    count = 0

    project_map = {p.title: p for p in projects}

    for p_data in PROJECTS:
        thumb_key = p_data.get("thumb_storage_key")
        if not thumb_key:
            continue

        project = project_map.get(p_data["title"])
        if not project:
            continue
        if project.images.exists():
            print(f"  Images already exist for: {project.title}")
            continue

        # Derive parent image storage key from thumb key.
        # Thumb key: projects/{uuid}/{hash}/{name}/thumb.webp
        # Parent key: projects/{uuid}/{hash}/{name}.png
        parent_key = thumb_key.rsplit("/thumb.webp", 1)[0] + ".png"
        filename = parent_key.rsplit("/", 1)[-1]

        image = ProjectImage.objects.create(
            project=project,
            storage_key=parent_key,
            original_filename=filename,
            content_type="image/png",
            file_size=0,
            is_main=True,
            display_order=0,
            upload_status=UploadStatus.UPLOADED,
            uploaded_at=timezone.now(),
        )

        ImageVariant.objects.create(
            image=image,
            size=VariantSize.THUMB,
            storage_key=thumb_key,
            width=384,
            height=216,
            file_size=0,
        )

        count += 1
        print(f"  Added image + thumb for: {project.title}")

    return count


def create_competitions(projects: list[Project]) -> None:
    """Create competitions so winner badges show on the listing."""
    print("\nCreating competitions for winners...")

    for project_title, comp_name in COMPETITION_WINNERS.items():
        if Competition.objects.filter(name=comp_name).exists():
            print(f"  Competition already exists: {comp_name}")
            continue

        project = next((p for p in projects if p.title == project_title), None)
        if not project:
            print(f"  Project not found for winner: {project_title}")
            continue

        comp = Competition.objects.create(
            name=comp_name,
            start_date="2026-01-01",
            end_date="2026-01-31",
            quote="",
            prize_amount=50000,
            status=CompetitionStatus.CLOSED,
            winner=project,
        )
        comp.projects.add(project)
        print(f"  Created competition: {comp_name} (winner: {project_title})")


def main() -> None:
    if User.objects.filter(email=SEED_MARKER_EMAIL).exists():
        print("Prod-copy seed data already exists. To re-seed, delete the marker user:")
        print(f"  User.objects.filter(email='{SEED_MARKER_EMAIL}').delete()")
        print("Then run this script again.")
        return

    print("=== Seeding database with production-like data ===\n")

    admin = User.objects.filter(is_staff=True).first()

    users = create_users()
    projects = create_projects(users, admin)
    image_count = create_project_images(projects)
    create_competitions(projects)

    User.objects.create(
        email=SEED_MARKER_EMAIL,
        kennitala=generate_kennitala(),
        first_name="ProdCopy",
        last_name="Marker",
        is_active=False,
    )

    print("\n=== Prod-copy seed complete ===")
    print(f"  Users:    {len(users)}")
    print(f"  Projects: {len(projects)}")
    print(f"  Images:   {image_count}")
    print(f"\nAll seed users have password: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
