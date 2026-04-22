# Translations Backend Implementation Plan (Phase 1 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django backend for dynamic translations: two tables (`Translation`, `TranslationAudit`), a service layer (`services/translations/` with handler + query interfaces and django_impl classes), three HTTP endpoints (catalog read, version probe, edit), and a webhook that notifies the web-ui on edits.

**Architecture:** New Django app `apps.translations` with two models. New service layer at `services/translations/` following the existing handler-interface / query-interface / django_impl pattern — this is a strict architectural rule: `api/routers/*.py` MUST NOT touch the ORM directly; all DB access goes through `HANDLERS.translations` (writes/side-effects) and `REPO.translations` (reads). The router becomes a 3-endpoint shim that calls into the service layer. The handler owns side-effects including flipping `is_machine_translated` and firing the revalidation webhook.

**Tech Stack:** Django 5, Django-Ninja, pytest + hamcrest, factory_boy (all already in the repo).

**Spec:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`

**Out of scope for this phase:** Web-UI changes, `next-intl` setup, inline edit UX, MT generation, lint rules, editor worklist.

---

## File Structure

### New files

- `src/django-backend/apps/translations/__init__.py` ✓ (Task 1)
- `src/django-backend/apps/translations/apps.py` ✓ (Task 1)
- `src/django-backend/apps/translations/models.py` ✓ (Tasks 2+3)
- `src/django-backend/apps/translations/admin.py` (Task 11)
- `src/django-backend/apps/translations/migrations/__init__.py` ✓ (Task 1)
- `src/django-backend/apps/translations/migrations/0001_initial.py` ✓ (Task 2)
- `src/django-backend/apps/translations/migrations/0002_translationaudit.py` ✓ (Task 3)
- `src/django-backend/apps/translations/webhooks.py` (Task 7)
- `src/django-backend/services/translations/__init__.py` (Task 5)
- `src/django-backend/services/translations/handler_interface.py` (Task 5)
- `src/django-backend/services/translations/query_interface.py` (Task 5)
- `src/django-backend/services/translations/django_impl/__init__.py` (Task 5)
- `src/django-backend/services/translations/django_impl/handler.py` (Task 8)
- `src/django-backend/services/translations/django_impl/query.py` (Task 6)
- `src/django-backend/services/translations/django_impl/test_handler.py` (Task 8)
- `src/django-backend/services/translations/django_impl/test_query.py` (Task 6)
- `src/django-backend/api/schemas/translations.py` ✓ (Task 4)
- `src/django-backend/api/routers/translations.py` (Task 10)
- `src/django-backend/api/routers/test_translations.py` (Task 10)
- `src/django-backend/tests/test_translations_webhook.py` (Task 7)

### Modified files

- `src/django-backend/project_showcase/settings.py` — `INSTALLED_APPS` ✓ (Task 1); `WEB_UI_REVALIDATE_URL` / `WEB_UI_REVALIDATE_SECRET` (Task 7).
- `src/django-backend/api/main.py` — register router (Task 10).
- `src/django-backend/tests/factories.py` — `TranslationFactory` ✓ (Task 2).
- `src/django-backend/services/__init__.py` — wire translations into `HandlerServices` + `QueryServices` (Task 9).

---

## Codebase conventions observed

- Routers (`api/routers/`) must be thin. They call `HANDLERS.<name>.method(...)` or `REPO.<name>.method(...)` — they must not touch `.objects.` directly.
- Each service defines an abstract `HandlerInterface` and/or `QueryInterface` plus a concrete `DjangoXHandler`/`DjangoXQuery` in `django_impl/`.
- Concrete Django implementations live in `django_impl/handler.py` and `django_impl/query.py`, exported via `django_impl/__init__.py`.
- Unit tests for service classes live alongside them: `django_impl/test_handler.py`, `django_impl/test_query.py`.
- `services/__init__.py` exports `HANDLERS` (writes) and `REPO` (reads) as dataclass-backed registries.
- Tests use pytest + PyHamcrest (`assert_that`, `equal_to`, `has_entries`) + factories from `tests/factories.py`.
- Authentication: `from api.auth.security import auth` (ninja `HttpBearer`). Use `auth=auth` on endpoints that require login.

---

## Version control

User uses **jj** (jujutsu), not git. Per-task commits:

```bash
jj commit -m "<type>(translations): <message>"
```

Each task ends with a jj commit. Already-landed tasks 1–4 have jj commits `uwqv`, `wtuw`, `kxmv`, `mrns`.

---

## Task 1: Scaffold the `translations` Django app ✓ DONE

(Completed in jj change `uwqv`. See git history.)

---

## Task 2: `Translation` model (TDD) ✓ DONE

(Completed in jj change `wtuw`. 3 tests in `TestTranslationModel`.)

---

## Task 3: `TranslationAudit` model (TDD) ✓ DONE

(Completed in jj change `kxmv`. 3 tests in `TestAuditWriteOnSave`. Save hook writes audit only when text changes.)

---

## Task 4: Ninja schemas ✓ DONE

(Completed in jj change `mrns`. `TranslationPatchRequest`, `TranslationResponse`, `TranslationVersionResponse`.)

---

## Task 5: Service interfaces (no tests — contracts only)

**Why:** Before writing implementations or router code, nail down the contract the router will speak to. Tasks 6 and 8 fill in the django_impl.

**Files:**
- Create: `src/django-backend/services/translations/__init__.py` (empty)
- Create: `src/django-backend/services/translations/handler_interface.py`
- Create: `src/django-backend/services/translations/query_interface.py`
- Create: `src/django-backend/services/translations/django_impl/__init__.py` (empty for now)

- [ ] **Step 1: Create package files**

`src/django-backend/services/translations/__init__.py`: (empty)

`src/django-backend/services/translations/django_impl/__init__.py`: (empty — will export classes after Tasks 6 and 8)

- [ ] **Step 2: Write `query_interface.py`**

`src/django-backend/services/translations/query_interface.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class TranslationQueryInterface(ABC):
    @abstractmethod
    def get_catalog(self, locale: str) -> dict[str, str]:
        """Return {key: text} for all non-retired rows in `locale`."""

    @abstractmethod
    def get_catalog_version(self, locale: str) -> int:
        """Return the max updated_at for `locale` as an epoch int. 0 if empty."""
```

- [ ] **Step 3: Write `handler_interface.py`**

`src/django-backend/services/translations/handler_interface.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.translations.models import Translation


class TranslationHandlerInterface(ABC):
    @abstractmethod
    def update_text(
        self,
        locale: str,
        key: str,
        text: str,
        user: AbstractBaseUser,
    ) -> Translation:
        """Upsert a translation for (locale, key). Side effects:
        - flips `is_machine_translated` to False
        - writes audit (via Translation.save hook)
        - fires the web-ui revalidation webhook
        - sets updated_by to `user`
        Returns the updated/created Translation instance.
        """
```

- [ ] **Step 4: Verify imports**

```bash
cd src/django-backend && uv run python -c "
from services.translations.query_interface import TranslationQueryInterface
from services.translations.handler_interface import TranslationHandlerInterface
print('ok')
"
```
Expected: `ok`.

- [ ] **Step 5: Lint**

```bash
cd src/django-backend && uv run ruff check services/translations/
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(translations): service interfaces (handler, query)"
```

---

## Task 6: `DjangoTranslationQuery` + unit tests (TDD)

**Files:**
- Create: `src/django-backend/services/translations/django_impl/test_query.py`
- Create: `src/django-backend/services/translations/django_impl/query.py`
- Modify: `src/django-backend/services/translations/django_impl/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `src/django-backend/services/translations/django_impl/test_query.py`:
```python
import pytest
from hamcrest import assert_that, equal_to, has_entries, has_key, is_not

from services.translations.django_impl.query import DjangoTranslationQuery
from tests.factories import TranslationFactory


@pytest.mark.django_db
class TestGetCatalog:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_returns_key_text_map_for_locale(self) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="nav.about", text="Um okkur")
        TranslationFactory(locale="en", key="nav.home", text="Home")

        result = self.query.get_catalog("is")

        assert_that(result, equal_to({"nav.home": "Heim", "nav.about": "Um okkur"}))

    def test_excludes_retired_rows(self) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        TranslationFactory(locale="is", key="old.key", text="Gamalt", retired=True)

        result = self.query.get_catalog("is")

        assert_that(result, has_entries(**{"nav.home": "Heim"}))
        assert_that(result, is_not(has_key("old.key")))

    def test_unknown_locale_returns_empty(self) -> None:
        assert_that(self.query.get_catalog("xx"), equal_to({}))


@pytest.mark.django_db
class TestGetCatalogVersion:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_empty_returns_zero(self) -> None:
        assert_that(self.query.get_catalog_version("is"), equal_to(0))

    def test_returns_max_updated_at_as_epoch(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        assert_that(
            self.query.get_catalog_version("is"),
            equal_to(int(t.updated_at.timestamp())),
        )

    def test_scoped_by_locale(self) -> None:
        TranslationFactory(locale="is", key="a", text="A-is")
        en = TranslationFactory(locale="en", key="b", text="B-en")

        assert_that(
            self.query.get_catalog_version("en"),
            equal_to(int(en.updated_at.timestamp())),
        )
```

- [ ] **Step 2: Run to verify fail**

```bash
cd src/django-backend && uv run pytest services/translations/django_impl/test_query.py -v
```
Expected: FAIL — `DjangoTranslationQuery` not defined.

- [ ] **Step 3: Implement the query**

Create `src/django-backend/services/translations/django_impl/query.py`:
```python
from __future__ import annotations

from django.db.models import Max

from apps.translations.models import Translation
from services.translations.query_interface import TranslationQueryInterface


class DjangoTranslationQuery(TranslationQueryInterface):
    def get_catalog(self, locale: str) -> dict[str, str]:
        rows = Translation.objects.filter(locale=locale, retired=False).values_list(
            "key", "text"
        )
        return dict(rows)

    def get_catalog_version(self, locale: str) -> int:
        max_updated = Translation.objects.filter(locale=locale).aggregate(
            m=Max("updated_at")
        )["m"]
        return int(max_updated.timestamp()) if max_updated else 0
```

- [ ] **Step 4: Export from `django_impl/__init__.py`**

Replace `src/django-backend/services/translations/django_impl/__init__.py`:
```python
from .query import DjangoTranslationQuery

__all__ = ["DjangoTranslationQuery"]
```

(The handler will be added here in Task 8.)

- [ ] **Step 5: Run tests to verify pass**

```bash
cd src/django-backend && uv run pytest services/translations/django_impl/test_query.py -v
```
Expected: 6 tests pass.

- [ ] **Step 6: Lint**

```bash
cd src/django-backend && uv run ruff check services/translations/
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): DjangoTranslationQuery"
```

---

## Task 7: Revalidation webhook helper (TDD)

**Why:** Standalone module the handler will call on update. Kept thin and defensive — never raises.

**Files:**
- Modify: `src/django-backend/project_showcase/settings.py` (add settings)
- Create: `src/django-backend/apps/translations/webhooks.py`
- Create: `src/django-backend/tests/test_translations_webhook.py`

- [ ] **Step 1: Add settings entries**

In `src/django-backend/project_showcase/settings.py`, add a section at the bottom (if `import os` is not already imported at the top, add it):
```python
# Translations — web-ui revalidation webhook
WEB_UI_REVALIDATE_URL = os.environ.get("WEB_UI_REVALIDATE_URL", "")
WEB_UI_REVALIDATE_SECRET = os.environ.get("WEB_UI_REVALIDATE_SECRET", "")
```

- [ ] **Step 2: Write the failing test**

Create `src/django-backend/tests/test_translations_webhook.py`:
```python
from unittest.mock import patch

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
        args = post.call_args.args
        kwargs = post.call_args.kwargs
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

- [ ] **Step 3: Run to verify fail**

```bash
cd src/django-backend && uv run pytest tests/test_translations_webhook.py -v
```
Expected: FAIL — module does not exist.

- [ ] **Step 4: Implement the helper**

Create `src/django-backend/apps/translations/webhooks.py`:
```python
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_web_ui(locale: str) -> None:
    """Best-effort POST to the web-ui's revalidation endpoint. Never raises."""
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

- [ ] **Step 5: Verify `requests` is available**

```bash
cd src/django-backend && uv run python -c "import requests; print(requests.__version__)"
```
Expected: version string. If missing, it is almost certainly already a transitive dep; check `grep -rn 'import requests' src/django-backend --include='*.py'` — if nothing else uses it, add it to `pyproject.toml`.

- [ ] **Step 6: Run tests to verify pass**

```bash
cd src/django-backend && uv run pytest tests/test_translations_webhook.py -v
```
Expected: 3 tests pass.

- [ ] **Step 7: Lint**

```bash
cd src/django-backend && uv run ruff check apps/translations/ tests/test_translations_webhook.py
```
Expected: clean.

- [ ] **Step 8: Commit**

```bash
jj commit -m "feat(translations): revalidation webhook helper"
```

---

## Task 8: `DjangoTranslationHandler.update_text` + unit tests (TDD)

**Files:**
- Create: `src/django-backend/services/translations/django_impl/test_handler.py`
- Create: `src/django-backend/services/translations/django_impl/handler.py`
- Modify: `src/django-backend/services/translations/django_impl/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `src/django-backend/services/translations/django_impl/test_handler.py`:
```python
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from apps.translations.models import Translation, TranslationAudit
from services.translations.django_impl.handler import DjangoTranslationHandler
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestUpdateText:
    def setup_method(self) -> None:
        self.handler = DjangoTranslationHandler()

    def test_updates_existing_row_and_flips_mt_flag(self) -> None:
        user = UserFactory()
        t = TranslationFactory(
            locale="is",
            key="nav.home",
            text="Heim",
            is_machine_translated=True,
        )
        with patch(
            "services.translations.django_impl.handler.notify_web_ui"
        ) as notify:
            result = self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )

        t.refresh_from_db()
        assert_that(t.text, equal_to("Forsíða"))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(t.updated_by, equal_to(user))
        assert_that(result.pk, equal_to(t.pk))
        notify.assert_called_once_with("is")

    def test_writes_audit_entry(self) -> None:
        user = UserFactory()
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch("services.translations.django_impl.handler.notify_web_ui"):
            self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )
        audit = (
            TranslationAudit.objects.filter(translation=t)
            .order_by("-changed_at")
            .first()
        )
        assert_that(audit.old_text, equal_to("Heim"))
        assert_that(audit.new_text, equal_to("Forsíða"))
        assert_that(audit.changed_by, equal_to(user))

    def test_creates_row_if_missing(self) -> None:
        user = UserFactory()
        with patch("services.translations.django_impl.handler.notify_web_ui"):
            result = self.handler.update_text(
                locale="is", key="new.key", text="Nýtt", user=user
            )
        t = Translation.objects.get(locale="is", key="new.key")
        assert_that(t.text, equal_to("Nýtt"))
        assert_that(t.updated_by, equal_to(user))
        assert_that(t.is_machine_translated, equal_to(False))
        assert_that(result.pk, equal_to(t.pk))

    def test_webhook_failure_does_not_fail_update(self) -> None:
        user = UserFactory()
        TranslationFactory(locale="is", key="nav.home", text="Heim")
        with patch(
            "services.translations.django_impl.handler.notify_web_ui",
            side_effect=Exception("boom"),
        ):
            # Handler must defend against a raising webhook even though
            # notify_web_ui itself never raises — belt and braces.
            self.handler.update_text(
                locale="is", key="nav.home", text="Forsíða", user=user
            )
        t = Translation.objects.get(locale="is", key="nav.home")
        assert_that(t.text, equal_to("Forsíða"))
```

- [ ] **Step 2: Run to verify fail**

```bash
cd src/django-backend && uv run pytest services/translations/django_impl/test_handler.py -v
```
Expected: FAIL — handler module does not exist.

- [ ] **Step 3: Implement the handler**

Create `src/django-backend/services/translations/django_impl/handler.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.translations.models import Translation
from apps.translations.webhooks import notify_web_ui
from services.translations.handler_interface import TranslationHandlerInterface

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

logger = logging.getLogger(__name__)


class DjangoTranslationHandler(TranslationHandlerInterface):
    def update_text(
        self,
        locale: str,
        key: str,
        text: str,
        user: AbstractBaseUser,
    ) -> Translation:
        try:
            t = Translation.objects.get(locale=locale, key=key)
            t.text = text
            t.is_machine_translated = False
            t.updated_by = user
            t.save()
        except Translation.DoesNotExist:
            t = Translation.objects.create(
                locale=locale,
                key=key,
                text=text,
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

- [ ] **Step 4: Export from `django_impl/__init__.py`**

Replace `src/django-backend/services/translations/django_impl/__init__.py`:
```python
from .handler import DjangoTranslationHandler
from .query import DjangoTranslationQuery

__all__ = ["DjangoTranslationHandler", "DjangoTranslationQuery"]
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd src/django-backend && uv run pytest services/translations/django_impl/ -v
```
Expected: all tests (query + handler) pass — 10 tests.

- [ ] **Step 6: Lint**

```bash
cd src/django-backend && uv run ruff check services/translations/
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): DjangoTranslationHandler.update_text"
```

---

## Task 9: Wire services into `services/__init__.py`

**Files:**
- Modify: `src/django-backend/services/__init__.py`

- [ ] **Step 1: Add imports**

In `src/django-backend/services/__init__.py`, add to the import block at the top (alongside the other `services.<name>.django_impl` and `services.<name>.X_interface` imports):
```python
from services.translations.django_impl import (
    DjangoTranslationHandler,
    DjangoTranslationQuery,
)
from services.translations.handler_interface import TranslationHandlerInterface
from services.translations.query_interface import TranslationQueryInterface
```

- [ ] **Step 2: Add field to `HandlerServices`**

In the `HandlerServices` dataclass, add a field alphabetically (or at the bottom, matching surrounding style):
```python
    translations: TranslationHandlerInterface = field(
        default_factory=DjangoTranslationHandler
    )
```

- [ ] **Step 3: Add field to `QueryServices`**

In the `QueryServices` dataclass, add:
```python
    translations: TranslationQueryInterface = field(
        default_factory=DjangoTranslationQuery
    )
```

- [ ] **Step 4: Verify `HANDLERS` and `REPO` still instantiate**

```bash
cd src/django-backend && uv run python -c "
from services import HANDLERS, REPO
print(type(HANDLERS.translations).__name__)
print(type(REPO.translations).__name__)
"
```
Expected:
```
DjangoTranslationHandler
DjangoTranslationQuery
```

- [ ] **Step 5: Django system check**

```bash
cd src/django-backend && uv run python manage.py check
```
Expected: no issues.

- [ ] **Step 6: Lint**

```bash
cd src/django-backend && uv run ruff check services/__init__.py
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): wire HANDLERS.translations / REPO.translations"
```

---

## Task 10: Router (GET catalog, GET version, PATCH) + tests (TDD)

This is now intentionally thin — no ORM access in the router.

**Files:**
- Create: `src/django-backend/api/routers/test_translations.py`
- Create: `src/django-backend/api/routers/translations.py`
- Modify: `src/django-backend/api/main.py`

- [ ] **Step 1: Write the failing tests**

Create `src/django-backend/api/routers/test_translations.py`:
```python
import pytest
from hamcrest import assert_that, equal_to, has_entries, has_key, is_not

from api.auth.jwt import create_access_token
from apps.translations.models import Translation
from tests.factories import TranslationFactory, UserFactory


def _auth_header(user) -> dict[str, str]:
    token = create_access_token(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


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
        TranslationFactory(locale="is", key="old.key", text="Gamalt", retired=True)

        response = client.get("/api/i18n/is")

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(**{"nav.home": "Heim"}))
        assert_that(body, is_not(has_key("old.key")))

    def test_unknown_locale_returns_empty(self, client) -> None:
        response = client.get("/api/i18n/xx")
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), equal_to({}))


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
        assert_that(
            response.json()["version"], equal_to(int(t.updated_at.timestamp()))
        )


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

    def test_updates_row_via_handler(self, client) -> None:
        user = UserFactory()
        TranslationFactory(
            locale="is",
            key="nav.home",
            text="Heim",
            is_machine_translated=True,
        )
        # Router should delegate; we don't mock HANDLERS — we rely on the
        # handler's own unit tests for detailed behavior and just confirm
        # the round-trip works.
        response = client.patch(
            "/api/i18n/is/nav.home",
            data='{"text":"Forsíða"}',
            content_type="application/json",
            **_auth_header(user),
        )
        assert_that(response.status_code, equal_to(200))
        t = Translation.objects.get(locale="is", key="nav.home")
        assert_that(t.text, equal_to("Forsíða"))
        assert_that(t.is_machine_translated, equal_to(False))

    def test_creates_row_if_missing(self, client) -> None:
        user = UserFactory()
        response = client.patch(
            "/api/i18n/is/new.key",
            data='{"text":"Nýtt"}',
            content_type="application/json",
            **_auth_header(user),
        )
        assert_that(response.status_code, equal_to(200))
        assert_that(Translation.objects.filter(locale="is", key="new.key").exists(), equal_to(True))
```

- [ ] **Step 2: Run to verify fail**

```bash
cd src/django-backend && uv run pytest api/routers/test_translations.py -v
```
Expected: FAIL — route not registered (404s).

- [ ] **Step 3: Implement the router (thin — no ORM)**

Create `src/django-backend/api/routers/translations.py`:
```python
from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.translations import (
    TranslationPatchRequest,
    TranslationResponse,
    TranslationVersionResponse,
)
from services import HANDLERS, REPO

router = Router()


@router.get("/{locale}", response=dict[str, str], tags=["Translations"])
def get_catalog(request: HttpRequest, locale: str) -> dict[str, str]:
    """Return the full non-retired translation catalog for a locale."""
    return REPO.translations.get_catalog(locale)


@router.get(
    "/{locale}/version",
    response=TranslationVersionResponse,
    tags=["Translations"],
)
def get_version(request: HttpRequest, locale: str) -> dict[str, int]:
    """Return a monotonic version for a locale's catalog (max updated_at as epoch)."""
    return {"version": REPO.translations.get_catalog_version(locale)}


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
):
    """Edit a translation. Creates the row if missing. Requires authentication."""
    return HANDLERS.translations.update_text(
        locale=locale, key=key, text=payload.text, user=request.auth
    )
```

- [ ] **Step 4: Register router in `api/main.py`**

Modify `src/django-backend/api/main.py`. Add `translations` to the router imports (alphabetical order) and add an `add_router("/i18n", ...)` line alongside the others:
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
# ... unchanged ...
api.add_router("/users", users.router)
api.add_router("/i18n", translations.router)  # <-- new
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd src/django-backend && uv run pytest api/routers/test_translations.py -v
```
Expected: all 8 tests pass.

- [ ] **Step 6: Lint**

```bash
cd src/django-backend && uv run ruff check api/routers/translations.py api/routers/test_translations.py api/main.py
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
jj commit -m "feat(translations): HTTP router wired to HANDLERS/REPO"
```

---

## Task 11: Admin registration

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

- [ ] **Step 2: Django check**

```bash
cd src/django-backend && uv run python manage.py check
```

- [ ] **Step 3: Lint**

```bash
cd src/django-backend && uv run ruff check apps/translations/admin.py
```

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(translations): admin registration (audit read-only)"
```

---

## Task 12: Regenerate OpenAPI + full test suite + lint

- [ ] **Step 1: Regen OpenAPI spec**

```bash
cd src/django-backend && make extract-openapi
```

- [ ] **Step 2: Run the full backend test suite**

```bash
cd src/django-backend && make test
```
Expected: all tests pass, no regressions.

- [ ] **Step 3: Run linter**

```bash
cd src/django-backend && make lint
```
Expected: `ruff check` and `ruff format --check` both clean. If format fails, run `uv run ruff format .`.

- [ ] **Step 4: Commit**

```bash
jj commit -m "chore(translations): regen OpenAPI + lint clean"
```

---

## Task 13: End-to-end smoke test

- [ ] **Step 1: Start backend locally**

```bash
cd src/django-backend && uv run python manage.py migrate && uv run python manage.py runserver
```

- [ ] **Step 2: Seed a row via shell**

```bash
cd src/django-backend && uv run python manage.py shell -c "
from apps.translations.models import Translation
Translation.objects.create(locale='is', key='nav.home', text='Heim', source_hash='abc', is_machine_translated=True)
print('seeded')
"
```

- [ ] **Step 3: GET /api/i18n/is**

```bash
curl http://localhost:8000/api/i18n/is
```
Expected: `{"nav.home":"Heim"}`.

- [ ] **Step 4: GET /api/i18n/is/version**

```bash
curl http://localhost:8000/api/i18n/is/version
```
Expected: `{"version":<epoch>}`.

- [ ] **Step 5: PATCH without auth → 401**

```bash
curl -X PATCH http://localhost:8000/api/i18n/is/nav.home \
  -H 'Content-Type: application/json' -d '{"text":"Forsíða"}'
```
Expected: 401.

- [ ] **Step 6: PATCH with valid token**

Obtain a token via `/api/auth/login`. Then:
```bash
curl -X PATCH http://localhost:8000/api/i18n/is/nav.home \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"text":"Forsíða"}'
```
Expected: 200 with updated row. Re-hit `GET /api/i18n/is` to verify.

- [ ] **Step 7: Verify webhook fires**

Set `WEB_UI_REVALIDATE_URL=https://httpbin.org/post` + a secret and run the server again; perform another PATCH. No warnings in the log means the fire-and-forget succeeded.

---

## Phase 1 exit criteria

- `make test` and `make lint` pass cleanly.
- Router contains zero `.objects.` calls (enforced by grep; the only DB access lives under `services/translations/django_impl/`).
- All three endpoints return documented shapes and do what's expected end-to-end.
- Admin registered.
- OpenAPI regenerated.

## Self-review notes

- **Spec coverage:** all model fields, uniqueness, audit, MT flag flip, retired filtering, catalog endpoint, version endpoint, PATCH with auth + audit, webhook firing — covered by Tasks 2, 3, 6, 7, 8, 10.
- **Architectural policy:** ✅ Router has no ORM access. DB access lives only in `services/translations/django_impl/`.
- **Deferred to later phases:** MT generation (Phase 3), `source_hash` population (Phase 3), lint rules (Phase 3), editor worklist (Phase 5), system pseudo-user for seeds (Phase 3).
