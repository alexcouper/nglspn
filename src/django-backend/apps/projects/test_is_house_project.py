import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import Project
from tests.factories import ProjectFactory


@pytest.mark.django_db
class TestIsHouseProjectGuard:
    def test_default_is_false(self):
        project = ProjectFactory()
        assert project.is_house_project is False

    def test_setting_flag_on_first_row_succeeds(self):
        project = ProjectFactory(is_house_project=True)
        assert Project.objects.get(pk=project.pk).is_house_project is True

    def test_setting_flag_on_second_row_raises(self):
        ProjectFactory(is_house_project=True)
        p2 = ProjectFactory()
        p2.is_house_project = True
        with pytest.raises(ValidationError):
            p2.save()
        assert Project.objects.get(pk=p2.pk).is_house_project is False

    def test_re_saving_house_project_is_idempotent(self):
        project = ProjectFactory(is_house_project=True)
        # Save again with no change — must not raise.
        project.save()
        project.refresh_from_db()
        project.title = "Renamed"
        project.save()
        assert Project.objects.filter(is_house_project=True).count() == 1

    def test_moving_flag_between_rows_succeeds(self):
        p1 = ProjectFactory(is_house_project=True)
        p2 = ProjectFactory()
        p1.is_house_project = False
        p1.save()
        p2.is_house_project = True
        p2.save()
        assert Project.objects.get(pk=p1.pk).is_house_project is False
        assert Project.objects.get(pk=p2.pk).is_house_project is True
