#!/usr/bin/env python
"""Seed script to populate the database with sample data.

Creates users, projects (with various statuses), and competitions
for development and demo purposes. Safe to run multiple times -
skips creation if seed data already exists.

Usage:
    uv run python scripts/seed_db.py
    # or
    make seed
"""

import os
import random
import secrets
import string
import sys
from datetime import date
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
    CompetitionReviewer,
    CompetitionStatus,
    Project,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
    UploadStatus,
)
from apps.tags.models import Tag
from apps.users.models import User

SEED_MARKER_EMAIL = "seed-marker@naglasupan.is"

USERS = [
    {"email": "anna@example.com", "first_name": "Anna", "last_name": "Sigurdsson"},
    {"email": "bjarki@example.com", "first_name": "Bjarki", "last_name": "Thorsson"},
    {"email": "dagny@example.com", "first_name": "Dagny", "last_name": "Helgadottir"},
    {"email": "einar@example.com", "first_name": "Einar", "last_name": "Jonsson"},
    {
        "email": "freyja@example.com",
        "first_name": "Freyja",
        "last_name": "Magnusdottir",
    },
    {"email": "gunnar@example.com", "first_name": "Gunnar", "last_name": "Olafsson"},
    {"email": "helga@example.com", "first_name": "Helga", "last_name": "Bjornsdottir"},
    {
        "email": "ingvar@example.com",
        "first_name": "Ingvar",
        "last_name": "Kristjansson",
    },
    {
        "email": "katrin@example.com",
        "first_name": "Katrin",
        "last_name": "Gudmundsdottir",
    },
    {"email": "leifur@example.com", "first_name": "Leifur", "last_name": "Haraldsson"},
]

PROJECTS = [
    {
        "title": "Reykjavik Bikes",
        "tagline": "Bike-sharing made easy for Reykjavik commuters",
        "description": "A bike-sharing platform for the Reykjavik metro area with real-time availability tracking.",
        "long_description": "Reykjavik Bikes connects cyclists with available bikes across the city. Features include live station maps, trip planning, and monthly subscription management. Built to promote sustainable transport in Iceland's capital.",
        "website_url": "https://reykjavikbikes.example.com",
        "github_url": "https://github.com/example/reykjavik-bikes",
        "tech_stack": ["React", "Node.js", "PostgreSQL"],
        "monthly_visitors": 12000,
        "status": ProjectStatus.APPROVED,
        "tag_names": ["React", "Node.js", "Web App", "Live", "Side Project"],
    },
    {
        "title": "Northern Lights Tracker",
        "tagline": "Never miss the aurora again",
        "description": "Real-time aurora borealis forecasting app for Iceland using ML-based prediction models.",
        "long_description": "Uses satellite data and machine learning to predict aurora visibility across Iceland. Sends push notifications when conditions are optimal for your location.",
        "website_url": "https://aurora.example.com",
        "tech_stack": ["Python", "React", "AWS"],
        "monthly_visitors": 45000,
        "status": ProjectStatus.APPROVED,
        "tag_names": ["Python", "React", "AWS", "Web App", "Live", "Bootstrapped"],
    },
    {
        "title": "Icelandic Recipe Box",
        "tagline": "Traditional Icelandic flavors, one recipe at a time",
        "description": "A curated collection of traditional and modern Icelandic recipes with ingredient sourcing.",
        "website_url": "https://recipes.example.com",
        "tech_stack": ["Next.js", "PostgreSQL"],
        "monthly_visitors": 8500,
        "status": ProjectStatus.APPROVED,
        "tag_names": ["Next.js", "PostgreSQL", "Web App", "Live", "Side Project"],
    },
    {
        "title": "Saga Reader",
        "tagline": "Bringing ancient sagas to modern readers",
        "description": "Interactive reader for Icelandic sagas with modern Icelandic translations and annotations.",
        "long_description": "Makes the Icelandic sagas accessible to modern readers. Features side-by-side Old Norse and modern Icelandic text, vocabulary tools, and cultural annotations.",
        "website_url": "https://sagareader.example.com",
        "github_url": "https://github.com/example/saga-reader",
        "tech_stack": ["Svelte", "Django", "PostgreSQL"],
        "monthly_visitors": 3200,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Svelte",
            "Django",
            "PostgreSQL",
            "Web App",
            "Mature",
            "Open Source",
            "Society Impact",
        ],
    },
    {
        "title": "Volcanic Alert",
        "tagline": "Stay ahead of Iceland's volcanic activity",
        "description": "Early warning system for volcanic activity around Iceland with live seismic data.",
        "website_url": "https://volcanic.example.com",
        "tech_stack": ["Python", "TypeScript", "Redis", "Docker"],
        "monthly_visitors": 22000,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Python",
            "TypeScript",
            "Redis",
            "Docker",
            "Live",
            "Open Source",
            "Society Impact",
        ],
        "is_featured": True,
    },
    {
        "title": "Fish Market API",
        "tagline": "Real-time fish prices from every harbor in Iceland",
        "description": "Open API for real-time Icelandic fish market prices and catch data.",
        "long_description": "Provides structured access to fish auction data from harbors across Iceland. Used by restaurants, retailers, and researchers to track seafood pricing trends.",
        "website_url": "https://fishapi.example.com",
        "github_url": "https://github.com/example/fish-market-api",
        "tech_stack": ["Django", "REST API", "PostgreSQL", "Docker"],
        "monthly_visitors": 5400,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Django",
            "REST API",
            "PostgreSQL",
            "Docker",
            "API",
            "Live",
            "Open Source",
        ],
    },
    {
        "title": "Geyser Monitor",
        "tagline": "Live geothermal insights at your fingertips",
        "description": "IoT monitoring dashboard for geothermal activity at popular tourist sites.",
        "website_url": "https://geyser.example.com",
        "tech_stack": ["Vue", "Go", "Redis"],
        "monthly_visitors": 1800,
        "status": ProjectStatus.APPROVED,
        "tag_names": ["Vue", "Go", "Redis", "Web App", "Beta", "Pre-seed"],
    },
    {
        "title": "Reykjavik Events",
        "tagline": "Discover what's happening in Reykjavik tonight",
        "description": "Community-driven event discovery platform for the greater Reykjavik area.",
        "website_url": "https://events.example.com",
        "tech_stack": ["Next.js", "Node.js", "MongoDB"],
        "monthly_visitors": 15000,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Next.js",
            "Node.js",
            "MongoDB",
            "Web App",
            "Live",
            "Bootstrapped",
            "Community Booster",
        ],
        "is_featured": True,
    },
    {
        "title": "Wool Marketplace",
        "tagline": "Connecting Icelandic wool with the world",
        "description": "E-commerce platform connecting Icelandic wool producers with international buyers.",
        "website_url": "https://woolmarket.example.com",
        "tech_stack": ["Django", "React", "PostgreSQL", "AWS"],
        "monthly_visitors": 6700,
        "status": ProjectStatus.PENDING,
        "tag_names": ["Django", "React", "PostgreSQL", "AWS", "Web App", "MVP", "Seed"],
    },
    {
        "title": "Icelandic Language Tutor",
        "tagline": "Learn Icelandic with AI-powered lessons",
        "description": "AI-powered Icelandic language learning app with speech recognition and grammar exercises.",
        "website_url": "https://learnIS.example.com",
        "tech_stack": ["React", "Python", "AWS"],
        "monthly_visitors": 0,
        "status": ProjectStatus.PENDING,
        "tag_names": [
            "React",
            "Python",
            "AWS",
            "Web App",
            "In Development",
            "Pre-seed",
        ],
    },
    {
        "title": "Puffin Tracker",
        "tagline": "Monitoring Iceland's puffin colonies for conservation",
        "description": "Wildlife conservation tool tracking puffin colony populations across Iceland.",
        "website_url": "https://puffins.example.com",
        "github_url": "https://github.com/example/puffin-tracker",
        "tech_stack": ["Python", "React", "PostgreSQL"],
        "monthly_visitors": 2100,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Python",
            "React",
            "PostgreSQL",
            "Web App",
            "Beta",
            "Open Source",
            "Society Impact",
        ],
    },
    {
        "title": "Hot Spring Finder",
        "tagline": "Find your perfect hot spring anywhere in Iceland",
        "description": "GPS-based app for discovering natural hot springs across Iceland with safety ratings.",
        "website_url": "https://hotsprings.example.com",
        "tech_stack": ["React", "Node.js", "MongoDB"],
        "monthly_visitors": 31000,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "React",
            "Node.js",
            "MongoDB",
            "Mobile App",
            "Live",
            "Bootstrapped",
        ],
    },
    {
        "title": "Glacier Watch",
        "tagline": "Visualizing a century of glacier change in Iceland",
        "description": "Dashboard visualizing glacier retreat data across Iceland over the past century.",
        "website_url": "https://glacierwatch.example.com",
        "tech_stack": ["Svelte", "Python", "PostgreSQL"],
        "monthly_visitors": 0,
        "status": ProjectStatus.PENDING,
        "tag_names": ["Svelte", "Python", "PostgreSQL", "Tool", "Idea", "Open Source"],
    },
    {
        "title": "Startup Iceland Hub",
        "tagline": "The home for Iceland's startup community",
        "description": "Directory and networking platform for the Icelandic startup ecosystem.",
        "website_url": "https://startuphub.example.com",
        "tech_stack": ["Next.js", "Django", "PostgreSQL", "Vercel"],
        "monthly_visitors": 9200,
        "status": ProjectStatus.APPROVED,
        "tag_names": [
            "Next.js",
            "Django",
            "PostgreSQL",
            "Vercel",
            "Web App",
            "Live",
            "Seed",
            "Community Booster",
        ],
        "is_featured": True,
    },
    {
        "title": "Renewable Energy Dashboard",
        "tagline": "Iceland's clean energy grid in real time",
        "description": "Real-time monitoring of Iceland's renewable energy grid including geothermal and hydro.",
        "website_url": "https://energy.example.com",
        "tech_stack": ["Angular", "Go", "GraphQL", "Docker"],
        "monthly_visitors": 4300,
        "status": ProjectStatus.REJECTED,
        "rejection_reason": "Very similar to an existing approved project. Consider collaborating with the Volcanic Alert team.",
        "tag_names": ["Angular", "Go", "GraphQL", "Docker", "Tool", "In Development"],
    },
    {
        "title": "Whaler's Archive",
        "tagline": "Preserving Iceland's whaling history digitally",
        "description": "Digital archive preserving historical Icelandic whaling records and photographs.",
        "website_url": "https://whalearchive.example.com",
        "tech_stack": ["Django", "PostgreSQL", "AWS"],
        "monthly_visitors": 800,
        "status": ProjectStatus.ICE_BOX,
        "tag_names": [
            "Django",
            "PostgreSQL",
            "AWS",
            "Web App",
            "Abandoned",
            "Open Source",
        ],
    },
]

# Real image storage keys from production CDN (cdn.naglasupan.is).
# Mapped to seed projects so they have realistic screenshots.
PROJECT_IMAGES: dict[str, list[dict[str, str]]] = {
    "Reykjavik Bikes": [
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/76b8c24d336d/1.png",
            "filename": "1.png",
        },
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/356ed9c9e2a0/2.png",
            "filename": "2.png",
        },
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/dd2537c6c91b/3.png",
            "filename": "3.png",
        },
    ],
    "Northern Lights Tracker": [
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/60a9fb3a7ccc/4.png",
            "filename": "4.png",
        },
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/474347497f65/5.png",
            "filename": "5.png",
        },
    ],
    "Icelandic Recipe Box": [
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/c2986b0f7af8/6.png",
            "filename": "6.png",
        },
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/276193cb521a/7.png",
            "filename": "7.png",
        },
    ],
    "Saga Reader": [
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/e791028885a6/1-frontpage.png",
            "filename": "1-frontpage.png",
        },
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/496f29c526ec/2-login.png",
            "filename": "2-login.png",
        },
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/54ffbb034230/3-mitt-svaedi.png",
            "filename": "3-mitt-svaedi.png",
        },
    ],
    "Volcanic Alert": [
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/47f4c09e2bf7/4-edit-profile.png",
            "filename": "4-edit-profile.png",
        },
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/e87d6e54eccd/5-material.png",
            "filename": "5-material.png",
        },
    ],
    "Fish Market API": [
        {
            "storage_key": "projects/d4afe752-200a-49fc-a0c2-ef95e1bc50f0/c930f1695243/68747470733a2f2f67617376616b74696e2e69732f696d616765732f67617376616b74696e2e706e67.png",
            "filename": "gasvaktin.png",
        },
    ],
    "Geyser Monitor": [
        {
            "storage_key": "projects/7e0593da-2d20-428e-b3a6-96235d3bc7d3/d6c6a9285b7d/create.png",
            "filename": "create.png",
        },
        {
            "storage_key": "projects/7e0593da-2d20-428e-b3a6-96235d3bc7d3/5eb25c182bdb/pick-beers.png",
            "filename": "pick-beers.png",
        },
    ],
    "Reykjavik Events": [
        {
            "storage_key": "projects/7e0593da-2d20-428e-b3a6-96235d3bc7d3/7da7b4b15fa7/rate-beer.png",
            "filename": "rate-beer.png",
        },
        {
            "storage_key": "projects/7e0593da-2d20-428e-b3a6-96235d3bc7d3/d273450356f8/smakk.app_.png",
            "filename": "smakk.app.png",
        },
    ],
    "Puffin Tracker": [
        {
            "storage_key": "projects/55144197-7223-4f16-9a13-09245acba2a1/9a658ef5b7bc/Screenshot2026-01-01at14.35.52.png",
            "filename": "Screenshot2026-01-01at14.35.52.png",
        },
    ],
    "Hot Spring Finder": [
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/ee41aecd5166/6-material-details.png",
            "filename": "6-material-details.png",
        },
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/106fd1f924f5/7-projects.png",
            "filename": "7-projects.png",
        },
        {
            "storage_key": "projects/ab979d64-d5bb-4dcc-8f1a-74d2c1189dfd/cd9faa2e0320/8-project-details.png",
            "filename": "8-project-details.png",
        },
    ],
    "Startup Iceland Hub": [
        {
            "storage_key": "projects/f44fcbf5-8737-4beb-bdaf-94a3f8c15446/4fb847781f39/naglasupan.png",
            "filename": "naglasupan.png",
        },
        {
            "storage_key": "projects/a4d9ed43-8b3f-4983-8a80-e2b7a8478d21/727f2b33700d/ScreenshotFrom2026-01-2412-14-38.png",
            "filename": "ScreenshotFrom2026-01-2412-14-38.png",
        },
    ],
    "Wool Marketplace": [
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/be3ba26a557a/8.png",
            "filename": "8.png",
        },
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/6bf5cb291c7b/9.png",
            "filename": "9.png",
        },
    ],
    "Whaler's Archive": [
        {
            "storage_key": "projects/898b8389-9afd-4786-ace5-2d99e6899c74/313c1c7241b8/10.png",
            "filename": "10.png",
        },
    ],
}

COMPETITIONS = [
    {
        "name": "Janúar keppni 2025",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 1, 31),
        "quote": "Celebrating Iceland's most innovative projects.",
        "prize_amount": 50000,
        "status": CompetitionStatus.CLOSED,
        "project_count": 5,
        "pick_winner": True,
    },
    {
        "name": "Febrúar keppni 2025",
        "start_date": date(2025, 2, 1),
        "end_date": date(2025, 2, 28),
        "quote": "Building the future of Icelandic tech.",
        "prize_amount": 50000,
        "status": CompetitionStatus.CLOSED,
        "project_count": 5,
        "pick_winner": True,
    },
    {
        "name": "Mars keppni 2025",
        "start_date": date(2025, 3, 1),
        "end_date": date(2025, 3, 31),
        "quote": "Spring into innovation.",
        "prize_amount": 75000,
        "status": CompetitionStatus.ACCEPTING_APPLICATIONS,
        "project_count": 4,
        "pick_winner": False,
    },
]


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
            description=p["description"],
            long_description=p.get("long_description", ""),
            website_url=p["website_url"],
            github_url=p.get("github_url"),
            tech_stack=p.get("tech_stack", []),
            monthly_visitors=p.get("monthly_visitors", 0),
            status=p["status"],
            rejection_reason=p.get("rejection_reason"),
            is_featured=p.get("is_featured", False),
            submission_month=f"2025-{(i % 3) + 1:02d}",
            owner=owner,
            approved_by=admin if p["status"] == ProjectStatus.APPROVED else None,
            approved_at=timezone.now()
            if p["status"] == ProjectStatus.APPROVED
            else None,
        )

        # Assign tags
        for tag_name in p.get("tag_names", []):
            if tag_name not in tag_cache:
                tag = Tag.objects.filter(name=tag_name).first()
                if tag:
                    tag_cache[tag_name] = tag
            if tag_name in tag_cache:
                project.tags.add(tag_cache[tag_name])

        print(f"  Created project: {project.title} ({project.status}) by {owner.email}")
        created.append(project)

    return created


def create_project_images(projects: list[Project]) -> int:
    print("\nCreating project images...")
    count = 0
    for project in projects:
        images = PROJECT_IMAGES.get(project.title, [])
        if not images:
            continue
        if project.images.exists():
            print(f"  Images already exist for: {project.title}")
            continue
        for i, img in enumerate(images):
            ProjectImage.objects.create(
                project=project,
                storage_key=img["storage_key"],
                original_filename=img["filename"],
                content_type="image/png",
                file_size=0,
                is_main=(i == 0),
                display_order=i,
                upload_status=UploadStatus.UPLOADED,
                uploaded_at=timezone.now(),
            )
            count += 1
        print(f"  Added {len(images)} images to: {project.title}")
    return count


def create_competitions(projects: list[Project], users: list[User]) -> None:
    print("\nCreating competitions...")
    approved = [p for p in projects if p.status == ProjectStatus.APPROVED]

    for comp_data in COMPETITIONS:
        if Competition.objects.filter(name=comp_data["name"]).exists():
            print(f"  Competition already exists: {comp_data['name']}")
            continue

        comp = Competition(
            name=comp_data["name"],
            start_date=comp_data["start_date"],
            end_date=comp_data["end_date"],
            quote=comp_data["quote"],
            prize_amount=comp_data["prize_amount"],
            status=comp_data["status"],
        )
        comp.save()

        # Assign projects
        count = min(comp_data["project_count"], len(approved))
        comp_projects = random.sample(approved, count)
        comp.projects.add(*comp_projects)

        # Pick a winner for closed competitions
        if comp_data["pick_winner"] and comp_projects:
            comp.winner = comp_projects[0]
            comp.save()

        # Add reviewers
        reviewers = random.sample(users, min(3, len(users)))
        for reviewer_user in reviewers:
            CompetitionReviewer.objects.get_or_create(
                user=reviewer_user,
                competition=comp,
            )

        # Add rankings from reviewers for closed competitions
        if comp_data["status"] == CompetitionStatus.CLOSED:
            for reviewer_user in reviewers:
                shuffled = list(comp_projects)
                random.shuffle(shuffled)
                for pos, proj in enumerate(shuffled, start=1):
                    ProjectRanking.objects.get_or_create(
                        reviewer=reviewer_user,
                        competition=comp,
                        project=proj,
                        defaults={"position": pos},
                    )

        print(
            f"  Created competition: {comp.name} ({comp.status}) with {count} projects"
        )


def main() -> None:
    # Check if seed data already exists
    if User.objects.filter(email=SEED_MARKER_EMAIL).exists():
        print("Seed data already exists. To re-seed, delete the marker user:")
        print(f"  User.objects.filter(email='{SEED_MARKER_EMAIL}').delete()")
        print("Then run this script again.")
        return

    print("=== Seeding database ===\n")

    # Find admin user for approvals
    admin = User.objects.filter(is_staff=True).first()

    users = create_users()
    projects = create_projects(users, admin)
    image_count = create_project_images(projects)
    create_competitions(projects, users)

    # Create marker so we know seed data exists
    User.objects.create(
        email=SEED_MARKER_EMAIL,
        kennitala=generate_kennitala(),
        first_name="Seed",
        last_name="Marker",
        is_active=False,
    )

    print("\n=== Seed complete ===")
    print(f"  Users:        {len(users)}")
    print(f"  Projects:     {len(projects)}")
    print(f"  Images:       {image_count}")
    print(f"  Competitions: {Competition.objects.count()}")
    print(f"\nAll seed users have password: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
