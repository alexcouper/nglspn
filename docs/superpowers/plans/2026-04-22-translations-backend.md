# Translations Backend Implementation Plan (Phase 1 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django backend for dynamic translations: two tables (`Translation`, `TranslationAudit`), three HTTP endpoints (catalog read, version probe, edit), and a webhook that notifies the web-ui on edits so it can invalidate its cache.

**Architecture:** New Django app `apps.translations` with two models. All API endpoints live in a new Django-Ninja router at `/api/i18n`. Audit entries are written automatically on every save via an override on `Translation.save()`. After a successful PATCH, the request handler fires a best-effort webhook to the web-ui's `/api/revalidate-i18n` endpoint with a shared secret — failures are logged but do not fail the user's request.

**Tech Stack:** Django 5, Django-Ninja, pytest + hamcrest, factory_boy (all already in the repo).

**Spec:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`

**Out of scope for this phase:** Web-UI changes, `next-intl` setup, inline edit UX, MT generation, lint rules, editor worklist. Those are Phases 2–5, each with their own plan.

**How to verify the phase is done:** You can `curl` each endpoint and see the documented behavior. You can edit a row via PATCH and see a) the row updated, b) an audit row written, c) `is_machine_translated` flip to False, d) a webhook POST fire (visible in logs even if the target doesn't exist yet).

---

## File Structure

### New files

- `src/django-backend/apps/translations/__init__.py`
- `src/django-backend/apps/translations/apps.py` — Django app config
- `src/django-backend/apps/translations/models.py` — `Translation`, `TranslationAudit`
- `src/django-backend/apps/translations/admin.py` — register in admin (read-only audit)
- `src/django-backend/apps/translations/migrations/__init__.py`
- `src/django-backend/apps/translations/migrations/0001_initial.py` — generated
- `src/django-backend/apps/translations/webhooks.py` — fire `revalidate-i18n` webhook
- `src/django-backend/api/routers/translations.py` — HTTP endpoints
- `src/django-backend/api/schemas/translations.py` — ninja schemas for requests/responses
- `src/django-backend/api/routers/test_translations.py` — tests for endpoints
- `src/django-backend/tests/test_translations_model.py` — tests for model + audit behavior
- `src/django-backend/tests/test_translations_webhook.py` — tests for webhook firing

### Modified files

- `src/django-backend/project_showcase/settings.py` — add `apps.translations` to `INSTALLED_APPS`, add `WEB_UI_REVALIDATE_URL` + `WEB_UI_REVALIDATE_SECRET` settings.
- `src/django-backend/api/main.py` — register the new router.
- `src/django-backend/tests/factories.py` — add `TranslationFactory`.

---

## Codebase conventions observed

- Django apps live in `src/django-backend/apps/<name>/` and are registered in `INSTALLED_APPS` as `apps.<name>`.
- HTTP layer uses Django-Ninja. Routers live in `api/routers/<name>.py`; schemas in `api/schemas/<name>.py`; routers are mounted in `api/main.py` via `api.add_router("/prefix", module.router)`.
- Tests: two places
  - Router-level tests colocated with routers: `api/routers/test_<name>.py`.
  - App-level tests in `tests/test_<name>.py` (model behavior, invariants).
- Tests use pytest + PyHamcrest matchers (`assert_that`, `equal_to`, `has_entries`) + `factory_boy` factories from `tests/factories.py`.
- Authentication: `from api.auth.security import auth` — ninja `HttpBearer` JWT auth. Use `auth=auth` on endpoints that require login.

---

## Version control

User uses `jj` (jujutsu), not git. Every task below ends with a `jj commit` step.

Before starting the plan: open a new jj changeset so this phase is isolated.

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
jj is-empty || jj new -m "WIP: translations backend phase 1"
jj describe -m "feat(translations): backend catalog, API, webhook (phase 1)"
```

(If `jj is-empty` returns true, just `jj describe`.)

Per-task commits: use `jj commit -m "<msg>"` which will start a new empty change on top. That's the conventional flow.

---

## Task 1: Scaffold the `translations` Django app

**Files:**
- Create: `src/django-backend/apps/translations/__init__.py`
- Create: `src/django-backend/apps/translations/apps.py`
- Create: `src/django-backend/apps/translations/models.py`
- Create: `src/django-backend/apps/translations/admin.py`
- Create: `src/django-backend/apps/translations/migrations/__init__.py`
- Modify: `src/django-backend/project_showcase/settings.py` (INSTALLED_APPS)

- [ ] **Step 1: Create the app package files (empty/stub)**

`src/django-backend/apps/translations/__init__.py`:
```python
```

`src/django-backend/apps/translations/apps.py`:
```python
from django.apps import AppConfig


class TranslationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.translations"
```

`src/django-backend/apps/translations/models.py`:
```python
```

`src/django-backend/apps/translations/admin.py`:
```python
```

`src/django-backend/apps/translations/migrations/__init__.py`:
```python
```

- [ ] **Step 2: Register app in settings**

In `src/django-backend/project_showcase/settings.py`, add `"apps.translations",` to `INSTALLED_APPS` directly after `"apps.notifications",` (the last entry at line ~72):

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "apps.users",
    "apps.projects",
    "apps.tags",
    "apps.emails",
    "apps.discussions",
    "apps.notifications",
    "apps.translations",  # <-- new
    # ... rest ...
]
```

- [ ] **Step 3: Verify Django sees the app**

Run: `cd src/django-backend && uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(translations): scaffold app"
```

---

## Task 2: `Translation` model (TDD)

**Files:**
- Modify: `src/django-backend/apps/translations/models.py`
- Create: `src/django-backend/tests/test_translations_model.py`
- Modify: `src/django-backend/tests/factories.py`
- Create: `src/django-backend/apps/translations/migrations/0001_initial.py` (via `makemigrations`)

- [ ] **Step 1: Write the failing test**

Create `src/django-backend/tests/test_translations_model.py`:
```python
import hashlib

import pytest
from django.db.utils import IntegrityError
from hamcrest import assert_that, equal_to, is_not, none

from apps.translations.models import Translation


@pytest.mark.django_db
class TestTranslationModel:
    def test_create_translation(self) -> None:
        t = Translation.objects.create(
            locale="is",
            key="home.hero.title",
            text="Velkomin",
            source_hash=hashlib.sha256(b"Welcome").hexdigest(),
        )
        assert_that(t.pk, is_not(none()))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(t.retired, equal_to(False))

    def test_locale_key_uniqueness(self) -> None:
        Translation.objects.create(
            locale="is", key="nav.home", text="Heim", source_hash="abc"
        )
        with pytest.raises(IntegrityError):
            Translation.objects.create(
                locale="is", key="nav.home", text="Aftur heim", source_hash="abc"
            )

    def test_same_key_different_locales_allowed(self) -> None:
        Translation.objects.create(
            locale="en", key="nav.home", text="Home", source_hash="abc"
        )
        Translation.objects.create(
            locale="is", key="nav.home", text="Heim", source_hash="abc"
        )
        assert_that(Translation.objects.count(), equal_to(2))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/django-backend && uv run pytest tests/test_translations_model.py -v`
Expected: FAIL — `ImportError` or `AttributeError` because `Translation` doesn't exist yet.

- [ ] **Step 3: Implement the model**

Replace `src/django-backend/apps/translations/models.py`:
```python
from django.conf import settings
from django.db import models


class Translation(models.Model):
    locale = models.CharField(max_length=16, db_index=True)
    key = models.CharField(max_length=255, db_index=True)
    text = models.TextField()
    source_hash = models.CharField(max_length=64)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="translations_edited",
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_machine_translated = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "key"], name="uniq_translation_locale_key"
            )
        ]
        indexes = [
            models.Index(fields=["locale", "retired"]),
        ]

    def __str__(self) -> str:
        return f"[{self.locale}] {self.key}"
```

- [ ] **Step 4: Generate migration**

Run: `cd src/django-backend && uv run python manage.py makemigrations translations`
Expected: creates `apps/translations/migrations/0001_initial.py`.

- [ ] **Step 5: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest tests/test_translations_model.py -v`
Expected: 3 tests pass.

- [ ] **Step 6: Add factory**

In `src/django-backend/tests/factories.py`, add at the bottom:
```python
from apps.translations.models import Translation  # add to imports at top of file


class TranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Translation

    locale = "is"
    key = factory.Sequence(lambda n: f"test.key.{n}")
    text = factory.Faker("sentence")
    source_hash = factory.Faker("sha256")
    is_machine_translated = False
    retired = False
```
(Place the `from apps.translations.models import Translation` line with the other model imports at the top of the file.)

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): Translation model + migration"
```

---

## Task 3: `TranslationAudit` model (TDD)

**Files:**
- Modify: `src/django-backend/apps/translations/models.py`
- Modify: `src/django-backend/tests/test_translations_model.py`
- Create: `src/django-backend/apps/translations/migrations/0002_translationaudit.py` (via `makemigrations`)

- [ ] **Step 1: Write the failing tests**

Append to `src/django-backend/tests/test_translations_model.py`:
```python
from apps.translations.models import TranslationAudit
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestAuditWriteOnSave:
    def test_create_writes_audit_with_null_old_text(self) -> None:
        user = UserFactory()
        t = Translation.objects.create(
            locale="is",
            key="nav.home",
            text="Heim",
            source_hash="abc",
            updated_by=user,
        )
        audits = TranslationAudit.objects.filter(translation=t)
        assert_that(audits.count(), equal_to(1))
        entry = audits.get()
        assert_that(entry.old_text, equal_to(""))
        assert_that(entry.new_text, equal_to("Heim"))
        assert_that(entry.changed_by, equal_to(user))
        assert_that(entry.locale, equal_to("is"))
        assert_that(entry.key, equal_to("nav.home"))

    def test_update_writes_audit_with_previous_text(self) -> None:
        user1 = UserFactory()
        user2 = UserFactory()
        t = TranslationFactory(text="Heim", updated_by=user1)
        t.text = "Forsíða"
        t.updated_by = user2
        t.save()

        audits = TranslationAudit.objects.filter(translation=t).order_by("changed_at")
        assert_that(audits.count(), equal_to(2))
        latest = audits.last()
        assert_that(latest.old_text, equal_to("Heim"))
        assert_that(latest.new_text, equal_to("Forsíða"))
        assert_that(latest.changed_by, equal_to(user2))

    def test_no_audit_when_text_unchanged(self) -> None:
        t = TranslationFactory(text="Heim")
        # Saving without changing text should not add an audit
        t.is_machine_translated = True
        t.save()
        assert_that(TranslationAudit.objects.filter(translation=t).count(), equal_to(1))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd src/django-backend && uv run pytest tests/test_translations_model.py::TestAuditWriteOnSave -v`
Expected: FAIL — `TranslationAudit` not defined.

- [ ] **Step 3: Add the audit model + save hook**

Replace the contents of `src/django-backend/apps/translations/models.py`:
```python
from django.conf import settings
from django.db import models


class Translation(models.Model):
    locale = models.CharField(max_length=16, db_index=True)
    key = models.CharField(max_length=255, db_index=True)
    text = models.TextField()
    source_hash = models.CharField(max_length=64)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="translations_edited",
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_machine_translated = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "key"], name="uniq_translation_locale_key"
            )
        ]
        indexes = [
            models.Index(fields=["locale", "retired"]),
        ]

    def __str__(self) -> str:
        return f"[{self.locale}] {self.key}"

    def save(self, *args, **kwargs) -> None:
        previous_text = ""
        if self.pk is not None:
            previous_text = (
                Translation.objects.filter(pk=self.pk)
                .values_list("text", flat=True)
                .first()
                or ""
            )
        super().save(*args, **kwargs)
        if previous_text != self.text:
            TranslationAudit.objects.create(
                translation=self,
                locale=self.locale,
                key=self.key,
                old_text=previous_text,
                new_text=self.text,
                changed_by=self.updated_by,
            )


class TranslationAudit(models.Model):
    translation = models.ForeignKey(
        Translation,
        on_delete=models.DO_NOTHING,
        related_name="audits",
    )
    locale = models.CharField(max_length=16)
    key = models.CharField(max_length=255)
    old_text = models.TextField(blank=True)
    new_text = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["translation", "changed_at"]),
            models.Index(fields=["locale", "key"]),
        ]
```

Note: `on_delete=models.DO_NOTHING` for `translation` FK because we want audit to survive even if the Translation row is deleted. Django still allows this; the FK column just retains the stale id.

- [ ] **Step 4: Generate migration**

Run: `cd src/django-backend && uv run python manage.py makemigrations translations`
Expected: creates `0002_translationaudit.py`.

- [ ] **Step 5: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest tests/test_translations_model.py -v`
Expected: all 6 tests pass (3 from Task 2 + 3 from Task 3).

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(translations): TranslationAudit + automatic write on save"
```

---

## Task 4: Ninja schemas (no tests — schemas are exercised by router tests)

**Files:**
- Create: `src/django-backend/api/schemas/translations.py`

- [ ] **Step 1: Write the schemas file**

Create `src/django-backend/api/schemas/translations.py`:
```python
from datetime import datetime

from ninja import Schema


class TranslationPatchRequest(Schema):
    text: str


class TranslationResponse(Schema):
    locale: str
    key: str
    text: str
    source_hash: str
    is_machine_translated: bool
    updated_at: datetime


class TranslationVersionResponse(Schema):
    version: int  # Unix epoch seconds of max updated_at; 0 if empty.
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd src/django-backend && uv run python -c "from api.schemas.translations import TranslationPatchRequest, TranslationResponse, TranslationVersionResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
jj commit -m "feat(translations): ninja schemas"
```

---

## Task 5: `GET /api/i18n/{locale}` endpoint (TDD)

**Files:**
- Create: `src/django-backend/api/routers/translations.py`
- Create: `src/django-backend/api/routers/test_translations.py`
- Modify: `src/django-backend/api/main.py`

- [ ] **Step 1: Write the failing test**

Create `src/django-backend/api/routers/test_translations.py`:
```python
import pytest
from hamcrest import assert_that, equal_to, has_entries, is_not, has_key

from tests.factories import TranslationFactory


@pytest.mark.django_db
class TestGetCatalog:
    def test_returns_key_text_map_for_locale(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="nav.about", text="Um okkur")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            equal_to({"nav.home": "Heim", "nav.about": "Um okkur"}),
        )

    def test_excludes_retired_rows(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(
            locale="is", key="old.key", text="Gamalt", retired=True
        )

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(**{"nav.home": "Heim"}))
        assert_that(body, is_not(has_key("old.key")))

    def test_unknown_locale_returns_empty(self, client) -> None:
        response = client.get("/api/i18n/xx")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({}))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py -v`
Expected: FAIL — route not registered, 404.

- [ ] **Step 3: Implement the router with the GET endpoint**

Create `src/django-backend/api/routers/translations.py`:
```python
from django.http import HttpRequest
from ninja import Router

from apps.translations.models import Translation

router = Router()


@router.get("/{locale}", response=dict[str, str], tags=["Translations"])
def get_catalog(request: HttpRequest, locale: str) -> dict[str, str]:
    """Return the full non-retired translation catalog for a locale."""
    rows = Translation.objects.filter(locale=locale, retired=False).values_list(
        "key", "text"
    )
    return dict(rows)
```

- [ ] **Step 4: Register router in `api/main.py`**

Modify `src/django-backend/api/main.py`. Add `translations` to the router imports and the `add_router` calls:

```python
from api.routers import (
    auth,
    competitions,
    discussions,
    my_projects,
    my_review,
    projects,
    tags,
    translations,  # <-- new
    users,
)
# ... unchanged code ...

api.add_router("/auth", auth.router)
# ... other add_router calls unchanged ...
api.add_router("/users", users.router)
api.add_router("/i18n", translations.router)  # <-- new
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py::TestGetCatalog -v`
Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(translations): GET /api/i18n/{locale} endpoint"
```

---

## Task 6: `GET /api/i18n/{locale}/version` endpoint (TDD)

**Files:**
- Modify: `src/django-backend/api/routers/translations.py`
- Modify: `src/django-backend/api/routers/test_translations.py`

- [ ] **Step 1: Write the failing tests**

Append to `src/django-backend/api/routers/test_translations.py`:
```python
@pytest.mark.django_db
class TestGetVersion:
    def test_empty_returns_zero(self, client) -> None:
        response = client.get("/api/i18n/is/version")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({"version": 0}))

    def test_returns_max_updated_at_as_epoch(self, client) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        response = client.get("/api/i18n/is/version")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["version"], equal_to(int(t.updated_at.timestamp())))

    def test_version_scoped_by_locale(self, client) -> None:
        TranslationFactory(locale="is", key="a", text="A-is")
        en = TranslationFactory(locale="en", key="b", text="B-en")

        response = client.get("/api/i18n/en/version")
        assert_that(response.json()["version"], equal_to(int(en.updated_at.timestamp())))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py::TestGetVersion -v`
Expected: FAIL — endpoint does not exist.

- [ ] **Step 3: Implement the endpoint**

Append to `src/django-backend/api/routers/translations.py`:
```python
from django.db.models import Max

from api.schemas.translations import TranslationVersionResponse


@router.get(
    "/{locale}/version",
    response=TranslationVersionResponse,
    tags=["Translations"],
)
def get_version(request: HttpRequest, locale: str) -> dict[str, int]:
    """Return a monotonic version for a locale's catalog (max updated_at as epoch)."""
    max_updated = Translation.objects.filter(locale=locale).aggregate(
        m=Max("updated_at")
    )["m"]
    return {"version": int(max_updated.timestamp()) if max_updated else 0}
```

(Place the `from django.db.models import Max` import at the top of the file alongside the other imports. Same for the schema import.)

- [ ] **Step 4: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py -v`
Expected: all tests from Tasks 5 + 6 pass.

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat(translations): GET /api/i18n/{locale}/version endpoint"
```

---

## Task 7: Webhook fire-and-forget helper (TDD)

**Files:**
- Create: `src/django-backend/apps/translations/webhooks.py`
- Create: `src/django-backend/tests/test_translations_webhook.py`
- Modify: `src/django-backend/project_showcase/settings.py`

- [ ] **Step 1: Add settings entries**

In `src/django-backend/project_showcase/settings.py`, add near the bottom (before the last setting, or in a clearly-marked "Translations" section):
```python
# Translations — web-ui revalidation webhook
WEB_UI_REVALIDATE_URL = os.environ.get("WEB_UI_REVALIDATE_URL", "")
WEB_UI_REVALIDATE_SECRET = os.environ.get("WEB_UI_REVALIDATE_SECRET", "")
```
(If `os` is not already imported at the top of settings.py, add `import os`.)

- [ ] **Step 2: Write the failing test**

Create `src/django-backend/tests/test_translations_webhook.py`:
```python
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from apps.translations.webhooks import notify_web_ui


class TestNotifyWebUi:
    def test_posts_to_configured_url_with_secret_header(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = "https://web.example/api/revalidate-i18n"
        settings.WEB_UI_REVALIDATE_SECRET = "top-secret"

        with patch("apps.translations.webhooks.requests.post") as post:
            post.return_value.status_code = 200
            notify_web_ui("is")

        post.assert_called_once()
        kwargs = post.call_args.kwargs
        args = post.call_args.args
        assert_that(args[0], equal_to("https://web.example/api/revalidate-i18n"))
        assert_that(kwargs["json"], equal_to({"locale": "is"}))
        assert_that(
            kwargs["headers"],
            equal_to({"X-Revalidate-Secret": "top-secret"}),
        )

    def test_no_op_when_url_unset(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = ""
        with patch("apps.translations.webhooks.requests.post") as post:
            notify_web_ui("is")
        post.assert_not_called()

    def test_swallows_network_errors(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = "https://web.example/api/revalidate-i18n"
        settings.WEB_UI_REVALIDATE_SECRET = "top-secret"
        with patch(
            "apps.translations.webhooks.requests.post",
            side_effect=Exception("boom"),
        ):
            notify_web_ui("is")  # Must not raise.
```

- [ ] **Step 3: Run to verify failure**

Run: `cd src/django-backend && uv run pytest tests/test_translations_webhook.py -v`
Expected: FAIL — `apps.translations.webhooks` does not exist.

- [ ] **Step 4: Implement the helper**

Create `src/django-backend/apps/translations/webhooks.py`:
```python
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_web_ui(locale: str) -> None:
    """Best-effort POST to the web-ui telling it to revalidate its cached catalog.

    Never raises: webhook failures must not fail the originating request.
    No-op if WEB_UI_REVALIDATE_URL is unset (e.g. local dev).
    """
    url = settings.WEB_UI_REVALIDATE_URL
    if not url:
        return
    try:
        requests.post(
            url,
            json={"locale": locale},
            headers={"X-Revalidate-Secret": settings.WEB_UI_REVALIDATE_SECRET},
            timeout=2,
        )
    except Exception as exc:  # noqa: BLE001 - intentional broad catch
        logger.warning("revalidate webhook failed for locale=%s: %s", locale, exc)
```

- [ ] **Step 5: Confirm `requests` is available**

Run: `cd src/django-backend && uv run python -c "import requests; print(requests.__version__)"`

Expected: a version string. If this errors with ModuleNotFoundError, add `requests` to `pyproject.toml` dependencies and `uv sync`; the project likely already uses `requests` elsewhere — check with `grep -rn "import requests" src/django-backend --include="*.py"`.

- [ ] **Step 6: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest tests/test_translations_webhook.py -v`
Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): revalidation webhook helper"
```

---

## Task 8: `PATCH /api/i18n/{locale}/{key}` endpoint (TDD)

This is the meat of the backend. It: (a) requires authentication, (b) updates or creates the row, (c) flips `is_machine_translated` to False, (d) writes the audit entry (automatic via save hook from Task 3), (e) fires the webhook.

**Files:**
- Modify: `src/django-backend/api/routers/translations.py`
- Modify: `src/django-backend/api/routers/test_translations.py`

- [ ] **Step 1: Write the failing tests**

Append to `src/django-backend/api/routers/test_translations.py`:
```python
from unittest.mock import patch

from api.auth.jwt import create_access_token
from apps.translations.models import Translation, TranslationAudit
from tests.factories import UserFactory


def _auth_header(user) -> dict[str, str]:
    token = create_access_token(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
class TestPatchTranslation:
    def test_requires_authentication(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        response = client.patch(
            "/api/i18n/is/nav.home",
            data='{"text":"Forsíða"}',
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_updates_existing_row_and_flips_mt_flag(self, client) -> None:
        user = UserFactory()
        t = TranslationFactory(
            locale="is",
            key="nav.home",
            text="Heim",
            is_machine_translated=True,
        )
        with patch("api.routers.translations.notify_web_ui") as notify:
            response = client.patch(
                "/api/i18n/is/nav.home",
                data='{"text":"Forsíða"}',
                content_type="application/json",
                **_auth_header(user),
            )
        assert_that(response.status_code, equal_to(200))
        t.refresh_from_db()
        assert_that(t.text, equal_to("Forsíða"))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(t.updated_by, equal_to(user))
        notify.assert_called_once_with("is")

    def test_writes_audit_entry(self, client) -> None:
        user = UserFactory()
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch("api.routers.translations.notify_web_ui"):
            client.patch(
                "/api/i18n/is/nav.home",
                data='{"text":"Forsíða"}',
                content_type="application/json",
                **_auth_header(user),
            )
        audit = TranslationAudit.objects.filter(translation=t).order_by("-changed_at").first()
        assert_that(audit.old_text, equal_to("Heim"))
        assert_that(audit.new_text, equal_to("Forsíða"))
        assert_that(audit.changed_by, equal_to(user))

    def test_creates_row_if_missing(self, client) -> None:
        user = UserFactory()
        with patch("api.routers.translations.notify_web_ui"):
            response = client.patch(
                "/api/i18n/is/new.key",
                data='{"text":"Nýtt"}',
                content_type="application/json",
                **_auth_header(user),
            )
        assert_that(response.status_code, equal_to(200))
        t = Translation.objects.get(locale="is", key="new.key")
        assert_that(t.text, equal_to("Nýtt"))
        assert_that(t.updated_by, equal_to(user))

    def test_webhook_failure_does_not_fail_request(self, client) -> None:
        user = UserFactory()
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch(
            "api.routers.translations.notify_web_ui", side_effect=Exception("boom")
        ):
            response = client.patch(
                "/api/i18n/is/nav.home",
                data='{"text":"Forsíða"}',
                content_type="application/json",
                **_auth_header(user),
            )
        # Even though notify raised, the row must have been updated AND
        # the response must be 200. The helper is defensive; we simulate
        # something worse here to ensure the router also handles it.
        # NB: the actual `notify_web_ui` never raises, but defensive
        # callers are cheap insurance. See implementation in next step.
        assert_that(response.status_code, equal_to(200))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py::TestPatchTranslation -v`
Expected: FAIL — endpoint does not exist.

- [ ] **Step 3: Implement the endpoint**

Append to `src/django-backend/api/routers/translations.py`:
```python
import logging

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.translations import (
    TranslationPatchRequest,
    TranslationResponse,
)
from apps.translations.webhooks import notify_web_ui

logger = logging.getLogger(__name__)


@router.patch(
    "/{locale}/{key}",
    response={200: TranslationResponse, 401: Error},
    auth=auth,
    tags=["Translations"],
)
def patch_translation(
    request: HttpRequest,
    locale: str,
    key: str,
    payload: TranslationPatchRequest,
) -> Translation:
    """Edit a translation. Creates the row if missing. Requires authentication."""
    user = request.auth
    try:
        t = Translation.objects.get(locale=locale, key=key)
        t.text = payload.text
        t.is_machine_translated = False
        t.updated_by = user
        t.save()
    except Translation.DoesNotExist:
        # Creating a row via PATCH covers the case where the web-ui references
        # a key that has not yet been seeded for this locale. source_hash is
        # left empty; the next migration run will backfill it.
        t = Translation.objects.create(
            locale=locale,
            key=key,
            text=payload.text,
            source_hash="",
            is_machine_translated=False,
            updated_by=user,
        )

    try:
        notify_web_ui(locale)
    except Exception as exc:  # noqa: BLE001 - defensive; notify_web_ui already swallows
        logger.warning("notify_web_ui raised unexpectedly: %s", exc)

    return t
```

(Merge these imports with the existing ones at the top of the file — don't create duplicate import blocks.)

- [ ] **Step 4: Run tests to verify pass**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py -v`
Expected: all tests (across Tasks 5, 6, 8) pass.

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat(translations): PATCH /api/i18n/{locale}/{key} endpoint"
```

---

## Task 9: Admin registration (audit is read-only)

**Files:**
- Modify: `src/django-backend/apps/translations/admin.py`

- [ ] **Step 1: Register models**

Replace `src/django-backend/apps/translations/admin.py`:
```python
from django.contrib import admin

from apps.translations.models import Translation, TranslationAudit


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ("locale", "key", "is_machine_translated", "retired", "updated_at")
    list_filter = ("locale", "is_machine_translated", "retired")
    search_fields = ("key", "text")
    readonly_fields = ("updated_at", "source_hash")


@admin.register(TranslationAudit)
class TranslationAuditAdmin(admin.ModelAdmin):
    list_display = ("locale", "key", "changed_by", "changed_at")
    list_filter = ("locale",)
    search_fields = ("key", "old_text", "new_text")
    readonly_fields = tuple(
        f.name for f in TranslationAudit._meta.fields  # type: ignore[attr-defined]
    )

    def has_add_permission(self, request) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False
```

- [ ] **Step 2: Verify with Django check**

Run: `cd src/django-backend && uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
jj commit -m "feat(translations): admin registration (audit read-only)"
```

---

## Task 10: Regenerate OpenAPI and run the full backend test suite

**Files:**
- Modify: `src/django-backend/openapi.json` (generated)
- Modify: `src/web-ui/backend-openapi.json` (generated) — only if the web-ui consumes this now; skip if phase 2 handles it.

- [ ] **Step 1: Regenerate OpenAPI spec**

Run: `cd src/django-backend && make extract-openapi`
Expected: success; commit the updated `openapi.json`.

- [ ] **Step 2: Run the full backend test suite**

Run: `cd src/django-backend && make test`
Expected: all tests pass, including pre-existing ones (no regressions).

- [ ] **Step 3: Run linter**

Run: `cd src/django-backend && make lint`
Expected: `ruff check` and `ruff format --check` both clean. Fix any complaints (run `uv run ruff format .` to auto-fix formatting).

- [ ] **Step 4: Commit**

```bash
jj commit -m "chore(translations): regen OpenAPI + lint clean"
```

---

## Task 11: Smoke test end-to-end against a running server

**Files:** none (manual verification).

- [ ] **Step 1: Start the backend locally**

Run: `cd src/django-backend && uv run python manage.py migrate && uv run python manage.py runserver`

- [ ] **Step 2: Seed a row via the admin or shell**

In another terminal:
```bash
cd src/django-backend && uv run python manage.py shell -c "
from apps.translations.models import Translation
Translation.objects.create(locale='is', key='nav.home', text='Heim', source_hash='abc', is_machine_translated=True)
print('seeded')
"
```

- [ ] **Step 3: Hit the catalog endpoint**

Run: `curl http://localhost:8000/api/i18n/is`
Expected: `{"nav.home":"Heim"}`

- [ ] **Step 4: Hit the version endpoint**

Run: `curl http://localhost:8000/api/i18n/is/version`
Expected: `{"version":<some-epoch>}`

- [ ] **Step 5: Hit the PATCH endpoint (will 401 without a token)**

Run: `curl -X PATCH http://localhost:8000/api/i18n/is/nav.home -H 'Content-Type: application/json' -d '{"text":"Forsíða"}'`
Expected: 401.

- [ ] **Step 6: PATCH with a valid token**

Acquire a token via the existing `/api/auth/login` endpoint using a known user; then:
```bash
curl -X PATCH http://localhost:8000/api/i18n/is/nav.home \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"text":"Forsíða"}'
```
Expected: 200 with the updated row. Re-hit `GET /api/i18n/is` and verify the new text.

- [ ] **Step 7: Verify webhook fires with WEB_UI_REVALIDATE_URL pointed at httpbin**

```bash
WEB_UI_REVALIDATE_URL=https://httpbin.org/post WEB_UI_REVALIDATE_SECRET=dev \
  uv run python manage.py runserver
```
Do another PATCH as in Step 6. Check backend logs — you should see no warning. To see the outbound request succeed, temporarily increase log level or drop a `logger.info` in the helper.

- [ ] **Step 8: If everything works, commit an empty marker changeset**

This is a pure verification step; no file changes. Skip the commit if nothing changed. If you added any log lines to verify, revert those before committing — they should not ship.

---

## Phase 1 exit criteria

- `make test` passes in `src/django-backend`.
- `make lint` passes in `src/django-backend`.
- All three endpoints (`GET /api/i18n/{locale}`, `GET /api/i18n/{locale}/version`, `PATCH /api/i18n/{locale}/{key}`) return the shapes documented in this plan.
- Editing via PATCH writes an audit row automatically.
- Editing via PATCH fires the webhook (visible via logs or a real webhook listener).
- OpenAPI spec is regenerated.

When all checked, come back for Phase 2 (web-ui bilingual rendering), which will consume the API built here.

---

## Self-review notes

- **Spec coverage:**
  - Data model (`Translation`, `TranslationAudit`, uniqueness on `(locale, key)`, `source_hash`, `updated_by`, `is_machine_translated`, `retired`): Tasks 2, 3.
  - `GET /api/i18n/<locale>`: Task 5.
  - `GET /api/i18n/<locale>/version`: Task 6.
  - `PATCH /api/i18n/<locale>/<key>`: Task 8.
  - Webhook on edit: Tasks 7, 8.
  - Audit-on-save: Task 3.
  - MT flag flips on human edit: Task 8.
- **Deliberately deferred to later phases:**
  - Key-naming convention enforcement (lint) — Phase 3.
  - System pseudo-user for MT seeds — Phase 3 (when MT-generation lands); until then, `updated_by` stays null for seeds, which the model already allows.
  - `source_hash` population — Phase 3 (generated by the MT command).
  - Editor worklist — Phase 5.
