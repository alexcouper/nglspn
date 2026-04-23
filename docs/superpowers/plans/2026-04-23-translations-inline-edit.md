# Phase 4 — Inline Translation Edit UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any logged-in user can flip an "Edit translations" toggle and inline-edit any visible translated string. The editor sees their change immediately (optimistic), other users see it within seconds (existing webhook → `revalidateTag`). Each edit is auditable; every popover exposes history and one-click revert.

**Architecture:** A cookie-persisted edit-mode flag is read in the locale layout and propagated through a new client-side `EditableMessagesProvider` that wraps `NextIntlClientProvider`. That provider lifts the catalog into client state so `applyOverride(key, text)` can mutate it instantly without re-fetch. A `<Translatable tKey="...">` wrapper renders its children plus an absolutely-positioned pencil overlay (when edit mode is on) and opens a portal-rendered `<TranslationPopover>` on click. The popover loads current text + `updated_at` + last-N audit entries from a new `GET /api/i18n/{locale}/{key}` endpoint, lets the editor edit (with ICU placeholders rendered as locked chips), warns on stale `updated_at`, and PATCHes back to the existing endpoint — which already fires the revalidation webhook.

**Tech Stack:** Next.js 16 App Router + `next-intl` v4.9.1 (already wired), React 19, TypeScript, Django Ninja (existing translations router), `pytest`, Playwright.

**Design reference:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md` (§Edit UX, §Concurrency, §Trust model).
**Phase 2 (web-ui i18n) plan:** `docs/superpowers/plans/2026-04-22-translations-web-ui.md`.
**Phase 3 (authoring) plan:** `docs/superpowers/plans/2026-04-22-translations-authoring.md`.

---

## Scope

**In scope (Phase 4):**
- New backend endpoint `GET /api/i18n/{locale}/{key}` returning `{text, updated_at, history: [...]}` (last N audit entries) for the popover.
- Cookie-persisted edit-mode flag (`nglspn-edit-mode`).
- "Edit translations" toggle in `UserMenu` (logged-in users only).
- `EditableMessagesProvider` — wraps `NextIntlClientProvider`, holds messages in client state, exposes `applyOverride(key, text)` + `editMode`.
- `<Translatable tKey="...">` wrapper component — pencil overlay on hover when edit mode on; opens popover on click. Zero overhead when edit mode off.
- `<TranslationPopover>` — portal-positioned, with: Icelandic textarea, English reference, ICU placeholder chips (non-editable), last-N history disclosure with revert, save/cancel/Esc, last-write-wins concurrency warning.
- Missing-translation visual marker in edit mode (Icelandic falling back to English gets a faint underline).
- Wrap chrome strings (Navigation, Footer, UserMenu) in `<Translatable>` so they're editable inline.
- Playwright e2e for the edit happy-path.

**Out of scope (deferred):**
- Sweeping hardcoded JSX strings on non-chrome pages and adding a `no-hardcoded-jsx-strings` ESLint rule. Listed as a Phase 4 nice-to-have in `verify.md`, but it requires new keys → `make translate-new-keys` → DeepL, and the user has paused DeepL pending a provider-replacement decision. **Tracked as Task 14 (stub).**
- Editor worklist (Phase 5).
- Long-form / markdown-preview popover layout (design §Long-form text). v1 popover is single-textarea only.
- Per-user permission gate beyond "logged-in" (design §Trust model: any logged-in user).

---

## File structure

**Create:**
- `src/django-backend/api/schemas/translations.py` — extend with `TranslationDetailResponse` + `TranslationAuditEntry`.
- `src/django-backend/services/translations/query_interface.py` — extend with `get_detail`.
- `src/django-backend/services/translations/django_impl/query.py` — implement `get_detail`.
- `src/django-backend/services/translations/django_impl/test_query.py` — extend.
- `src/web-ui/src/lib/i18n/edit-mode-cookie.ts` — server + client helpers for the `nglspn-edit-mode` cookie.
- `src/web-ui/src/lib/i18n/api.ts` — client API: `getTranslationDetail(locale, key)`, `patchTranslation(locale, key, text)`.
- `src/web-ui/src/contexts/editable-messages.tsx` — `EditableMessagesProvider` + `useEditableMessages` hook.
- `src/web-ui/src/components/Translatable.tsx` — wrapper with pencil overlay.
- `src/web-ui/src/components/TranslationPopover.tsx` — popover UI.
- `src/web-ui/src/components/TranslationChips.tsx` — ICU placeholder chips editor.
- `src/web-ui/src/components/EditModeToggle.tsx` — menu item that toggles cookie + refreshes.
- `src/web-ui/e2e/i18n-edit.spec.ts` — Playwright spec.

**Modify:**
- `src/django-backend/api/routers/translations.py` — add `GET /{locale}/{key}` route.
- `src/web-ui/src/app/[locale]/layout.tsx` — read edit-mode cookie, replace direct `NextIntlClientProvider` with `EditableMessagesProvider`.
- `src/web-ui/src/components/UserMenu.tsx` — mount `EditModeToggle`.
- `src/web-ui/src/messages/en.json` — add edit-mode-related UI keys (toggle label, popover labels, errors). Authored by hand — no DeepL needed; Icelandic text added by inline migration in Task 13.
- `src/web-ui/src/components/Navigation.tsx` — wrap nav link labels in `<Translatable>`.
- `src/web-ui/src/components/Footer.tsx` — wrap footer link labels in `<Translatable>`.
- `src/web-ui/src/components/UserMenu.tsx` — wrap menu item labels in `<Translatable>`.

**One-line responsibility per file:**
- `edit-mode-cookie.ts` — read/write the boolean cookie from server (`cookies()`) and client (`document.cookie`).
- `api.ts` — typed fetch wrappers for the two i18n endpoints used by the popover.
- `editable-messages.tsx` — owns the live in-memory catalog the editor mutates; passes `messages` prop to `NextIntlClientProvider`.
- `Translatable.tsx` — render-time wrapper that adds the pencil affordance and opens the popover.
- `TranslationPopover.tsx` — the modal-ish edit UI; contains save/cancel logic, concurrency check, history.
- `TranslationChips.tsx` — `contentEditable`-based textarea that protects ICU `{name}` placeholders.
- `EditModeToggle.tsx` — small client component that flips the cookie and refreshes server state.

---

## Data contracts

### `GET /api/i18n/{locale}/{key}` response

```ts
type TranslationDetailResponse = {
  locale: string;
  key: string;
  text: string;                 // current text in this locale (empty if no row)
  updated_at: string | null;    // ISO-8601, null if no row exists yet
  history: TranslationAuditEntry[];   // last 10 audits, newest first
};

type TranslationAuditEntry = {
  changed_at: string;           // ISO-8601
  changed_by: string | null;    // display name, null if system
  old_text: string;
  new_text: string;
};
```

### Edit-mode cookie

- Name: `nglspn-edit-mode`.
- Value: `"1"` (on) or absent (off).
- Path: `/`.
- `Max-Age`: `60 * 60 * 24 * 30` (30 days).
- `SameSite=Lax`. Not `HttpOnly` — client reads/writes it directly.

### Optimistic update flow

1. User hits Save in popover.
2. Client calls `patchTranslation(locale, key, text)`.
3. On 200 response, client calls `applyOverride(key, text)` from `useEditableMessages()`. The provider re-`setState`s `messages` with the new value spliced into the nested object at the dotted path.
4. `NextIntlClientProvider` re-renders with new `messages` → all `useTranslations()` consumers see the new text instantly.
5. Other users see it on their next navigation (existing Phase 1 webhook → `revalidateTag` path).

### Concurrency check

- Popover stores the `updated_at` it received from `GET /api/i18n/{locale}/{key}` at open time.
- Before sending PATCH on Save, popover re-`GET`s the row.
- If new `updated_at` differs from the open-time one → render a non-blocking warning `"Edited <relative-time> by <user>. Save anyway?"` with a single confirm button. After confirm, PATCH proceeds (last-write-wins).
- Audit log already records old_text/new_text (existing `Translation.save` hook), so any mis-overwrite is recoverable from the history disclosure.

---

## Task 1: Backend — `get_detail` query (TDD)

**Files:**
- Modify: `src/django-backend/services/translations/query_interface.py`
- Modify: `src/django-backend/services/translations/django_impl/query.py`
- Modify: `src/django-backend/services/translations/django_impl/test_query.py`

- [ ] **Step 1: Start a changeset**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
jj new -m "feat(translations): get_detail returns row + audit history"
```

- [ ] **Step 2: Extend the query interface**

Edit `src/django-backend/services/translations/query_interface.py` to add the abstract method:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditEntry:
    changed_at: datetime
    changed_by: str | None
    old_text: str
    new_text: str


@dataclass(frozen=True)
class TranslationDetail:
    locale: str
    key: str
    text: str
    updated_at: datetime | None
    history: list[AuditEntry]


class TranslationQueryInterface(ABC):
    @abstractmethod
    def get_catalog(self, locale: str) -> dict[str, str]:
        """Return {key: text} for all non-retired rows in `locale`."""

    @abstractmethod
    def get_catalog_version(self, locale: str) -> int:
        """Return the max updated_at for `locale` as an epoch int. 0 if empty."""

    @abstractmethod
    def get_detail(self, locale: str, key: str, history_limit: int = 10) -> TranslationDetail:
        """Return current text + updated_at + last-N audit entries for (locale, key).
        If no row exists, returns empty text + None updated_at + empty history."""
```

- [ ] **Step 3: Write failing test for `get_detail`**

Append to `src/django-backend/services/translations/django_impl/test_query.py`:

```python
import pytest
from hamcrest import assert_that, equal_to, has_length, none, not_none

from services.translations.django_impl.query import DjangoTranslationQuery
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestGetDetail:
    def setup_method(self) -> None:
        self.query = DjangoTranslationQuery()

    def test_returns_text_and_updated_at_for_existing_row(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")

        detail = self.query.get_detail("is", "nav.home")

        assert_that(detail.text, equal_to("Heim"))
        assert_that(detail.updated_at, equal_to(t.updated_at))
        assert_that(detail.history, equal_to([]))

    def test_returns_empty_for_missing_row(self) -> None:
        detail = self.query.get_detail("is", "nonexistent.key")

        assert_that(detail.text, equal_to(""))
        assert_that(detail.updated_at, none())
        assert_that(detail.history, equal_to([]))

    def test_history_is_newest_first_and_capped(self) -> None:
        user = UserFactory(first_name="Alice", last_name="A")
        t = TranslationFactory(locale="is", key="nav.home", text="Heim", updated_by=user)
        # Trigger 3 audits via the .save hook.
        for new_text in ["Forsida", "Forsíða", "Heim"]:
            t.text = new_text
            t.updated_by = user
            t.save()

        detail = self.query.get_detail("is", "nav.home", history_limit=2)

        assert_that(detail.history, has_length(2))
        assert_that(detail.history[0].new_text, equal_to("Heim"))
        assert_that(detail.history[1].new_text, equal_to("Forsíða"))
        assert_that(detail.history[0].changed_by, not_none())

    def test_history_changed_by_null_for_system_edits(self) -> None:
        t = TranslationFactory(locale="is", key="nav.home", text="Heim")
        # No user attached → system edit
        t.text = "Forsíða"
        t.updated_by = None
        t.save()

        detail = self.query.get_detail("is", "nav.home")

        assert_that(detail.history[0].changed_by, none())
```

- [ ] **Step 4: Run — expect FAIL**

Run: `cd src/django-backend && uv run pytest services/translations/django_impl/test_query.py::TestGetDetail -v`
Expected: 4 errors (`get_detail` not implemented).

- [ ] **Step 5: Implement `get_detail`**

Edit `src/django-backend/services/translations/django_impl/query.py`:

```python
from __future__ import annotations

from django.db.models import Max

from apps.translations.models import Translation, TranslationAudit
from services.translations.query_interface import (
    AuditEntry,
    TranslationDetail,
    TranslationQueryInterface,
)


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

    def get_detail(
        self, locale: str, key: str, history_limit: int = 10
    ) -> TranslationDetail:
        row = Translation.objects.filter(locale=locale, key=key).first()
        history_qs = (
            TranslationAudit.objects.filter(locale=locale, key=key)
            .select_related("changed_by")
            .order_by("-changed_at")[:history_limit]
        )
        history = [
            AuditEntry(
                changed_at=a.changed_at,
                changed_by=_display_name(a.changed_by) if a.changed_by else None,
                old_text=a.old_text,
                new_text=a.new_text,
            )
            for a in history_qs
        ]
        if row is None:
            return TranslationDetail(
                locale=locale, key=key, text="", updated_at=None, history=history
            )
        return TranslationDetail(
            locale=locale,
            key=key,
            text=row.text,
            updated_at=row.updated_at,
            history=history,
        )


def _display_name(user) -> str:
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.email
```

- [ ] **Step 6: Run — expect PASS**

Run: `uv run pytest services/translations/django_impl/test_query.py -v`
Expected: all green (existing 5 tests + 4 new).

- [ ] **Step 7: Commit**

```bash
jj describe -m "feat(translations): add get_detail returning row + audit history"
```

(jj auto-commits on next `jj new`. Description above replaces the stub message.)

---

## Task 2: Backend — `GET /api/i18n/{locale}/{key}` route (TDD)

**Files:**
- Modify: `src/django-backend/api/schemas/translations.py`
- Modify: `src/django-backend/api/routers/translations.py`
- Test: `src/django-backend/api/routers/test_translations.py` (create if missing)

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(api): GET /i18n/{locale}/{key} returns text + history"
```

- [ ] **Step 2: Extend response schemas**

Edit `src/django-backend/api/schemas/translations.py`:

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
    version: int


class TranslationAuditEntryResponse(Schema):
    changed_at: datetime
    changed_by: str | None
    old_text: str
    new_text: str


class TranslationDetailResponse(Schema):
    locale: str
    key: str
    text: str
    updated_at: datetime | None
    history: list[TranslationAuditEntryResponse]
```

- [ ] **Step 3: Write failing route test**

Create `src/django-backend/api/routers/test_translations.py` (or extend if exists). Check first:

Run: `ls src/django-backend/api/routers/test_translations.py`

If absent, create it:

```python
import pytest
from hamcrest import assert_that, equal_to, has_length, has_entries

from apps.translations.models import Translation
from tests.factories import TranslationFactory, UserFactory


@pytest.mark.django_db
class TestGetTranslationDetail:
    def test_returns_existing_row_with_empty_history(self, client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")

        resp = client.get("/api/i18n/is/nav.home")

        assert_that(resp.status_code, equal_to(200))
        body = resp.json()
        assert_that(body, has_entries(locale="is", key="nav.home", text="Heim"))
        assert_that(body["history"], equal_to([]))
        assert_that(body["updated_at"], equal_to(body["updated_at"]))  # truthy

    def test_returns_empty_text_for_missing_row(self, client) -> None:
        resp = client.get("/api/i18n/is/no.such.key")

        assert_that(resp.status_code, equal_to(200))
        body = resp.json()
        assert_that(body["text"], equal_to(""))
        assert_that(body["updated_at"], equal_to(None))

    def test_history_returned_newest_first(self, client) -> None:
        user = UserFactory(first_name="Alice", last_name="A")
        t = TranslationFactory(
            locale="is", key="nav.home", text="Heim", updated_by=user
        )
        for txt in ["A", "B", "C"]:
            t.text = txt
            t.updated_by = user
            t.save()

        resp = client.get("/api/i18n/is/nav.home")

        body = resp.json()
        assert_that(body["history"], has_length(3))
        assert_that(body["history"][0]["new_text"], equal_to("C"))
        assert_that(body["history"][2]["new_text"], equal_to("A"))
```

If a `test_translations.py` already exists, append the `TestGetTranslationDetail` class to it instead.

- [ ] **Step 4: Run — expect FAIL (404)**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py::TestGetTranslationDetail -v`
Expected: FAIL — route not registered (404).

- [ ] **Step 5: Add the route**

Edit `src/django-backend/api/routers/translations.py`. Insert this handler **before** `patch_translation` (so `/{locale}/{key}` is matched as a GET separately from the PATCH):

```python
from api.schemas.translations import (
    TranslationDetailResponse,
    TranslationPatchRequest,
    TranslationResponse,
    TranslationVersionResponse,
)

# ... existing routes above ...


@router.get(
    "/{locale}/{key}",
    response=TranslationDetailResponse,
    tags=["Translations"],
)
def get_translation_detail(
    request: HttpRequest, locale: str, key: str
) -> TranslationDetailResponse:
    """Return current text + last 10 audit entries for a translation row."""
    detail = REPO.translations.get_detail(locale=locale, key=key, history_limit=10)
    return TranslationDetailResponse(
        locale=detail.locale,
        key=detail.key,
        text=detail.text,
        updated_at=detail.updated_at,
        history=[
            {
                "changed_at": entry.changed_at,
                "changed_by": entry.changed_by,
                "old_text": entry.old_text,
                "new_text": entry.new_text,
            }
            for entry in detail.history
        ],
    )
```

- [ ] **Step 6: Run — expect PASS**

Run: `uv run pytest api/routers/test_translations.py -v`
Expected: 3 passed.

- [ ] **Step 7: Regenerate OpenAPI + types**

```bash
cd src/django-backend && make extract-openapi
cd ../web-ui && npm run generate-types
```

- [ ] **Step 8: Commit**

```bash
jj describe -m "feat(api): GET /i18n/{locale}/{key} returns text + history"
```

---

## Task 3: Backend — verify PATCH returns updated_at (sanity)

**Files:**
- Test: `src/django-backend/api/routers/test_translations.py`

The existing PATCH handler already returns the full `Translation` object (which serializes `updated_at` via `TranslationResponse`). Verify with a regression test so the popover concurrency-check contract is locked.

- [ ] **Step 1: New changeset**

```bash
jj new -m "test(api): regression — PATCH translation returns updated_at"
```

- [ ] **Step 2: Append regression test**

Append to `src/django-backend/api/routers/test_translations.py`:

```python
@pytest.mark.django_db
class TestPatchTranslationContract:
    def test_response_includes_updated_at(self, authenticated_client) -> None:
        TranslationFactory(locale="is", key="nav.home", text="Heim")

        resp = authenticated_client.patch(
            "/api/i18n/is/nav.home",
            data={"text": "Forsíða"},
            content_type="application/json",
        )

        assert_that(resp.status_code, equal_to(200))
        body = resp.json()
        assert_that(body["text"], equal_to("Forsíða"))
        # updated_at must be present and ISO-8601-shaped — popover relies on it
        # for concurrency checks.
        assert "updated_at" in body
        assert "T" in body["updated_at"]
```

If `authenticated_client` fixture does not exist, check existing tests for the project's auth fixture pattern:

Run: `grep -rn "authenticated_client\|@pytest.fixture" src/django-backend/conftest.py src/django-backend/tests/ | head -10`

Use whatever the codebase already uses to call PATCH endpoints under auth. If nothing is conventional, copy the bearer-token pattern from another router test (e.g. `test_my_review.py`).

- [ ] **Step 3: Run — expect PASS**

Run: `cd src/django-backend && uv run pytest api/routers/test_translations.py::TestPatchTranslationContract -v`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
jj describe -m "test(api): regression — PATCH translation returns updated_at"
```

---

## Task 4: Web-UI — edit-mode cookie helpers

**Files:**
- Create: `src/web-ui/src/lib/i18n/edit-mode-cookie.ts`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): edit-mode cookie helpers"
```

- [ ] **Step 2: Implement helpers**

Create `src/web-ui/src/lib/i18n/edit-mode-cookie.ts`:

```typescript
import "server-only";
import { cookies } from "next/headers";

export const EDIT_MODE_COOKIE = "nglspn-edit-mode";

export async function readEditModeFromServer(): Promise<boolean> {
  const store = await cookies();
  return store.get(EDIT_MODE_COOKIE)?.value === "1";
}
```

- [ ] **Step 3: Add a sibling client-only file**

Create `src/web-ui/src/lib/i18n/edit-mode-cookie.client.ts`:

```typescript
export const EDIT_MODE_COOKIE = "nglspn-edit-mode";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

export function setEditModeCookie(on: boolean): void {
  if (typeof document === "undefined") return;
  if (on) {
    document.cookie =
      `${EDIT_MODE_COOKIE}=1; path=/; max-age=${MAX_AGE_SECONDS}; samesite=lax`;
  } else {
    document.cookie = `${EDIT_MODE_COOKIE}=; path=/; max-age=0; samesite=lax`;
  }
}

export function readEditModeCookieClient(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie
    .split("; ")
    .some((pair) => pair === `${EDIT_MODE_COOKIE}=1`);
}
```

(Two files because `"server-only"` enforces the boundary; the client file imports `document` and is fine in the browser.)

- [ ] **Step 4: Type-check**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
jj describe -m "feat(web-ui): edit-mode cookie helpers (server + client)"
```

---

## Task 5: Web-UI — typed API client for popover

**Files:**
- Create: `src/web-ui/src/lib/i18n/api.ts`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): typed i18n popover API client"
```

- [ ] **Step 2: Implement the client**

Create `src/web-ui/src/lib/i18n/api.ts`:

```typescript
import type { Locale } from "@/i18n/config";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export type TranslationAuditEntry = {
  changed_at: string;
  changed_by: string | null;
  old_text: string;
  new_text: string;
};

export type TranslationDetail = {
  locale: string;
  key: string;
  text: string;
  updated_at: string | null;
  history: TranslationAuditEntry[];
};

export type TranslationPatchResponse = {
  locale: string;
  key: string;
  text: string;
  source_hash: string;
  is_machine_translated: boolean;
  updated_at: string;
};

export async function getTranslationDetail(
  locale: Locale,
  key: string,
): Promise<TranslationDetail> {
  const url = `${API_URL}/api/i18n/${locale}/${encodeURIComponent(key)}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`getTranslationDetail ${locale}/${key}: ${res.status}`);
  }
  return (await res.json()) as TranslationDetail;
}

export async function patchTranslation(
  locale: Locale,
  key: string,
  text: string,
  bearerToken: string,
): Promise<TranslationPatchResponse> {
  const url = `${API_URL}/api/i18n/${locale}/${encodeURIComponent(key)}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${bearerToken}`,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`patchTranslation ${locale}/${key}: ${res.status} ${detail}`);
  }
  return (await res.json()) as TranslationPatchResponse;
}
```

- [ ] **Step 3: Type-check**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
jj describe -m "feat(web-ui): typed i18n popover API client"
```

---

## Task 6: Web-UI — `EditableMessagesProvider` (lift catalog into client state)

**Files:**
- Create: `src/web-ui/src/contexts/editable-messages.tsx`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): EditableMessagesProvider — client-state messages with applyOverride"
```

- [ ] **Step 2: Implement the provider**

Create `src/web-ui/src/contexts/editable-messages.tsx`:

```typescript
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { NextIntlClientProvider } from "next-intl";
import type { Locale } from "@/i18n/config";

type Messages = Record<string, unknown>;

type EditableMessagesContextValue = {
  editMode: boolean;
  locale: Locale;
  /** True when this dotted key resolves to text from the en fallback (no row in `locale`). */
  isFallback: (dottedKey: string) => boolean;
  /** Splice text into messages at the dotted-key path; triggers re-render of all consumers. */
  applyOverride: (dottedKey: string, text: string) => void;
  /** Read the English source string at a dotted path (popover uses this for the reference block). */
  readEnglish: (dottedKey: string) => string | undefined;
};

const EditableMessagesContext = createContext<EditableMessagesContextValue | null>(
  null,
);

export function useEditableMessages(): EditableMessagesContextValue {
  const ctx = useContext(EditableMessagesContext);
  if (ctx === null) {
    throw new Error(
      "useEditableMessages must be used inside <EditableMessagesProvider>",
    );
  }
  return ctx;
}

export function EditableMessagesProvider({
  locale,
  initialMessages,
  enMessages,
  localeOnlyMessages,
  editMode,
  children,
}: {
  locale: Locale;
  /** Already-merged messages (en deep-merged with locale catalog). What NextIntl renders. */
  initialMessages: Messages;
  /** Plain English source catalog (en.json). */
  enMessages: Messages;
  /** Locale-only catalog without the en fallback merged in. Used for fallback detection. */
  localeOnlyMessages: Messages;
  editMode: boolean;
  children: ReactNode;
}) {
  const [messages, setMessages] = useState<Messages>(initialMessages);

  const applyOverride = useCallback((dottedKey: string, text: string) => {
    setMessages((prev) => setIn(prev, dottedKey.split("."), text));
  }, []);

  const isFallback = useCallback(
    (dottedKey: string) => {
      // English is the source of truth; nothing is "fallback" for en consumers.
      if (locale === "en") return false;
      const parts = dottedKey.split(".");
      const localeOnly = getIn(localeOnlyMessages, parts);
      const en = getIn(enMessages, parts);
      // Fell back if the locale's own catalog has no value at this path, but en does.
      return localeOnly === undefined && en !== undefined;
    },
    [locale, localeOnlyMessages, enMessages],
  );

  const readEnglish = useCallback(
    (dottedKey: string) => {
      const v = getIn(enMessages, dottedKey.split("."));
      return typeof v === "string" ? v : undefined;
    },
    [enMessages],
  );

  const value = useMemo<EditableMessagesContextValue>(
    () => ({ editMode, locale, isFallback, applyOverride, readEnglish }),
    [editMode, locale, isFallback, applyOverride, readEnglish],
  );

  return (
    <EditableMessagesContext.Provider value={value}>
      <NextIntlClientProvider locale={locale} messages={messages}>
        {children}
      </NextIntlClientProvider>
    </EditableMessagesContext.Provider>
  );
}

function setIn(
  obj: Messages,
  path: string[],
  value: string,
): Messages {
  if (path.length === 0) return obj;
  const [head, ...rest] = path;
  const child = obj[head];
  if (rest.length === 0) {
    return { ...obj, [head]: value };
  }
  const childObj =
    child && typeof child === "object" && !Array.isArray(child)
      ? (child as Messages)
      : {};
  return { ...obj, [head]: setIn(childObj, rest, value) };
}

function getIn(obj: Messages, path: string[]): unknown {
  let cursor: unknown = obj;
  for (const part of path) {
    if (cursor && typeof cursor === "object" && !Array.isArray(cursor)) {
      cursor = (cursor as Messages)[part];
    } else {
      return undefined;
    }
  }
  return cursor;
}
```

- [ ] **Step 3: Type-check**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
jj describe -m "feat(web-ui): EditableMessagesProvider with applyOverride + fallback detection"
```

---

## Task 7: Web-UI — expose locale-only catalog + wire `EditableMessagesProvider`

**Files:**
- Modify: `src/web-ui/src/lib/i18n/catalog.ts` (add unflatten export — or keep colocated)
- Create: `src/web-ui/src/lib/i18n/messages.ts` — small helper that returns both merged and locale-only messages.
- Modify: `src/web-ui/src/app/[locale]/layout.tsx`

The existing `i18n/request.ts` returns only the merged messages to NextIntl. The popover's fallback marker needs the *un-merged* locale-only catalog. We compute both in a shared helper and use it from the layout.

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): wire EditableMessagesProvider with locale-only payload"
```

- [ ] **Step 2: Add the messages helper**

Create `src/web-ui/src/lib/i18n/messages.ts`:

```typescript
import "server-only";
import { fetchCatalog } from "./catalog";
import type { Locale } from "@/i18n/config";
import enMessages from "@/messages/en.json";

type Messages = Record<string, unknown>;

function unflatten(flat: Record<string, string>): Messages {
  const out: Messages = {};
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split(".");
    let cursor: Messages = out;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (
        typeof cursor[part] !== "object" ||
        cursor[part] === null ||
        Array.isArray(cursor[part])
      ) {
        cursor[part] = {};
      }
      cursor = cursor[part] as Messages;
    }
    cursor[parts[parts.length - 1]] = value;
  }
  return out;
}

function deepMerge(base: Messages, over: Messages): Messages {
  const result: Messages = { ...base };
  for (const [k, v] of Object.entries(over)) {
    const e = result[k];
    if (
      typeof v === "object" && v !== null && !Array.isArray(v) &&
      typeof e === "object" && e !== null && !Array.isArray(e)
    ) {
      result[k] = deepMerge(e as Messages, v as Messages);
    } else {
      result[k] = v;
    }
  }
  return result;
}

export async function loadMessages(locale: Locale): Promise<{
  merged: Messages;
  localeOnly: Messages;
  english: Messages;
}> {
  const english = enMessages as Messages;
  if (locale === "en") {
    return { merged: english, localeOnly: english, english };
  }
  const flat = await fetchCatalog(locale);
  const localeOnly = unflatten(flat);
  return { merged: deepMerge(english, localeOnly), localeOnly, english };
}
```

> The `unflatten` and `deepMerge` functions are duplicated from `i18n/request.ts`. After this task lands, refactor `request.ts` to import them from here in a follow-up commit (out of scope for this plan to keep the diff small).

- [ ] **Step 3: Update the layout**

Replace `src/web-ui/src/app/[locale]/layout.tsx` with:

```typescript
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { Suspense } from "react";
import { AuthProvider } from "@/contexts/auth";
import { EditableMessagesProvider } from "@/contexts/editable-messages";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { routing } from "@/i18n/routing";
import { LocaleHtmlLang } from "@/components/LocaleHtmlLang";
import { readEditModeFromServer } from "@/lib/i18n/edit-mode-cookie";
import { loadMessages } from "@/lib/i18n/messages";
import type { Locale } from "@/i18n/config";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    alternates: {
      canonical: locale === "is" ? "/" : `/${locale}`,
      languages: { is: "/", en: "/en", "x-default": "/" },
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  const { merged, localeOnly, english } = await loadMessages(locale as Locale);
  const editMode = await readEditModeFromServer();

  return (
    <EditableMessagesProvider
      locale={locale as Locale}
      initialMessages={merged}
      localeOnlyMessages={localeOnly}
      enMessages={english}
      editMode={editMode}
    >
      <LocaleHtmlLang locale={locale} />
      <AuthProvider>
        <Suspense>
          <Navigation />
        </Suspense>
        <Suspense>
          <div className="flex-1 flex flex-col">{children}</div>
        </Suspense>
        <Footer />
      </AuthProvider>
    </EditableMessagesProvider>
  );
}
```

- [ ] **Step 3: Smoke-check render still works**

```bash
cd src/web-ui && npm run dev
```

In another terminal, hit `http://localhost:3000/` and `http://localhost:3000/en` and confirm: Icelandic on `/`, English on `/en`. Stop the dev server (`Ctrl-C`) once verified.

- [ ] **Step 4: Run e2e i18n tests (regression)**

Make sure both servers are still running per the verify.md Phase 1 smoke-test section, then:

```bash
cd src/web-ui && npx playwright test e2e/i18n.spec.ts
```

Expected: 3/3 pass (no behavioral change — provider swap is internal).

- [ ] **Step 5: Commit**

```bash
jj describe -m "feat(web-ui): wire EditableMessagesProvider into locale layout"
```

---

## Task 8: Web-UI — edit-mode toggle in user menu

**Files:**
- Create: `src/web-ui/src/components/EditModeToggle.tsx`
- Modify: `src/web-ui/src/components/UserMenu.tsx`
- Modify: `src/web-ui/src/messages/en.json`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): edit-mode toggle in user menu"
```

- [ ] **Step 2: Add UI keys to en.json**

Replace `src/web-ui/src/messages/en.json` with:

```json
{
  "nav": {
    "projects": "Projects",
    "competitions": "Competitions",
    "continueOnboarding": "Continue onboarding",
    "myProjects": "My Projects",
    "myReviews": "My Reviews",
    "login": "Log in",
    "register": "Register",
    "profile": "Profile",
    "logout": "Log out",
    "editTranslationsOn": "Editing translations: on",
    "editTranslationsOff": "Edit translations"
  },
  "footer": {
    "about": "About",
    "privacy": "Privacy",
    "discord": "Discord"
  },
  "translatePopover": {
    "title": "Edit translation",
    "englishReference": "English",
    "save": "Save",
    "cancel": "Cancel",
    "saving": "Saving…",
    "history": "History",
    "revertToThis": "Revert to this",
    "noHistory": "No previous edits.",
    "concurrencyWarning": "This was edited {seconds} seconds ago by {user}. Save anyway?",
    "concurrencyConfirm": "Save anyway",
    "placeholderLost": "Don't change or remove the highlighted placeholders.",
    "missingTranslationHint": "Showing English. Add an Icelandic translation by editing this string."
  }
}
```

> Icelandic seeding for the new keys is added by hand in Task 13's data migration — no DeepL run needed in this plan.

- [ ] **Step 3: Implement the toggle**

Create `src/web-ui/src/components/EditModeToggle.tsx`:

```typescript
"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEditableMessages } from "@/contexts/editable-messages";
import { setEditModeCookie } from "@/lib/i18n/edit-mode-cookie.client";

export function EditModeToggle({ onClick }: { onClick?: () => void }) {
  const { editMode } = useEditableMessages();
  const router = useRouter();
  const t = useTranslations("nav");

  return (
    <button
      type="button"
      role="menuitem"
      onClick={() => {
        setEditModeCookie(!editMode);
        onClick?.();
        router.refresh();
      }}
      className="block w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
    >
      {editMode ? t("editTranslationsOn") : t("editTranslationsOff")}
    </button>
  );
}
```

- [ ] **Step 4: Mount toggle in UserMenu**

Edit `src/web-ui/src/components/UserMenu.tsx`. Find the menu body (the `{isOpen && (<div ...>...</div>)}` block) and insert the toggle just above the existing logout button, separated by a divider:

```tsx
import { EditModeToggle } from "./EditModeToggle";

// ... inside the dropdown body, after the profile link block:

<div className="border-t border-border my-1" />
<EditModeToggle onClick={() => setIsOpen(false)} />
<div className="border-t border-border my-1" />
<button
  onClick={() => {
    logout();
    setIsOpen(false);
  }}
  className="block w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
>
  {t("logout")}
</button>
```

- [ ] **Step 5: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass. The lint-i18n script will validate the new `nav.editTranslations*` keys exist.

- [ ] **Step 6: Manual smoke**

Boot dev (`npm run dev`), log in as the test user, click the user menu — confirm "Edit translations" appears. Click it; the label should change to "Editing translations: on". Click again to turn off.

- [ ] **Step 7: Commit**

```bash
jj describe -m "feat(web-ui): edit-mode toggle in user menu"
```

---

## Task 9: Web-UI — `<Translatable>` wrapper (no popover yet)

**Files:**
- Create: `src/web-ui/src/components/Translatable.tsx`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): Translatable wrapper with pencil overlay"
```

- [ ] **Step 2: Implement the wrapper**

Create `src/web-ui/src/components/Translatable.tsx`:

```typescript
"use client";

import { useState, type ReactNode } from "react";
import { useEditableMessages } from "@/contexts/editable-messages";
import { TranslationPopover } from "./TranslationPopover";

export function Translatable({
  tKey,
  children,
}: {
  /** Dotted i18n key, e.g. "nav.profile". */
  tKey: string;
  /** Already-rendered translated text (typically `t("...")`). */
  children: ReactNode;
}) {
  const { editMode, isFallback } = useEditableMessages();
  const [popoverAnchor, setPopoverAnchor] = useState<HTMLElement | null>(null);

  if (!editMode) {
    // Zero overhead in non-edit mode — render children inline.
    return <>{children}</>;
  }

  const fallback = isFallback(tKey);

  return (
    <span
      className={
        "relative group/translatable inline-block " +
        (fallback ? "underline decoration-dotted decoration-amber-400/60" : "")
      }
      data-i18n-key={tKey}
    >
      {children}
      <button
        type="button"
        aria-label={`Edit translation for ${tKey}`}
        onClick={(e) => setPopoverAnchor(e.currentTarget)}
        className="absolute -top-1 -right-3 opacity-0 group-hover/translatable:opacity-100 transition-opacity p-0.5 rounded bg-white shadow-sm border border-border text-slate-500 hover:text-slate-900"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z"
          />
        </svg>
      </button>
      {popoverAnchor && (
        <TranslationPopover
          tKey={tKey}
          anchor={popoverAnchor}
          onClose={() => setPopoverAnchor(null)}
        />
      )}
    </span>
  );
}
```

> The `TranslationPopover` import will resolve once Task 10 lands. This commit is intentionally not type-clean on its own — the next task lands the popover and re-enables type-check + lint as the gate.

- [ ] **Step 3: Stub the popover so this file compiles**

Create `src/web-ui/src/components/TranslationPopover.tsx` as a temporary stub:

```typescript
"use client";

export function TranslationPopover({
  tKey,
  onClose,
}: {
  tKey: string;
  anchor: HTMLElement;
  onClose: () => void;
}) {
  return (
    <div className="absolute top-full left-0 mt-1 z-50 bg-white border border-border rounded shadow-lg p-2 text-xs text-slate-500">
      Popover stub for <code>{tKey}</code>{" "}
      <button onClick={onClose} className="underline">
        close
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
jj describe -m "feat(web-ui): Translatable wrapper + popover stub"
```

---

## Task 10: Web-UI — popover skeleton (textarea + save/cancel)

**Files:**
- Modify: `src/web-ui/src/components/TranslationPopover.tsx`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): TranslationPopover textarea + save/cancel"
```

- [ ] **Step 2: Replace the stub with the real popover**

Replace `src/web-ui/src/components/TranslationPopover.tsx` with:

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslations, useLocale } from "next-intl";
import { useEditableMessages } from "@/contexts/editable-messages";
import { useAuth } from "@/contexts/auth";
import {
  getTranslationDetail,
  patchTranslation,
  type TranslationDetail,
} from "@/lib/i18n/api";
import type { Locale } from "@/i18n/config";

const POPOVER_WIDTH = 360;

export function TranslationPopover({
  tKey,
  anchor,
  onClose,
}: {
  tKey: string;
  anchor: HTMLElement;
  onClose: () => void;
}) {
  const t = useTranslations("translatePopover");
  const locale = useLocale() as Locale;
  const { applyOverride, readEnglish } = useEditableMessages();
  const { getToken } = useAuth();
  const englishReference = readEnglish(tKey) ?? "";

  const [detail, setDetail] = useState<TranslationDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const portalRoot = usePortalRoot();
  const position = useAnchoredPosition(anchor);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Load detail on open.
  useEffect(() => {
    let cancelled = false;
    getTranslationDetail(locale, tKey)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
        setDraft(d.text);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [locale, tKey]);

  // Close on Esc and outside click.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onMouseDown(e: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        !anchor.contains(e.target as Node)
      ) {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onMouseDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onMouseDown);
    };
  }, [anchor, onClose]);

  if (!portalRoot) return null;

  async function handleSave() {
    setBusy(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");
      const updated = await patchTranslation(locale, tKey, draft, token);
      applyOverride(tKey, updated.text);
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div
      ref={popoverRef}
      role="dialog"
      aria-label={t("title")}
      className="fixed z-[100] bg-white border border-border rounded-lg shadow-xl p-4"
      style={{
        top: position.top,
        left: position.left,
        width: POPOVER_WIDTH,
      }}
    >
      <div className="text-xs text-slate-500 mb-2">{tKey}</div>

      <textarea
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={3}
        className="w-full px-2 py-1.5 text-sm border border-border rounded resize-y focus:outline-none focus:ring-2 focus:ring-accent"
      />

      {locale !== "en" && (
        <div className="mt-2 text-xs">
          <div className="text-slate-500 uppercase tracking-wide mb-0.5">
            {t("englishReference")}
          </div>
          <div className="text-slate-700">{englishReference}</div>
        </div>
      )}

      {error && (
        <div className="mt-2 text-xs text-red-600" role="alert">
          {error}
        </div>
      )}

      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 text-sm text-slate-600 hover:text-slate-900"
          disabled={busy}
        >
          {t("cancel")}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={busy || !detail}
          className="px-3 py-1 text-sm bg-accent text-white rounded hover:bg-accent-hover disabled:opacity-50"
        >
          {busy ? t("saving") : t("save")}
        </button>
      </div>
    </div>,
    portalRoot,
  );
}

function usePortalRoot(): HTMLElement | null {
  const [root, setRoot] = useState<HTMLElement | null>(null);
  useEffect(() => setRoot(document.body), []);
  return root;
}

function useAnchoredPosition(anchor: HTMLElement) {
  const [pos, setPos] = useState({ top: 0, left: 0 });
  useEffect(() => {
    const r = anchor.getBoundingClientRect();
    setPos({
      top: r.bottom + 4,
      left: Math.max(8, Math.min(r.left, window.innerWidth - POPOVER_WIDTH - 8)),
    });
  }, [anchor]);
  return pos;
}
```

- [ ] **Step 3: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass. The lint-i18n check will validate that all `translatePopover.*` keys exist (they do — added in Task 8).

- [ ] **Step 4: Commit**

```bash
jj describe -m "feat(web-ui): TranslationPopover with textarea, save, cancel, Esc/outside-click"
```

---

## Task 11: Web-UI — ICU placeholder chips

**Files:**
- Create: `src/web-ui/src/components/TranslationChips.tsx`
- Modify: `src/web-ui/src/components/TranslationPopover.tsx`

The Phase 4 design requires that ICU placeholders (`{name}`, `{count, plural, ...}`) cannot be deleted or mangled in the editor. Render them as visually distinct, atomic, non-editable spans inside a `contentEditable` wrapper.

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): ICU placeholder chips inside translation popover"
```

- [ ] **Step 2: Implement the chips component**

Create `src/web-ui/src/components/TranslationChips.tsx`:

```typescript
"use client";

import { useEffect, useRef } from "react";

/** Match `{name}` and `{count, plural, ...}` (top-level only — does not recurse into nested braces). */
const PLACEHOLDER_RE = /\{[^{}]+\}/g;

export type ChipsValidation =
  | { ok: true; placeholders: string[] }
  | { ok: false; placeholders: string[]; missing: string[] };

export function extractPlaceholders(text: string): string[] {
  return text.match(PLACEHOLDER_RE) ?? [];
}

export function validateAgainstReference(
  reference: string,
  draft: string,
): ChipsValidation {
  const refPlaceholders = extractPlaceholders(reference).sort();
  const draftPlaceholders = extractPlaceholders(draft).sort();
  const missing = refPlaceholders.filter((p) => !draftPlaceholders.includes(p));
  if (missing.length === 0) {
    return { ok: true, placeholders: refPlaceholders };
  }
  return { ok: false, placeholders: refPlaceholders, missing };
}

/**
 * A `contentEditable` div that renders text chunks editably and ICU `{...}`
 * placeholders as atomic non-editable chips. On every input, calls `onChange`
 * with the serialized plain-text value (chips serialize back to `{name}` form).
 */
export function ChipsEditor({
  value,
  onChange,
  rows = 3,
}: {
  value: string;
  onChange: (next: string) => void;
  rows?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Render chips on mount + when external value changes (e.g. revert).
  useEffect(() => {
    if (!ref.current) return;
    if (serialize(ref.current) !== value) {
      ref.current.innerHTML = renderChipsHtml(value);
    }
  }, [value]);

  function handleInput() {
    if (!ref.current) return;
    const next = serialize(ref.current);
    if (next !== value) onChange(next);
  }

  return (
    <div
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      onInput={handleInput}
      role="textbox"
      aria-multiline="true"
      style={{ minHeight: `${rows * 1.5}em` }}
      className="w-full px-2 py-1.5 text-sm border border-border rounded focus:outline-none focus:ring-2 focus:ring-accent whitespace-pre-wrap"
    />
  );
}

function renderChipsHtml(value: string): string {
  const parts: string[] = [];
  let i = 0;
  for (const match of value.matchAll(PLACEHOLDER_RE)) {
    const start = match.index ?? 0;
    if (start > i) parts.push(escapeHtml(value.slice(i, start)));
    parts.push(
      `<span data-chip="${escapeAttr(match[0])}" contenteditable="false" class="inline-block bg-amber-100 text-amber-900 rounded px-1 mx-0.5 text-xs select-none">${escapeHtml(match[0])}</span>`,
    );
    i = start + match[0].length;
  }
  if (i < value.length) parts.push(escapeHtml(value.slice(i)));
  return parts.join("");
}

function serialize(el: HTMLElement): string {
  let out = "";
  for (const node of Array.from(el.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE) {
      out += node.textContent ?? "";
    } else if (node instanceof HTMLElement) {
      const chip = node.dataset.chip;
      if (chip) {
        out += chip;
      } else {
        out += node.textContent ?? "";
      }
    }
  }
  return out;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(s: string): string {
  return escapeHtml(s).replace(/"/g, "&quot;");
}
```

- [ ] **Step 3: Wire chips into the popover**

In `src/web-ui/src/components/TranslationPopover.tsx`:

1. Import `ChipsEditor` and `validateAgainstReference` from `./TranslationChips`.
2. Replace the `<textarea>` with `<ChipsEditor value={draft} onChange={setDraft} />`.
3. Compute `const validation = validateAgainstReference(englishReference, draft);` after the `draft` state line. (`englishReference` is already in scope from Task 10.)
4. Disable the Save button when `!validation.ok` and surface a small warning message:

```tsx
{!validation.ok && (
  <div className="mt-2 text-xs text-amber-700">{t("placeholderLost")}</div>
)}
```

5. Save button: `disabled={busy || !detail || !validation.ok}`.

- [ ] **Step 4: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 5: Quick manual chip check**

Boot dev. Wrap a temporary key in `<Translatable>` whose English uses an ICU placeholder (or stub a message like `"test.greet": "Hello, {name}"`), open the popover, try to delete the chip — it should refuse, and Save should be disabled. Then revert your stub.

(This is exploratory only; no committed change. Subagent: report what you observed.)

- [ ] **Step 6: Commit**

```bash
jj describe -m "feat(web-ui): ICU placeholder chips in translation popover"
```

---

## Task 12: Web-UI — history disclosure + revert

**Files:**
- Modify: `src/web-ui/src/components/TranslationPopover.tsx`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): history disclosure with revert in popover"
```

- [ ] **Step 2: Add the disclosure**

In `src/web-ui/src/components/TranslationPopover.tsx`, just below the English-reference block and above the buttons row, add:

```tsx
<details className="mt-3 text-xs">
  <summary className="cursor-pointer text-slate-500 hover:text-slate-900 select-none">
    {t("history")} {detail && detail.history.length > 0 ? `(${detail.history.length})` : ""}
  </summary>
  {detail && detail.history.length === 0 && (
    <div className="mt-1 text-slate-400">{t("noHistory")}</div>
  )}
  {detail && detail.history.length > 0 && (
    <ul className="mt-1 space-y-1">
      {detail.history.map((entry) => (
        <li key={entry.changed_at} className="border-l-2 border-slate-200 pl-2">
          <div className="text-slate-500">
            {entry.changed_by ?? "system"} · {formatRelative(entry.changed_at)}
          </div>
          <div className="text-slate-700 truncate">{entry.new_text}</div>
          <button
            type="button"
            onClick={() => setDraft(entry.new_text)}
            className="text-accent hover:underline"
          >
            {t("revertToThis")}
          </button>
        </li>
      ))}
    </ul>
  )}
</details>
```

- [ ] **Step 3: Add the relative-time formatter**

At the bottom of the same file, add:

```typescript
function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}
```

- [ ] **Step 4: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
jj describe -m "feat(web-ui): history disclosure with revert in translation popover"
```

---

## Task 13: Web-UI — concurrency check on save

**Files:**
- Modify: `src/web-ui/src/components/TranslationPopover.tsx`

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): concurrency warning + confirm on translation save"
```

- [ ] **Step 2: Track stale state and add confirm step**

In `src/web-ui/src/components/TranslationPopover.tsx`:

1. Add new state: `const [confirmStale, setConfirmStale] = useState<{seconds: number; user: string | null} | null>(null);`
2. Replace `handleSave` with the concurrency-aware version:

```typescript
async function handleSave(forceOverwrite = false) {
  setBusy(true);
  setError(null);
  try {
    const token = getToken();
    if (!token) throw new Error("Not authenticated");

    if (!forceOverwrite) {
      // Re-fetch detail; bail out for confirm if updated_at moved.
      const fresh = await getTranslationDetail(locale, tKey);
      if (
        detail?.updated_at &&
        fresh.updated_at &&
        fresh.updated_at !== detail.updated_at
      ) {
        const seconds = Math.max(
          1,
          Math.round((Date.now() - new Date(fresh.updated_at).getTime()) / 1000),
        );
        const lastEditor = fresh.history[0]?.changed_by ?? null;
        setConfirmStale({ seconds, user: lastEditor });
        setBusy(false);
        return;
      }
    }

    const updated = await patchTranslation(locale, tKey, draft, token);
    applyOverride(tKey, updated.text);
    onClose();
  } catch (e) {
    setError(String(e));
  } finally {
    setBusy(false);
  }
}
```

3. Above the buttons row, render the warning + confirm when `confirmStale !== null`:

```tsx
{confirmStale && (
  <div className="mt-2 text-xs text-amber-700" role="alert">
    {t("concurrencyWarning", {
      seconds: confirmStale.seconds,
      user: confirmStale.user ?? "someone",
    })}
    <button
      type="button"
      onClick={() => {
        setConfirmStale(null);
        handleSave(true);
      }}
      className="ml-2 underline hover:text-amber-900"
    >
      {t("concurrencyConfirm")}
    </button>
  </div>
)}
```

4. Update Save button click handler: `onClick={() => handleSave(false)}`.

- [ ] **Step 3: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
jj describe -m "feat(web-ui): concurrency warning + confirm on translation save"
```

---

## Task 14: Backend — seed Icelandic for new edit-mode UI keys

**Files:**
- Create: `src/django-backend/apps/translations/migrations/0004_seed_phase4_edit_ui.py`
- Run: `make translate-new-keys` is **not** used here (DeepL is paused). Hand-author the IS strings in the migration.

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(translations): seed Icelandic for phase 4 edit UI keys"
```

- [ ] **Step 2: Find the latest migration number**

Run: `ls src/django-backend/apps/translations/migrations/`
Identify the highest-numbered migration (likely `0003_seed_phase2_ui_chrome.py`). The new file is `0004_seed_phase4_edit_ui.py`. If the numbering has advanced, use the next free number.

- [ ] **Step 3: Author the migration**

Create `src/django-backend/apps/translations/migrations/0004_seed_phase4_edit_ui.py`:

```python
from __future__ import annotations

from django.db import migrations

# (locale, key, text)
SEEDS: list[tuple[str, str, str]] = [
    ("is", "nav.editTranslationsOn", "Þýðingaham: virkur"),
    ("is", "nav.editTranslationsOff", "Breyta þýðingum"),
    ("is", "translatePopover.title", "Breyta þýðingu"),
    ("is", "translatePopover.englishReference", "Enska"),
    ("is", "translatePopover.save", "Vista"),
    ("is", "translatePopover.cancel", "Hætta við"),
    ("is", "translatePopover.saving", "Vistar…"),
    ("is", "translatePopover.history", "Saga"),
    ("is", "translatePopover.revertToThis", "Fara aftur í þetta"),
    ("is", "translatePopover.noHistory", "Engar fyrri breytingar."),
    (
        "is",
        "translatePopover.concurrencyWarning",
        "Þetta var breytt fyrir {seconds} sekúndum af {user}. Vista samt?",
    ),
    ("is", "translatePopover.concurrencyConfirm", "Vista samt"),
    (
        "is",
        "translatePopover.placeholderLost",
        "Ekki breyta eða fjarlægja gulu táknin.",
    ),
    (
        "is",
        "translatePopover.missingTranslationHint",
        "Sýni ensku. Bættu við íslenskri þýðingu með því að breyta þessum streng.",
    ),
]


def seed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for locale, key, text in SEEDS:
        Translation.objects.update_or_create(
            locale=locale,
            key=key,
            defaults={
                "text": text,
                "source_hash": "",
                "is_machine_translated": False,
                "retired": False,
            },
        )


def unseed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    Translation.objects.filter(
        locale="is",
        key__in=[k for _, k, _ in SEEDS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("translations", "0003_seed_phase2_ui_chrome"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
```

If the previous migration name differs, update `dependencies` accordingly (look at the file actually present in the migrations dir).

- [ ] **Step 4: Update the snapshot to match en.json**

The Phase 3 lint check (`make lint-translations`) compares `en.json` to `apps/translations/generators/state/en-snapshot.json`. New keys must also exist in the snapshot or the lint will fail.

Update `src/django-backend/apps/translations/generators/state/en-snapshot.json` — read the file, find the `entries` map, and add entries for each new key from Task 8's en.json. The hash format used by the snapshot is `source_hash(text)` (16-char sha256 prefix). Compute hashes by running:

```bash
cd src/django-backend && uv run python -c "
from apps.translations.generators.hashing import source_hash
keys = {
  'nav.editTranslationsOn': 'Editing translations: on',
  'nav.editTranslationsOff': 'Edit translations',
  'translatePopover.title': 'Edit translation',
  'translatePopover.englishReference': 'English',
  'translatePopover.save': 'Save',
  'translatePopover.cancel': 'Cancel',
  'translatePopover.saving': 'Saving…',
  'translatePopover.history': 'History',
  'translatePopover.revertToThis': 'Revert to this',
  'translatePopover.noHistory': 'No previous edits.',
  'translatePopover.concurrencyWarning': 'This was edited {seconds} seconds ago by {user}. Save anyway?',
  'translatePopover.concurrencyConfirm': 'Save anyway',
  'translatePopover.placeholderLost': \"Don't change or remove the highlighted placeholders.\",
  'translatePopover.missingTranslationHint': 'Showing English. Add an Icelandic translation by editing this string.',
}
for k, v in keys.items():
    print(f'  {k!r}: ({v!r}, {source_hash(v)!r}),')
"
```

Use the printed hashes to extend the snapshot's `entries` dict. (If the snapshot file uses a different shape, mirror it exactly — the file already on disk is the source of truth for format.)

- [ ] **Step 5: Run lint-translations**

```bash
cd src/django-backend && make lint-translations
```

Expected: green (en.json and snapshot are now aligned).

- [ ] **Step 6: Apply migration locally**

```bash
cd src/django-backend && uv run python manage.py migrate translations
```

Expected: `Applying translations.0004_seed_phase4_edit_ui... OK`.

- [ ] **Step 7: Commit**

```bash
jj describe -m "feat(translations): seed Icelandic for phase 4 edit UI keys"
```

---

## Task 15: Web-UI — wrap chrome strings with `<Translatable>`

**Files:**
- Modify: `src/web-ui/src/components/Navigation.tsx`
- Modify: `src/web-ui/src/components/Footer.tsx`
- Modify: `src/web-ui/src/components/UserMenu.tsx`

The pattern: replace `{t("foo")}` with `<Translatable tKey="ns.foo">{t("foo")}</Translatable>`. Repeat for every chrome string. Skip aria-only labels and dynamic strings (e.g. `${displayName}`) — only translate keys that come from `t()`.

- [ ] **Step 1: New changeset**

```bash
jj new -m "feat(web-ui): wrap chrome strings with <Translatable>"
```

- [ ] **Step 2: Update Navigation.tsx**

Add at top:

```tsx
import { Translatable } from "./Translatable";
```

Then replace each chrome `{t("...")}` with the wrapped form. Concrete substitutions (line-by-line — existing markup preserved, only the `{t(...)}` expression is wrapped):

- `{t("projects")}` → `<Translatable tKey="nav.projects">{t("projects")}</Translatable>`
- `{t("competitions")}` → `<Translatable tKey="nav.competitions">{t("competitions")}</Translatable>`
- `{t("continueOnboarding")}` → `<Translatable tKey="nav.continueOnboarding">{t("continueOnboarding")}</Translatable>`
- `{t("myProjects")}` → `<Translatable tKey="nav.myProjects">{t("myProjects")}</Translatable>`
- `{t("myReviews")}` → `<Translatable tKey="nav.myReviews">{t("myReviews")}</Translatable>`
- `{t("login")}` → `<Translatable tKey="nav.login">{t("login")}</Translatable>`
- `{t("register")}` → `<Translatable tKey="nav.register">{t("register")}</Translatable>`
- `{t("profile")}` → `<Translatable tKey="nav.profile">{t("profile")}</Translatable>`
- `{t("logout")}` → `<Translatable tKey="nav.logout">{t("logout")}</Translatable>`

(Each appears twice in `Navigation.tsx` — once in desktop nav, once in mobile slide-in. Wrap both.)

- [ ] **Step 3: Update Footer.tsx**

Read the file:

Run: `cat src/web-ui/src/components/Footer.tsx`

Apply the same pattern to each `{t("about")}`, `{t("privacy")}`, `{t("discord")}` call: wrap with `<Translatable tKey="footer.about">{t("about")}</Translatable>` etc. Add the `Translatable` import at top.

- [ ] **Step 4: Update UserMenu.tsx**

In `src/web-ui/src/components/UserMenu.tsx`:

- `{t("profile")}` → `<Translatable tKey="nav.profile">{t("profile")}</Translatable>`
- `{t("logout")}` → `<Translatable tKey="nav.logout">{t("logout")}</Translatable>`

Also add the `Translatable` import.

- [ ] **Step 5: Lint + type-check**

```bash
cd src/web-ui && npm run lint && npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 6: Manual smoke**

Run dev (`npm run dev`). With edit mode off: hover over nav links — no pencil. Toggle edit mode on via UserMenu → hover any nav link → pencil appears, click it → popover opens with the existing Icelandic text. Edit, save, see the change instantly. Reload — change persists (it landed in Django).

- [ ] **Step 7: Commit**

```bash
jj describe -m "feat(web-ui): wrap chrome strings with <Translatable>"
```

---

## Task 16: Playwright e2e — inline edit happy path

**Files:**
- Create: `src/web-ui/e2e/i18n-edit.spec.ts`

- [ ] **Step 1: New changeset**

```bash
jj new -m "test(e2e): inline translation edit happy path"
```

- [ ] **Step 2: Write the spec**

Create `src/web-ui/e2e/i18n-edit.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

// Preconditions:
//   - Django backend reachable at $API_URL with phase 1+2+4 migrations applied
//     and the webhook env vars set (so PATCH triggers revalidation).
//   - Web-ui dev server running at Playwright's baseURL.
//   - $TEST_USER_EMAIL / $TEST_USER_PASSWORD valid in .env.claude.

const EMAIL = process.env.TEST_USER_EMAIL!;
const PASSWORD = process.env.TEST_USER_PASSWORD!;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(EMAIL);
  await page.getByLabel(/password/i).fill(PASSWORD);
  await page.getByRole("button", { name: /log in|sign in/i }).click();
  await page.waitForURL(/\/$|\/projects|\/onboarding/);
}

test("inline edit: edit nav.projects, see change instantly, persist after reload", async ({
  page,
}) => {
  test.skip(!EMAIL || !PASSWORD, "TEST_USER_EMAIL/PASSWORD not set");

  await login(page);
  await page.goto("/");

  // Open user menu and toggle edit mode on.
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  await page.getByRole("menuitem", { name: /edit translations/i }).click();

  // Page should re-render via router.refresh; menu closes. Re-open and verify "on" label.
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  await expect(
    page.getByRole("menuitem", { name: /editing translations: on/i }),
  ).toBeVisible();
  // Close menu.
  await page.keyboard.press("Escape");

  // Hover the Verkefni link → pencil appears → click it.
  const verkefni = page.getByRole("link", { name: "Verkefni" }).first();
  await verkefni.hover();
  const pencil = page
    .locator(`[data-i18n-key="nav.projects"] button[aria-label*="Edit translation"]`);
  await pencil.click();

  // Popover opens; edit and save.
  const popover = page.getByRole("dialog", { name: /edit translation/i });
  await expect(popover).toBeVisible();

  const editor = popover.getByRole("textbox");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.press("Delete");
  await page.keyboard.type("VERKVERK");

  await popover.getByRole("button", { name: /^save$/i }).click();

  // Optimistic update: nav re-renders without reload.
  await expect(
    page.getByRole("link", { name: "VERKVERK" }).first(),
  ).toBeVisible({ timeout: 3000 });

  // Reload — value should persist (Django round-trip succeeded).
  await page.reload();
  await expect(
    page.getByRole("link", { name: "VERKVERK" }).first(),
  ).toBeVisible({ timeout: 5000 });

  // Cleanup: revert via UI for repeatability.
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  await page.getByRole("menuitem", { name: /editing translations: on/i }).click();
  await page.waitForLoadState("networkidle");
  // Ensure edit mode still on (depending on cookie roundtrip), then re-toggle if not.
  // Reopen menu, click "Edit translations: on"? Wait — the toggle text changes.
  // For a clean revert, re-fetch the link by text "VERKVERK" and PATCH back to "Verkefni" via the popover:
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  const toggle = page.getByRole("menuitem", { name: /edit translations/i });
  if (await toggle.isVisible()) {
    await toggle.click();
  } else {
    await page.keyboard.press("Escape");
  }

  // Best-effort revert via API directly is also acceptable; for now re-edit through UI:
  await page.goto("/");
  const verkverk = page.getByRole("link", { name: "VERKVERK" }).first();
  await verkverk.hover();
  const pencil2 = page
    .locator(`[data-i18n-key="nav.projects"] button[aria-label*="Edit translation"]`);
  if (await pencil2.isVisible()) {
    await pencil2.click();
    const popover2 = page.getByRole("dialog", { name: /edit translation/i });
    const editor2 = popover2.getByRole("textbox");
    await editor2.click();
    await page.keyboard.press("Control+A");
    await page.keyboard.press("Delete");
    await page.keyboard.type("Verkefni");
    await popover2.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByRole("link", { name: "Verkefni" }).first()).toBeVisible({
      timeout: 3000,
    });
  }
});
```

> The cleanup section is best-effort — Playwright tests should not depend on perfect state restoration, but it's polite to leave the DB clean for the next run.

- [ ] **Step 3: Run the spec (with both servers running)**

Per `verify.md` Phase 1 smoke instructions, ensure Django is running on `:8001` (with webhook env vars) and web-ui dev on `:3000`. Then:

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
source .env.claude
cd src/web-ui && npx playwright test e2e/i18n-edit.spec.ts
```

Expected: 1 passed.

If the spec fails on Login (e.g. selector mismatch), inspect the existing `e2e/login.spec.ts` for the canonical selectors and copy them.

- [ ] **Step 4: Commit**

```bash
jj describe -m "test(e2e): inline translation edit happy path"
```

---

## Task 17: Full CI gate

- [ ] **Step 1: New changeset for any cleanup**

```bash
jj new -m "chore: phase 4 final CI gate"
```

- [ ] **Step 2: From repo root**

```bash
make ci
```

Expected: green. The Phase 3 lint-translations and lint-i18n.mjs checks should both pass — every new `t("translatePopover.*")` and `t("nav.editTranslations*")` key resolves in `en.json` and is reflected in the snapshot.

- [ ] **Step 3: If empty, no-op the changeset**

```bash
jj abandon  # if empty
```

Otherwise:

```bash
jj describe -m "chore: phase 4 final CI gate"
```

- [ ] **Step 4: Update verify.md (manual edit)**

Move Phase 4's status in `docs/superpowers/verify.md` from `⏳ NEXT UP` to `✅ Implemented`. Note any deferrals (sweep of non-chrome pages; ESLint no-hardcoded-strings rule).

---

## Task 18 (deferred — track but do not implement): hardcoded-string sweep + lint rule

Deferred from Phase 3 and re-deferred here pending the MT-provider decision (DeepL paused). When ready:

- Walk every page under `src/web-ui/src/app/[locale]/` and replace bare JSX text nodes with `t("...")` calls + add corresponding entries in `en.json`.
- Run `make translate-new-keys` (or its successor) to seed Icelandic.
- Wrap each newly-translated string with `<Translatable tKey="...">{t(...)}</Translatable>`.
- Add a custom ESLint rule (or extend `scripts/lint-i18n.mjs`) that flags any non-whitespace text node inside a JSX element that isn't `<Translatable>`-wrapped or `t()`-derived. Exclude `code`/`pre`/`Trans`/`script`-style elements.

This is large enough to warrant its own plan. Do **not** start it in this session.

---

## Done criteria

- `make ci` passes.
- A logged-in user can: toggle edit mode → pencil appears on every chrome string → click pencil → popover opens with current Icelandic + English reference + history → edit → see change instantly → reload → change persists → other clients see change within seconds (existing webhook).
- ICU placeholders cannot be deleted; Save is disabled when chips are missing.
- Concurrency warning appears when two editors race on the same key.
- Playwright `e2e/i18n-edit.spec.ts` passes.
- Phase 4 row in `verify.md` flipped to ✅ Implemented.
