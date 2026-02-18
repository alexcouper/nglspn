import pytest
from django.core.files.storage import InMemoryStorage
from django.test import Client

from api.auth.jwt import create_access_token, create_refresh_token
from apps.emails.models import BroadcastEmailImage
from tests.factories import ProjectFactory, TagFactory, UserFactory


@pytest.fixture(autouse=True)
def _allow_admin_ip(settings):
    settings.ADMIN_ALLOWED_IPS = ["127.0.0.1"]


@pytest.fixture(autouse=True)
def _use_in_memory_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "broadcast_images": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    # Django 6 resolves callable storage at field init time, so the S3 backend
    # is already baked into the field. Swap it out directly for tests.
    BroadcastEmailImage.image.field.storage = InMemoryStorage()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_headers(user):
    token = create_access_token(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def access_token(user):
    return create_access_token(user.id)


@pytest.fixture
def refresh_token(user):
    return create_refresh_token(user.id)


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(other_user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def project(user):
    return ProjectFactory(owner=user)


@pytest.fixture
def other_project(other_user):
    return ProjectFactory(owner=other_user)


@pytest.fixture
def tag(db):
    return TagFactory()


@pytest.fixture
def tags(db):
    return [TagFactory() for _ in range(3)]
