"""Seed the database with data matching the project listing mockup.

Usage:
    python manage.py seed_discover_data          # create seed data
    python manage.py seed_discover_data --clear   # remove seed data first

"""

from argparse import ArgumentParser
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.discussions.models import Discussion
from apps.projects.models import (
    Competition,
    Project,
    ProjectCategory,
    ProjectStatus,
)

User = get_user_model()

SEED_EMAIL = "seed-discover@example.com"

CATEGORIES = [
    {"name": "Consumer Products", "slug": "consumer-products", "order": 0},
    {"name": "Dev Tools", "slug": "dev-tools", "order": 1},
    {"name": "Community Boosters", "slug": "community-boosters", "order": 2},
]

PROJECTS = [
    # Consumer Products
    {
        "title": "Ljósmyndir",
        "tagline": "AI-powered photo management for Icelandic communities",
        "category": "consumer-products",
        "featured": True,
        "discussions": 24,
        "website": "https://ljosmyndir.example.com",
    },
    {
        "title": "Veðursjá",
        "tagline": "Hyperlocal weather for Icelandic regions with aurora alerts",
        "category": "consumer-products",
        "featured": False,
        "discussions": 0,
        "website": "https://vedursja.example.com",
    },
    {
        "title": "Matur",
        "tagline": "Recipe sharing with seasonal Icelandic ingredients",
        "category": "consumer-products",
        "featured": False,
        "discussions": 0,
        "website": "https://matur.example.com",
    },
    {
        "title": "Tónlist",
        "tagline": "Collaborative music creation platform",
        "category": "consumer-products",
        "featured": False,
        "discussions": 18,
        "winner_comp": "March 2026 Competition",
        "website": "https://tonlist.example.com",
    },
    {
        "title": "Ferðalag",
        "tagline": "Travel planning with local insights",
        "category": "consumer-products",
        "featured": False,
        "discussions": 0,
        "winner_comp": "February 2026 Competition",
        "website": "https://ferdalag.example.com",
    },
    {
        "title": "Heilsa",
        "tagline": "Health tracking designed for Nordic lifestyles",
        "category": "consumer-products",
        "featured": False,
        "discussions": 0,
        "winner_comp": "January 2026 Competition",
        "website": "https://heilsa.example.com",
    },
    # Dev Tools
    {
        "title": "Kóðavél",
        "tagline": "Code generation for Icelandic devs",
        "category": "dev-tools",
        "featured": True,
        "discussions": 9,
        "website": "https://kodavel.example.com",
    },
    {
        "title": "Próf",
        "tagline": "Test runner with native Icelandic language support",
        "category": "dev-tools",
        "featured": False,
        "discussions": 0,
        "website": "https://prof.example.com",
    },
    {
        "title": "Gagnagrunnur",
        "tagline": "Database migration tool for Icelandic character sets",
        "category": "dev-tools",
        "featured": False,
        "discussions": 0,
        "website": "https://gagnagrunnur.example.com",
    },
    {
        "title": "Pakki",
        "tagline": "Package manager for Icelandic open source projects",
        "category": "dev-tools",
        "featured": False,
        "discussions": 0,
        "website": "https://pakki.example.com",
    },
    {
        "title": "Leit",
        "tagline": "Search indexer with Icelandic stemming support",
        "category": "dev-tools",
        "featured": False,
        "discussions": 0,
        "website": "https://leit.example.com",
    },
    # Community Boosters
    {
        "title": "Bókasafn",
        "tagline": "Community library sharing and book exchange network",
        "category": "community-boosters",
        "featured": False,
        "discussions": 12,
        "website": "https://bokasafn.example.com",
    },
    {
        "title": "Samfélag",
        "tagline": "Local meetup coordination platform",
        "category": "community-boosters",
        "featured": True,
        "discussions": 0,
        "website": "https://samfelag.example.com",
    },
    {
        "title": "Skóli",
        "tagline": "Learning platform for Icelandic language and culture",
        "category": "community-boosters",
        "featured": False,
        "discussions": 0,
        "website": "https://skoli.example.com",
    },
    {
        "title": "Spjall",
        "tagline": "Community forum for Icelandic makers",
        "category": "community-boosters",
        "featured": False,
        "discussions": 0,
        "website": "https://spjall.example.com",
    },
]

COMPETITIONS = [
    {
        "name": "March 2026 Competition",
        "start": date(2026, 3, 1),
        "end": date(2026, 3, 31),
    },
    {
        "name": "February 2026 Competition",
        "start": date(2026, 2, 1),
        "end": date(2026, 2, 28),
    },
    {
        "name": "January 2026 Competition",
        "start": date(2026, 1, 1),
        "end": date(2026, 1, 31),
    },
]


class Command(BaseCommand):
    help = "Seed database with discover page mockup data"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove existing seed data before creating",
        )

    def handle(self, *args: object, **options: object) -> None:
        if options["clear"]:
            self._clear()

        owner = self._get_or_create_owner()
        cats = self._create_categories()
        projects = self._create_projects(owner, cats)
        self._create_competitions(projects)
        self._create_discussions(owner, projects)

        self.stdout.write(self.style.SUCCESS("Seed data created"))

    def _clear(self) -> None:
        user = User.objects.filter(email=SEED_EMAIL).first()
        if user:
            Project.objects.filter(owner=user).delete()
            user.delete()
        ProjectCategory.objects.filter(
            slug__in=[c["slug"] for c in CATEGORIES]
        ).delete()
        Competition.objects.filter(name__in=[c["name"] for c in COMPETITIONS]).delete()
        self.stdout.write("Cleared existing seed data")

    def _get_or_create_owner(self) -> "User":
        user, created = User.objects.get_or_create(
            email=SEED_EMAIL,
            defaults={
                "first_name": "Seed",
                "last_name": "User",
                "kennitala": "0000000000",
                "is_verified": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password("seedpassword123")
            user.save()
        return user

    def _create_categories(self) -> dict[str, ProjectCategory]:
        cats = {}
        for cat_data in CATEGORIES:
            cat, _ = ProjectCategory.objects.get_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "display_order": cat_data["order"],
                },
            )
            cats[cat.slug] = cat
        self.stdout.write(f"  Categories: {len(cats)}")
        return cats

    def _create_projects(
        self,
        owner: "User",
        cats: dict[str, ProjectCategory],
    ) -> dict[str, Project]:
        now = timezone.now()
        projects = {}
        for i, p_data in enumerate(PROJECTS):
            # Stagger approved_at so they appear in order
            approved_at = now - timedelta(days=i)
            project, _ = Project.objects.get_or_create(
                title=p_data["title"],
                owner=owner,
                defaults={
                    "tagline": p_data["tagline"],
                    "description": p_data["tagline"],
                    "website_url": p_data["website"],
                    "status": ProjectStatus.APPROVED,
                    "is_featured": p_data.get("featured", False),
                    "category": cats.get(p_data["category"]),
                    "approved_at": approved_at,
                    "submission_month": now.strftime("%Y-%m"),
                },
            )
            projects[project.title] = project
        self.stdout.write(f"  Projects: {len(projects)}")
        return projects

    def _create_competitions(self, projects: dict[str, Project]) -> None:
        winner_map = {}
        for p_data in PROJECTS:
            if "winner_comp" in p_data:
                winner_map[p_data["winner_comp"]] = p_data["title"]

        for comp_data in COMPETITIONS:
            winner_title = winner_map.get(comp_data["name"])
            winner = projects.get(winner_title) if winner_title else None
            comp, created = Competition.objects.get_or_create(
                name=comp_data["name"],
                defaults={
                    "start_date": comp_data["start"],
                    "submission_deadline": comp_data["end"],
                },
            )
            if winner and created:
                comp.projects.add(winner)
                comp.winner = winner
                comp.save()
        self.stdout.write(f"  Competitions: {len(COMPETITIONS)}")

    def _create_discussions(
        self,
        owner: "User",
        projects: dict[str, Project],
    ) -> None:
        total = 0
        for p_data in PROJECTS:
            count = p_data.get("discussions", 0)
            if count == 0:
                continue
            project = projects.get(p_data["title"])
            if not project:
                continue
            existing = Discussion.objects.filter(
                project=project, parent__isnull=True
            ).count()
            to_create = count - existing
            if to_create > 0:
                discussions = [
                    Discussion(
                        project=project,
                        author=owner,
                        body=f"Discussion {j + 1} about {project.title}",
                    )
                    for j in range(to_create)
                ]
                Discussion.objects.bulk_create(discussions)
                total += to_create
        self.stdout.write(f"  Discussions: {total}")
