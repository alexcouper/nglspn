"""Django validates `search_fields` only when a search actually runs, so a typo
there is a latent 500. Exercise every registered admin's search once."""

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import NotRegistered
from django.test import RequestFactory

from tests.factories import UserFactory


def searchable_admins() -> list[ModelAdmin]:
    admins = []
    for model in apps.get_models():
        try:
            model_admin = admin.site.get_model_admin(model)
        except NotRegistered:
            continue
        if model_admin.get_search_fields(None):
            admins.append(model_admin)
    return admins


def admin_id(model_admin: ModelAdmin) -> str:
    return model_admin.model.__name__


def run_admin_search(model_admin: ModelAdmin, term: str) -> None:
    request = RequestFactory().get("/admin/", {"q": term})
    request.user = UserFactory(is_staff=True, is_superuser=True)

    queryset, _ = model_admin.get_search_results(
        request, model_admin.get_queryset(request), term
    )

    list(queryset[:1])


@pytest.mark.django_db
@pytest.mark.parametrize("model_admin", searchable_admins(), ids=admin_id)
def test_admin_search_fields_are_queryable(model_admin: ModelAdmin):
    run_admin_search(model_admin, "foo")
