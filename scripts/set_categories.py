"""
Remove existing categories and create 4 new ones, then assign each project.
Run from src/django-backend/:
    DATABASE_URL="postgres://showcase_user:showcase_pass@localhost:5432/projectshowcase" \
    uv run python manage.py shell < ../../scripts/set_categories.py
"""

from apps.projects.models import Project, ProjectCategory

# 1. Remove all existing categories
ProjectCategory.objects.all().delete()
print("Deleted all existing categories.")

# 2. Create new categories (Apps & Services first, then sub-groups, then Dev Tools)
categories = {
    "apps-services": ("Apps & Services", 1),
    "community-public-good": ("Community & Public Good", 2),
    "productivity-business": ("Productivity & Business", 3),
    "developer-tools": ("Developer Tools", 4),
}

cat_objects = {}
for slug, (name, order) in categories.items():
    cat_objects[slug] = ProjectCategory.objects.create(
        name=name, slug=slug, display_order=order
    )
    print(f"Created category: {name}")

# 3. Map projects to categories by title
assignments = {
    "apps-services": [
        "eventa.is",
        "sundlaugar.com",
        "keep.is",
        "smakk.app",
        "Clusters",
        "rocketleague.is",
        "rastimar.golf.is",
        "minskimun.is",
        "leiksvæði.is",
        "boardroomkids.vercel.app",
        "morphvox.net",
        "Whats for dinner, huh? - Working title",
        "runescope.is",
    ],
    "community-public-good": [
        "Naglasúpan",
        "open.mannvaen.is",
        "digitalmap.atli.io",
        "wheretolearnicelandic.org",
        "Prótó",
        "Gasvaktin",
        "yrða.is",
    ],
    "productivity-business": [
        "vinnr.is",
        "Tensions",
        "postwall.app",
        "roommate",
    ],
    "developer-tools": [
        "codeclip.link",
        "Code Snippet Manager",
        "Synapse - Watch AI Agents Think in Real-Time",
        "Accessibility Scanner",
        "Loka-Orð",
    ],
}

assigned = 0
missing = []

for slug, titles in assignments.items():
    cat = cat_objects[slug]
    for title in titles:
        try:
            project = Project.objects.get(title=title)
            project.category = cat
            project.save()
            assigned += 1
            print(f"  {title} -> {cat.name}")
        except Project.DoesNotExist:
            missing.append(title)
            print(f"  WARNING: '{title}' not found!")

print(f"\nDone. Assigned {assigned} projects. {len(missing)} missing: {missing}")

# Check for any unassigned projects
unassigned = Project.objects.filter(category__isnull=True)
if unassigned.exists():
    print(f"\nUnassigned projects ({unassigned.count()}):")
    for p in unassigned:
        print(f"  - {p.title}")
