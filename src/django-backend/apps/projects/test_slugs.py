from unittest.mock import patch

import pytest
from django.db import IntegrityError

from apps.projects.models import ProjectStatus
from apps.projects.slugs import assign_unique_slug, generate_unique_project_slug
from tests.factories import ProjectFactory


@pytest.mark.django_db
class TestGenerateUniqueProjectSlug:
    def test_simple_title_produces_slugified_form(self):
        assert generate_unique_project_slug("Super App") == "super-app"

    def test_icelandic_title_is_transliterated(self):
        assert generate_unique_project_slug("Súperþing") == "superthing"

    def test_single_collision_appends_2(self):
        ProjectFactory(title="Existing", slug="existing", status=ProjectStatus.APPROVED)
        assert generate_unique_project_slug("Existing") == "existing-2"

    def test_multiple_collisions_walk_to_next_free(self):
        for n, existing in enumerate(["existing", "existing-2", "existing-3"], start=1):
            ProjectFactory(title=f"t{n}", slug=existing, status=ProjectStatus.APPROVED)
        assert generate_unique_project_slug("Existing") == "existing-4"

    def test_empty_title_falls_back_to_project(self):
        assert generate_unique_project_slug("") == "project"

    def test_dots_become_dashes(self):
        assert generate_unique_project_slug("boots.is") == "boots-is"

    def test_multiple_dots_become_dashes(self):
        assert generate_unique_project_slug("www.example.com") == "www-example-com"

    def test_underscores_become_dashes(self):
        assert generate_unique_project_slug("my_cool_app") == "my-cool-app"

    def test_slashes_become_dashes(self):
        assert generate_unique_project_slug("team/boots") == "team-boots"

    def test_arbitrary_punctuation_becomes_dashes(self):
        assert (
            generate_unique_project_slug("foo.com/hellothere?x=1")
            == "foo-com-hellothere-x-1"
        )


@pytest.mark.django_db
class TestAssignUniqueSlug:
    def test_assigns_slug_and_persists(self):
        project = ProjectFactory(title="My Cool Thing", slug=None)
        assign_unique_slug(project)
        project.refresh_from_db()
        assert project.slug == "my-cool-thing"

    def test_long_title_with_collision_stays_within_max_length(self):
        # "þ" transliterates to "th" — a 100-char title of "þ"s produces a
        # 200-char base slug, well past the 110-char slug field limit.
        long_title = "þ" * 100
        project = ProjectFactory(title=long_title, slug=None)
        slug_max = 110

        assign_unique_slug(project)
        project.refresh_from_db()
        first_slug = project.slug
        assert first_slug is not None
        assert len(first_slug) <= slug_max
        assert not first_slug.endswith("-")

        # Force a collision on a second publish of an identical title.
        other = ProjectFactory(title=long_title, slug=None)
        assign_unique_slug(other)
        other.refresh_from_db()

        assert other.slug is not None
        assert other.slug != first_slug
        assert len(other.slug) <= slug_max
        assert other.slug.endswith("-2")

    def test_retries_on_concurrent_integrity_error(self):
        project = ProjectFactory(title="Race Case", slug=None)
        real_save = project.save
        calls = {"n": 0}

        def flaky_save(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                msg = "simulated concurrent insert"
                raise IntegrityError(msg)
            return real_save(*args, **kwargs)

        with patch.object(project, "save", side_effect=flaky_save):
            assign_unique_slug(project)

        project.refresh_from_db()
        assert project.slug == "race-case-2"
        assert calls["n"] == 2
