# Article Hero Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make hero image removal work, add an optional article summary with a derived fallback, and rebuild the project Articles tab as a lead story plus a two-column card grid.

**Architecture:** Backend first — a pure `derive_summary` function, then the `Article.summary` field and schema wiring, then a sentinel that lets `PATCH` distinguish "omitted" from "explicitly null" so a hero can be cleared. Contract regeneration sits between backend and frontend. Frontend then builds one shared `ArticleHeroImage` (single definition of the 16:9 crop), one shared `ArticleCard`, rebuilds `ArticlesList`, and adds a card preview dialog that is also where the summary is authored.

**Tech Stack:** Django 4.2 + Django Ninja, Python 3.12, `uv`, Ruff, pytest + hamcrest. Next.js 16 App Router, React 19, TypeScript, Tailwind, vitest (no testing-library — tests mount with `createRoot` + `act`), Playwright.

**Spec:** [`docs/superpowers/specs/2026-08-05-article-hero-images-design.md`](../specs/2026-08-05-article-hero-images-design.md)

## Global Constraints

- **Version control is jj, not git.** Commit with `jj commit -m "…"`. Never run `git commit`, `git add`, or `git checkout`.
- **No "Generated with Claude Code" or "Co-Authored-By" lines** in commit messages.
- Backend commands run from `src/django-backend/`: `make test`, `make lint`, `make extract-openapi`. If pytest is missing, run `make install-deps` first.
- Frontend commands run from `src/web-ui/`: `npm test`, `npm run lint`, `npm run generate-types`.
- Any change to a Ninja schema requires `make extract-openapi` then `npm run generate-types`. Task 4 does this once for all backend schema changes; do not skip it, and do not hand-edit `src/web-ui/src/lib/api-types.ts`.
- Backend tests use hamcrest (`assert_that(x, equal_to(y))`) in `api/routers/`, and plain `assert` in `services/`. Follow whichever file you are in.
- Frontend tests must not add `@testing-library/react` — it is not a dependency. Mount with `createRoot` + `act`, copying the helpers at the top of `src/app/projects/[slug]/articles/image-insert.test.tsx`.
- User-facing product strings are Icelandic; code, comments, docs, and the editor chrome in these files are English (this editor UI is already English — match the surrounding file).

## File Structure

**Backend (`src/django-backend/`)**

| File | Responsibility |
|---|---|
| `services/articles/summary.py` (create) | `derive_summary(body, limit)` — markdown → plain excerpt |
| `services/articles/test_summary.py` (create) | Tests for the above |
| `apps/articles/models.py` (modify) | `Article.summary` field |
| `apps/articles/migrations/00XX_article_summary.py` (create, generated) | Migration |
| `services/articles/exceptions.py` (modify) | `PublishedArticleNeedsHeroImageError` |
| `services/articles/handler_interface.py` (modify) | `UnsetType`/`UNSET`, widened `update_article` signature |
| `services/articles/django_impl/handler.py` (modify) | Sentinel branch, published invariant, summary write |
| `api/schemas/article.py` (modify) | `summary` on update/out/list, `summary_display` on out |
| `api/routers/articles.py` (modify) | `exclude_unset` plumbing, 422 mapping |

**Frontend (`src/web-ui/src/`)**

| File | Responsibility |
|---|---|
| `components/ArticleHeroImage.tsx` (create) | The one 16:9 crop + placeholder |
| `components/ArticleCard.tsx` (create) | `lead` / `grid` card, no data fetching |
| `components/article-card.test.tsx` (create) | Tests for both components |
| `app/projects/[slug]/ArticlesList.tsx` (modify) | Lead + grid layout |
| `app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx` (modify) | Adopt `ArticleHeroImage` |
| `app/my-projects/[id]/MyProjectArticles.tsx` (modify) | Adopt `ArticleHeroImage` |
| `app/projects/[slug]/articles/ArticleCardPreview.tsx` (create) | Presentational preview + summary editor |
| `app/projects/[slug]/articles/ArticleCardPreviewDialog.tsx` (create) | Dialog shell + save wiring |
| `app/projects/[slug]/articles/article-card-preview.test.tsx` (create) | Tests |
| `app/projects/[slug]/articles/useArticleDraft.ts` (modify) | `summary` in form state, `saveSummary` |
| `app/projects/[slug]/articles/ArticleAuthoringPage.tsx` (modify) | Preview button, published-no-hero guard |
| `e2e/article-hero-removal.spec.ts` (create) | The regression |

---

### Task 1: `derive_summary`

A pure function, no Django. Written first so everything downstream has a real implementation to call.

**Files:**
- Create: `src/django-backend/services/articles/summary.py`
- Test: `src/django-backend/services/articles/test_summary.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `derive_summary(body: str, limit: int = 200) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `src/django-backend/services/articles/test_summary.py`:

```python
from __future__ import annotations

from services.articles.summary import derive_summary


class TestDeriveSummary:
    def test_returns_first_paragraph(self):
        body = "The opening line of the article.\n\nA second paragraph."

        assert derive_summary(body) == "The opening line of the article."

    def test_drops_leading_heading(self):
        body = "# My title\n\nThe actual opening line."

        assert derive_summary(body) == "The actual opening line."

    def test_drops_leading_image(self):
        body = "![a screenshot](https://cdn.example/x.png)\n\nThe opening line."

        assert derive_summary(body) == "The opening line."

    def test_unwraps_links_keeping_their_text(self):
        body = "See [the docs](https://example.com) for more."

        assert derive_summary(body) == "See the docs for more."

    def test_skips_a_body_that_opens_with_a_code_fence(self):
        body = "```python\nprint('hi')\n```\n\nWhat the snippet does."

        assert derive_summary(body) == "What the snippet does."

    def test_strips_list_markers_and_joins_the_lines(self):
        body = "- First point\n- Second point"

        assert derive_summary(body) == "First point Second point"

    def test_strips_emphasis_markers(self):
        body = "This is **important** and `literal`."

        assert derive_summary(body) == "This is important and literal."

    def test_leaves_underscores_inside_words_alone(self):
        body = "The hero_image_id field is the culprit."

        assert derive_summary(body) == "The hero_image_id field is the culprit."

    def test_truncates_on_a_word_boundary_with_an_ellipsis(self):
        body = "word " * 100

        assert derive_summary(body, limit=20) == "word word word word…"

    def test_empty_body_returns_empty_string(self):
        assert derive_summary("") == ""

    def test_body_with_only_a_heading_returns_empty_string(self):
        assert derive_summary("# Just a title\n") == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `src/django-backend/`:
```bash
uv run pytest services/articles/test_summary.py -v
```
Expected: collection error — `ModuleNotFoundError: No module named 'services.articles.summary'`.

- [ ] **Step 3: Write the implementation**

Create `src/django-backend/services/articles/summary.py`:

```python
"""Derive a listing summary from an article's markdown body.

Used when an article has no authored summary. Lives only here — a second
implementation in TypeScript would drift, so the frontend previews a saved
article rather than deriving client-side.
"""

from __future__ import annotations

import re

# Order matters below: fences and headings go before block splitting so a body
# that opens with either falls through to the first real paragraph, and images
# are removed before links because image syntax contains link syntax.
_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_HEADING_LINE_RE = re.compile(r"^ {0,3}#{1,6}\s.*$", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_LINE_MARKER_RE = re.compile(r"^ {0,3}(?:>\s*|[-*+]\s+|\d+[.)]\s+)")
# Underscores are left alone on purpose: stripping them mangles snake_case
# identifiers, which show up constantly in this product's articles.
_EMPHASIS_RE = re.compile(r"[*`~]")
_WHITESPACE_RE = re.compile(r"\s+")


def derive_summary(body: str, limit: int = 200) -> str:
    """Return a plain-text excerpt of ``body``, or "" if there is nothing to say."""
    text = _FENCE_RE.sub("", body)
    text = _HEADING_LINE_RE.sub("", text)
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)

    for block in text.split("\n\n"):
        lines = [_LINE_MARKER_RE.sub("", line) for line in block.splitlines()]
        candidate = _EMPHASIS_RE.sub("", " ".join(lines))
        candidate = _WHITESPACE_RE.sub(" ", candidate).strip()
        if candidate:
            return _truncate(candidate, limit)
    return ""


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return f"{cut}…"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest services/articles/test_summary.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Lint**

```bash
make lint
```
Expected: clean. If `ruff format --check` complains, run `uv run ruff format services/articles/summary.py services/articles/test_summary.py` and re-run.

- [ ] **Step 6: Commit**

```bash
jj commit -m "Add derive_summary for article listing excerpts"
```

---

### Task 2: `Article.summary` field and schema wiring

**Files:**
- Modify: `src/django-backend/apps/articles/models.py`
- Create (generated): `src/django-backend/apps/articles/migrations/00XX_article_summary.py`
- Modify: `src/django-backend/api/schemas/article.py`
- Modify: `src/django-backend/services/articles/handler_interface.py`
- Modify: `src/django-backend/services/articles/django_impl/handler.py`
- Modify: `src/django-backend/api/routers/articles.py`
- Test: `src/django-backend/services/articles/django_impl/test_handler.py`, `src/django-backend/api/routers/test_articles.py`

**Interfaces:**
- Consumes: `derive_summary(body: str, limit: int = 200) -> str` from Task 1.
- Produces: `Article.summary` (str, `""` when unset); `ArticleUpdate.summary: str | None`; `ArticleOut.summary: str` and `ArticleOut.summary_display: str`; `ArticleListItem.summary: str`; `update_article(..., summary: str | None = None)`.

- [ ] **Step 1: Write the failing tests**

Append to `src/django-backend/services/articles/django_impl/test_handler.py`:

```python
@pytest.mark.django_db
class TestArticleSummary:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_new_article_has_empty_summary(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project)

        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
        )

        assert article.summary == ""

    def test_update_sets_summary(self):
        article = ArticleFactory(body="The body opening.")

        updated = self.handler.update_article(article.id, summary="A hook.")

        assert updated.summary == "A hook."

    def test_empty_string_clears_the_summary(self):
        article = ArticleFactory(summary="A hook.")

        updated = self.handler.update_article(article.id, summary="")

        assert updated.summary == ""

    def test_omitting_summary_leaves_it_alone(self):
        article = ArticleFactory(summary="A hook.")

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.summary == "A hook."
```

Append to `src/django-backend/api/routers/test_articles.py`, inside `TestPatchArticle`:

```python
    def test_owner_can_set_and_clear_summary(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project, body="The body opening line.")

        set_response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"summary": "An authored hook."},
            auth_headers,
        )
        assert_that(set_response.status_code, equal_to(200))
        assert_that(set_response.json()["summary"], equal_to("An authored hook."))
        assert_that(
            set_response.json()["summary_display"], equal_to("An authored hook.")
        )

        clear_response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"summary": ""},
            auth_headers,
        )
        assert_that(clear_response.status_code, equal_to(200))
        assert_that(clear_response.json()["summary"], equal_to(""))
        assert_that(
            clear_response.json()["summary_display"],
            equal_to("The body opening line."),
        )
```

And a new class at the end of the same file:

```python
@pytest.mark.django_db
class TestArticleListSummary:
    def test_list_falls_back_to_derived_summary(self, client) -> None:
        project = ProjectFactory()
        ArticleFactory(
            project=project,
            state=ArticleState.PUBLISHED,
            slug="a-post",
            body="# Heading\n\nDerived from the body.",
            summary="",
        )

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()[0]["summary"], equal_to("Derived from the body."))

    def test_list_prefers_the_authored_summary(self, client) -> None:
        project = ProjectFactory()
        ArticleFactory(
            project=project,
            state=ArticleState.PUBLISHED,
            slug="b-post",
            body="Derived from the body.",
            summary="Authored.",
        )

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.json()[0]["summary"], equal_to("Authored."))
```

Check the imports already present at the top of `test_articles.py` — add `ArticleState` and `pytest` to them only if missing.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest services/articles/django_impl/test_handler.py::TestArticleSummary api/routers/test_articles.py -v
```
Expected: FAIL — `TypeError: update_article() got an unexpected keyword argument 'summary'` and `KeyError: 'summary'`.

- [ ] **Step 3: Add the model field**

In `src/django-backend/apps/articles/models.py`, on the `Article` model, next to `body`:

```python
    summary = models.CharField(max_length=300, blank=True, default="")
```

- [ ] **Step 4: Generate and inspect the migration**

```bash
uv run python manage.py makemigrations articles -n article_summary
```
Expected: creates `apps/articles/migrations/00XX_article_summary.py` with a single `AddField`. Open it and confirm it contains nothing else — if `makemigrations` swept in an unrelated model change, stop and ask before continuing.

- [ ] **Step 5: Widen the handler**

In `src/django-backend/services/articles/handler_interface.py`, add `summary: str | None = None` to the `update_article` signature, after `body`.

In `src/django-backend/services/articles/django_impl/handler.py`, add the same parameter to `update_article` and, immediately after the `body` branch:

```python
        if summary is not None and summary != article.summary:
            article.summary = summary
            update_fields.append("summary")
```

- [ ] **Step 6: Wire the schemas**

In `src/django-backend/api/schemas/article.py`, add the import:

```python
from services.articles.summary import derive_summary
```

Add to `ArticleUpdate`, after `body`:

```python
    summary: str | None = None
```

Add to `ArticleOut`, after `body`:

```python
    summary: str
    summary_display: str
```

and a resolver alongside the existing ones:

```python
    @staticmethod
    def resolve_summary_display(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)
```

Add to `ArticleListItem`, after `title`:

```python
    summary: str
```

and:

```python
    @staticmethod
    def resolve_summary(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)
```

`REPO.articles.for_project` (`services/articles/django_impl/query.py:36`) selects whole rows, so `obj.body` is already loaded and this adds no queries. Do not add `.only(...)` to that queryset without including `body`.

- [ ] **Step 7: Pass it through the router**

In `src/django-backend/api/routers/articles.py`, in `patch_article`, add to the `update_article` call:

```python
            summary=payload.summary,
```

- [ ] **Step 8: Run the tests to verify they pass**

```bash
uv run pytest services/articles/django_impl/test_handler.py api/routers/test_articles.py -v
```
Expected: all pass.

- [ ] **Step 9: Run the full backend suite and lint**

```bash
make test && make lint
```
Expected: green. `ArticleFactory` accepts `summary=` as an ordinary model field with no factory change needed.

- [ ] **Step 10: Commit**

```bash
jj commit -m "Add optional article summary with derived fallback"
```

---

### Task 3: Hero removal and the published invariant

**Files:**
- Modify: `src/django-backend/services/articles/exceptions.py`
- Modify: `src/django-backend/services/articles/handler_interface.py`
- Modify: `src/django-backend/services/articles/django_impl/handler.py:105`
- Modify: `src/django-backend/api/routers/articles.py:166`
- Test: `src/django-backend/services/articles/django_impl/test_handler.py`, `src/django-backend/api/routers/test_articles.py`

**Interfaces:**
- Consumes: `update_article(..., summary: str | None = None)` from Task 2.
- Produces: `UNSET` (instance of `UnsetType`) exported from `services.articles.handler_interface`; `PublishedArticleNeedsHeroImageError` from `services.articles.exceptions`; `update_article(..., hero_image_id: UUID | None | UnsetType = UNSET)`.

- [ ] **Step 1: Write the failing tests**

Append to `src/django-backend/services/articles/django_impl/test_handler.py`:

```python
@pytest.mark.django_db
class TestUpdateHeroImage:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_omitting_hero_image_id_leaves_the_hero_alone(self):
        article = ArticleFactory()
        original_hero_id = article.hero_image_id

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.hero_image_id == original_hero_id

    def test_explicit_none_clears_the_hero_on_a_draft(self):
        article = ArticleFactory(state=ArticleState.DRAFT)
        assert article.hero_image_id is not None

        updated = self.handler.update_article(article.id, hero_image_id=None)

        updated.refresh_from_db()
        assert updated.hero_image_id is None

    def test_explicit_none_on_a_published_article_is_rejected(self):
        article = ArticleFactory(
            state=ArticleState.PUBLISHED,
            slug="a-post",
            published_at=timezone.now(),
        )
        original_hero_id = article.hero_image_id

        with pytest.raises(PublishedArticleNeedsHeroImageError):
            self.handler.update_article(article.id, hero_image_id=None)

        article.refresh_from_db()
        assert article.hero_image_id == original_hero_id

    def test_swapping_the_hero_on_a_published_article_is_allowed(self):
        article = ArticleFactory(
            state=ArticleState.PUBLISHED,
            slug="a-post",
            published_at=timezone.now(),
        )
        replacement = ProjectImageFactory(project=article.project)

        updated = self.handler.update_article(
            article.id, hero_image_id=replacement.id
        )

        assert updated.hero_image_id == replacement.id
```

Add `PublishedArticleNeedsHeroImageError` to the `services.articles.exceptions` import block at the top of the file.

Append to `TestPatchArticle` in `src/django-backend/api/routers/test_articles.py`:

```python
    def test_patch_without_hero_key_keeps_the_hero(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        original_hero_id = article.hero_image_id

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Updated"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        article.refresh_from_db()
        assert_that(article.hero_image_id, equal_to(original_hero_id))

    def test_explicit_null_hero_clears_it_on_a_draft(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project, state=ArticleState.DRAFT)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Updated", "hero_image_id": None},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["hero_image_id"], equal_to(None))
        article.refresh_from_db()
        assert_that(article.hero_image_id, equal_to(None))

    def test_explicit_null_hero_on_a_published_article_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(
            project=project,
            state=ArticleState.PUBLISHED,
            slug="a-post",
            published_at=timezone.now(),
        )

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"hero_image_id": None},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(422))
        assert_that(
            response.json()["detail"],
            equal_to(
                "Published articles need a hero image — "
                "replace it rather than removing it."
            ),
        )
```

Add `from django.utils import timezone` and `ArticleState` to that file's imports if not already present.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest services/articles/django_impl/test_handler.py::TestUpdateHeroImage api/routers/test_articles.py::TestPatchArticle -v
```
Expected: `ImportError` for `PublishedArticleNeedsHeroImageError`, and the clearing tests fail because the hero survives.

- [ ] **Step 3: Add the exception**

Append to `src/django-backend/services/articles/exceptions.py`:

```python
class PublishedArticleNeedsHeroImageError(ArticleError):
    """Clearing the hero image was requested on an already-published article."""
```

- [ ] **Step 4: Add the sentinel and widen the interface**

In `src/django-backend/services/articles/handler_interface.py`, at module level — **outside** the `if TYPE_CHECKING:` block, because the value is needed at runtime:

```python
class UnsetType:
    """Distinguishes 'field omitted' from 'field explicitly set to null'.

    PATCH payloads cannot express "clear this" with ``None`` alone, because
    ``None`` is also what an absent optional field deserialises to.
    """

    def __repr__(self) -> str:
        return "UNSET"


UNSET = UnsetType()
```

Change `update_article`'s `hero_image_id` parameter in the same file to:

```python
        hero_image_id: UUID | None | UnsetType = UNSET,
```

- [ ] **Step 5: Implement the handler branch**

In `src/django-backend/services/articles/django_impl/handler.py`, import the sentinel:

```python
from services.articles.handler_interface import UNSET, ArticleHandlerInterface, UnsetType
```

(keep whatever the existing import of `ArticleHandlerInterface` looks like — merge, do not duplicate)

Add `PublishedArticleNeedsHeroImageError` to the `services.articles.exceptions` import.

Change the `update_article` signature's `hero_image_id` to `UUID | None | UnsetType = UNSET`, and replace the block at line 105:

```python
        if hero_image_id is not UNSET:
            hero_image = self._resolve_hero_image(hero_image_id, article.project_id)
            if hero_image is None and article.state == ArticleState.PUBLISHED:
                raise PublishedArticleNeedsHeroImageError
            new_hero_id = hero_image.pk if hero_image else None
            if new_hero_id != article.hero_image_id:
                article.hero_image = hero_image
                update_fields.append("hero_image")
```

`_resolve_hero_image` (`handler.py:247`) raises `HeroImageOnWrongProjectError` for an unknown id, so `None` here only ever means "the caller asked to clear it".

- [ ] **Step 6: Plumb `exclude_unset` through the router**

In `src/django-backend/api/routers/articles.py`, add to the imports:

```python
from services.articles.handler_interface import UNSET
```

and add `PublishedArticleNeedsHeroImageError` to the `services.articles.exceptions` import block.

In `patch_article`, replace the `HANDLERS.articles.update_article(...)` call and its `except` clauses with:

```python
    # A PATCH body cannot express "clear the hero" with null alone, because an
    # omitted optional field deserialises to null too. Only forward the key the
    # client actually sent; everything else stays UNSET.
    provided = payload.dict(exclude_unset=True)
    try:
        article = HANDLERS.articles.update_article(
            article_id,
            title=payload.title,
            body=payload.body,
            summary=payload.summary,
            hero_image_id=provided.get("hero_image_id", UNSET),
            channel_id=payload.channel_id,
            published_at=payload.published_at,
        )
    except ArticleNotFoundError:
        return 404, {"detail": "Article not found"}
    except (ChannelNotFoundError, ChannelOnWrongProjectError):
        return 404, {"detail": "Channel not found on this project"}
    except HeroImageOnWrongProjectError:
        return 422, {"detail": "Hero image must belong to this project"}
    except PublishedArticleNeedsHeroImageError:
        return 422, {
            "detail": (
                "Published articles need a hero image — "
                "replace it rather than removing it."
            )
        }
```

`.dict()` defaults to python mode, so `provided["hero_image_id"]` is still a `UUID`.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
uv run pytest services/articles/django_impl/test_handler.py api/routers/test_articles.py -v
```
Expected: all pass.

- [ ] **Step 8: Full suite and lint**

```bash
make test && make lint
```
Expected: green.

- [ ] **Step 9: Commit**

```bash
jj commit -m "Let PATCH clear an article hero image, and keep published articles from losing theirs"
```

---

### Task 4: Regenerate the API contract and TypeScript types

Mechanical, but its own task because everything after it depends on the generated types compiling.

**Files:**
- Modify (generated): `src/django-backend/backend-openapi.json`
- Modify (generated): `src/web-ui/src/lib/api-types.ts`

**Interfaces:**
- Consumes: the schema changes from Tasks 2 and 3.
- Produces: `ArticleListItem.summary: string`, `Article.summary: string`, `Article.summary_display: string`, `ArticleUpdate.summary?: string | null` in `src/web-ui/src/lib/api-types.ts`.

- [ ] **Step 1: Regenerate the OpenAPI spec**

From `src/django-backend/`:
```bash
make extract-openapi
```

- [ ] **Step 2: Regenerate the TypeScript types**

From `src/web-ui/`:
```bash
npm run generate-types
```

- [ ] **Step 3: Verify the new fields landed**

```bash
rg -n "summary" src/web-ui/src/lib/api-types.ts
```
Expected: `summary` on `ArticleListItem`, `summary` and `summary_display` on `ArticleOut`, `summary` on `ArticleUpdate`. If any is missing, the schema edit in Task 2 is incomplete — go back rather than hand-editing.

- [ ] **Step 4: Typecheck and lint**

From `src/web-ui/`:
```bash
npm run lint && npx tsc --noEmit
```
Expected: clean. Nothing consumes the new fields yet, so this should pass untouched.

- [ ] **Step 5: Commit**

```bash
jj commit -m "Regenerate OpenAPI spec and TypeScript types for article summary"
```

---

### Task 5: `ArticleHeroImage`

One definition of how an article hero is framed, adopted at its two existing call sites in the same task so nothing is left half-migrated.

**Files:**
- Create: `src/web-ui/src/components/ArticleHeroImage.tsx`
- Create: `src/web-ui/src/components/article-card.test.tsx`
- Modify: `src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx:97-106`
- Modify: `src/web-ui/src/app/my-projects/[id]/MyProjectArticles.tsx:97-106`

**Interfaces:**
- Consumes: `GradientPlaceholder` from `@/components/GradientPlaceholder`.
- Produces: `ArticleHeroImage({ src, alt, articleId, priority, className })` where `src: string | null | undefined`, `alt: string`, `articleId: string`, `priority?: boolean` (default `false`), `className?: string` (applied to the wrapper, for rounding).

- [ ] **Step 1: Write the failing test**

Create `src/web-ui/src/components/article-card.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { ArticleHeroImage } from "./ArticleHeroImage";

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// ---------------------------------------------------------------- the tests

describe("ArticleHeroImage", () => {
  it("crops to 16:9 so a wide upload is not squashed into a square", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleHeroImage
        src="https://cdn.example/hero.png"
        alt="A screenshot"
        articleId="article-1"
      />,
    );

    const img = container.querySelector("img")!;
    expect(img.getAttribute("src")).toBe("https://cdn.example/hero.png");
    expect(img.className).toContain("object-cover");
    expect(container.querySelector(".aspect-\\[16\\/9\\]")).not.toBeNull();

    cleanup();
  });

  it("falls back to a gradient placeholder when there is no image", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleHeroImage src={null} alt="" articleId="article-1" />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector(".aspect-\\[16\\/9\\]")).not.toBeNull();

    cleanup();
  });

  it("loads eagerly when marked priority and lazily otherwise", async () => {
    const eager = await mount(
      <ArticleHeroImage src="/a.png" alt="" articleId="a" priority />,
    );
    expect(eager.container.querySelector("img")!.getAttribute("loading")).toBe(
      "eager",
    );
    eager.unmount();

    const lazy = await mount(
      <ArticleHeroImage src="/b.png" alt="" articleId="b" />,
    );
    expect(lazy.container.querySelector("img")!.getAttribute("loading")).toBe(
      "lazy",
    );
    lazy.unmount();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

From `src/web-ui/`:
```bash
npx vitest run src/components/article-card.test.tsx
```
Expected: FAIL — cannot resolve `./ArticleHeroImage`.

- [ ] **Step 3: Write the component**

Create `src/web-ui/src/components/ArticleHeroImage.tsx`:

```tsx
"use client";

import { GradientPlaceholder } from "./GradientPlaceholder";

interface Props {
  src: string | null | undefined;
  alt: string;
  articleId: string;
  // Set on the one hero that is above the fold — the lead card, or the hero on
  // an article page. Everything else stays lazy.
  priority?: boolean;
  className?: string;
}

// The single definition of how an article hero is framed. A fixed 16:9 crop
// means a wide upload lands as-is and a portrait upload gives a centre band,
// and — because the card, the listing lead and the article page all use this —
// what the author frames is what every surface shows.
//
// Only original uploads are stored, with no size variants (see
// docs/image-performance-analysis.md), so these are full-resolution files.
export function ArticleHeroImage({
  src,
  alt,
  articleId,
  priority = false,
  className = "",
}: Props) {
  return (
    <div
      className={`relative aspect-[16/9] w-full overflow-hidden bg-muted ${className}`}
    >
      {src ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={src}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <GradientPlaceholder id={articleId} className="absolute inset-0" />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
npx vitest run src/components/article-card.test.tsx
```
Expected: 3 passed.

- [ ] **Step 5: Adopt it on the article page**

In `src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx`, add the import:

```tsx
import { ArticleHeroImage } from "@/components/ArticleHeroImage";
```

and replace the whole `{article.hero_image_url && (…)}` block at lines 97-106 with:

```tsx
        {article.hero_image_url && (
          <ArticleHeroImage
            src={article.hero_image_url}
            alt={article.title}
            articleId={article.id}
            priority
            className="rounded-lg mt-6"
          />
        )}
```

This replaces `w-full h-auto object-cover max-h-96`, which cropped to whatever `100% × 384px` was at the current viewport — so its framing shifted with screen width and never matched the listing's.

- [ ] **Step 6: Adopt it in the management list**

In `src/web-ui/src/app/my-projects/[id]/MyProjectArticles.tsx`, add the same import, and replace the `{article.hero_image_url ? (…) : (…)}` block at lines 97-106 with:

```tsx
                  <ArticleHeroImage
                    src={article.hero_image_url}
                    alt=""
                    articleId={article.id}
                    className="w-20 flex-shrink-0 rounded"
                  />
```

An author who picked a wide image should not see it as a square in their own list. The row keeps its existing compact layout and badges otherwise.

- [ ] **Step 7: Typecheck, lint, and run the full frontend suite**

```bash
npm run lint && npx tsc --noEmit && npm test
```
Expected: green.

- [ ] **Step 8: Commit**

```bash
jj commit -m "Add ArticleHeroImage and use it for the article page and management list"
```

---

### Task 6: `ArticleCard`

**Files:**
- Create: `src/web-ui/src/components/ArticleCard.tsx`
- Modify: `src/web-ui/src/components/article-card.test.tsx`

**Interfaces:**
- Consumes: `ArticleHeroImage` from Task 5; `ArticleListItem` from `@/lib/api` (now carrying `summary: string`); `formatDate` from `@/lib/utils`.
- Produces: `ArticleCard({ article, href, variant })` where `article: ArticleListItem`, `href: string`, `variant: "lead" | "grid"`.

- [ ] **Step 1: Write the failing tests**

Add to `src/web-ui/src/components/article-card.test.tsx` — the import at the top, a factory, and a new `describe`:

```tsx
import { ArticleCard } from "./ArticleCard";
import type { ArticleListItem } from "@/lib/api";

// --------------------------------------------------------------- factories

function articleListItem(
  overrides: Partial<ArticleListItem> = {},
): ArticleListItem {
  return {
    id: "article-1",
    title: "A headline about something",
    summary: "A short summary of the article.",
    slug: "a-headline",
    state: "published",
    published_at: "2026-08-01T10:00:00Z",
    global_visibility: "auto",
    channel: { id: "channel-1", name: "Releases" },
    hero_image_url: "https://cdn.example/hero.png",
    ...overrides,
  } as ArticleListItem;
}

describe("ArticleCard", () => {
  it("renders the headline, channel and summary, linking to the article", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCard
        article={articleListItem()}
        href="/projects/p/articles/a-headline"
        variant="grid"
      />,
    );

    const link = container.querySelector("a")!;
    expect(link.getAttribute("href")).toBe("/projects/p/articles/a-headline");
    expect(container.textContent).toContain("A headline about something");
    expect(container.textContent).toContain("Releases");
    expect(container.textContent).toContain("A short summary of the article.");

    cleanup();
  });

  it("gives the lead variant a larger headline than the grid variant", async () => {
    const lead = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="lead" />,
    );
    expect(lead.container.querySelector("h3")!.className).toContain("text-2xl");
    lead.unmount();

    const grid = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="grid" />,
    );
    expect(grid.container.querySelector("h3")!.className).toContain("text-base");
    grid.unmount();
  });

  it("loads the lead hero eagerly and grid heroes lazily", async () => {
    const lead = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="lead" />,
    );
    expect(lead.container.querySelector("img")!.getAttribute("loading")).toBe(
      "eager",
    );
    lead.unmount();

    const grid = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="grid" />,
    );
    expect(grid.container.querySelector("img")!.getAttribute("loading")).toBe(
      "lazy",
    );
    grid.unmount();
  });

  it("renders without a summary or a published date", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCard
        article={articleListItem({ summary: "", published_at: null })}
        href="/x"
        variant="grid"
      />,
    );

    expect(container.textContent).toContain("A headline about something");

    cleanup();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npx vitest run src/components/article-card.test.tsx
```
Expected: FAIL — cannot resolve `./ArticleCard`.

- [ ] **Step 3: Write the component**

Create `src/web-ui/src/components/ArticleCard.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArticleHeroImage } from "./ArticleHeroImage";

interface Props {
  article: ArticleListItem;
  // Supplied rather than derived from a project slug: a cross-project feed
  // builds its links differently.
  href: string;
  variant: "lead" | "grid";
}

const HEADLINE = {
  lead: "text-2xl font-semibold line-clamp-3",
  grid: "text-base font-semibold line-clamp-2",
} as const;

const SUMMARY = {
  lead: "line-clamp-2",
  grid: "line-clamp-3",
} as const;

export function ArticleCard({ article, href, variant }: Props) {
  const isLead = variant === "lead";

  return (
    <article className="rounded-lg border border-border bg-white overflow-hidden hover:border-accent/50 transition-colors">
      <Link href={href} className="block">
        <ArticleHeroImage
          src={article.hero_image_url}
          alt=""
          articleId={article.id}
          priority={isLead}
        />
        <div className={isLead ? "p-5" : "p-4"}>
          <div className="text-xs font-semibold uppercase tracking-wide text-accent">
            {article.channel.name}
            {article.published_at && (
              <span className="text-muted-foreground font-normal normal-case tracking-normal">
                {" · "}
                {formatDate(article.published_at)}
              </span>
            )}
          </div>
          <h3 className={`mt-1.5 text-foreground ${HEADLINE[variant]}`}>
            {article.title}
          </h3>
          {article.summary && (
            <p
              className={`mt-2 text-sm text-muted-foreground ${SUMMARY[variant]}`}
            >
              {article.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npx vitest run src/components/article-card.test.tsx
```
Expected: 7 passed (3 from Task 5, 4 new).

- [ ] **Step 5: Typecheck and lint**

```bash
npm run lint && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
jj commit -m "Add ArticleCard with lead and grid variants"
```

---

### Task 7: Rebuild `ArticlesList` as lead plus grid

**Files:**
- Modify: `src/web-ui/src/app/projects/[slug]/ArticlesList.tsx:67-105`

**Interfaces:**
- Consumes: `ArticleCard` from Task 6.
- Produces: nothing new — this is the consumer.

- [ ] **Step 1: Replace the render block**

In `src/web-ui/src/app/projects/[slug]/ArticlesList.tsx`, add the import:

```tsx
import { ArticleCard } from "@/components/ArticleCard";
```

Remove the now-unused `Link` and `formatDate` imports (`ArticleCard` owns both).

Replace the `return (<ul …>…</ul>)` block at lines 67-105 with:

```tsx
  const [lead, ...rest] = articles;

  return (
    <div className="space-y-5">
      <ArticleCard
        article={lead}
        href={`/projects/${projectSlug}/articles/${lead.slug}`}
        variant="lead"
      />
      {rest.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2">
          {rest.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              href={`/projects/${projectSlug}/articles/${article.slug}`}
              variant="grid"
            />
          ))}
        </div>
      )}
    </div>
  );
```

The `articles.length === 0` guard above already returns early, so `lead` is always defined here. Sorting and filtering are unchanged.

- [ ] **Step 2: Update the loading skeleton to match**

Replace the `articles === null` block at lines 53-60 with:

```tsx
  if (articles === null) {
    return (
      <div className="space-y-5">
        <div className="skeleton aspect-[16/9] w-full rounded-lg" />
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="skeleton aspect-[16/9] w-full rounded-lg" />
          <div className="skeleton aspect-[16/9] w-full rounded-lg" />
        </div>
      </div>
    );
  }
```

- [ ] **Step 3: Typecheck, lint, and run the suite**

```bash
npm run lint && npx tsc --noEmit && npm test
```
Expected: green.

- [ ] **Step 4: Check it in the browser**

Start the app per `CLAUDE.md`, log in with the credentials in `.env.claude`, and open a project with at least three published articles. Confirm: the newest article is a full-width 16:9 lead, the rest sit in a two-column grid, and a wide hero is no longer cropped to a square.

Known and accepted: with exactly two articles you get a full-width lead and one half-width card with a gap beside it.

- [ ] **Step 5: Commit**

```bash
jj commit -m "Render project articles as a lead story plus a card grid"
```

---

### Task 8: Card preview with summary editing

**Files:**
- Create: `src/web-ui/src/app/projects/[slug]/articles/ArticleCardPreview.tsx`
- Create: `src/web-ui/src/app/projects/[slug]/articles/ArticleCardPreviewDialog.tsx`
- Create: `src/web-ui/src/app/projects/[slug]/articles/article-card-preview.test.tsx`

**Interfaces:**
- Consumes: `ArticleCard` from Task 6; `Dialog` from `@/components/Dialog`; `Article` (i.e. `ArticleOut`, carrying `summary` and `summary_display`) from `@/lib/api`.
- Produces:
  - `toListItem(article: Article, summaryOverride?: string): ArticleListItem` — adapts a full article to what `ArticleCard` needs, exported from `ArticleCardPreview.tsx`.
  - `ArticleCardPreview({ article, summary, onSummaryChange })` where `summary: string` and `onSummaryChange: (value: string) => void`.
  - `ArticleCardPreviewDialog({ article, projectSlug, onClose, onSaved })` where `onSaved: (article: Article) => void`.

- [ ] **Step 1: Write the failing tests**

Create `src/web-ui/src/app/projects/[slug]/articles/article-card-preview.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Article } from "@/lib/api";
import { ArticleCardPreview, toListItem } from "./ArticleCardPreview";

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

async function typeInto(el: HTMLTextAreaElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "value",
  )!.set!;
  await act(async () => {
    setValue.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

// --------------------------------------------------------------- factories

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-1",
    project: { id: "p1", slug: "proj", title: "A project" },
    channel: { id: "c1", name: "Releases" },
    author: null,
    title: "A headline",
    body: "The body opening line.",
    summary: "",
    summary_display: "The body opening line.",
    hero_image_id: "img-1",
    hero_image_url: "https://cdn.example/hero.png",
    slug: "a-headline",
    source: "internal",
    external_url: null,
    state: "draft",
    published_at: null,
    global_visibility: "auto",
    is_globally_visible: false,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  } as Article;
}

// ---------------------------------------------------------------- the tests

describe("toListItem", () => {
  it("prefers the authored summary over the derived one", () => {
    const item = toListItem(article({ summary: "Authored." }));

    expect(item.summary).toBe("Authored.");
  });

  it("falls back to summary_display when nothing is authored", () => {
    const item = toListItem(article({ summary: "" }));

    expect(item.summary).toBe("The body opening line.");
  });
});

describe("ArticleCardPreview", () => {
  it("shows the derived summary as a placeholder when none is authored", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={() => {}}
      />,
    );

    const textarea = container.querySelector("textarea")!;
    expect(textarea.value).toBe("");
    expect(textarea.getAttribute("placeholder")).toBe("The body opening line.");

    cleanup();
  });

  it("reports typed text back to its owner", async () => {
    const onSummaryChange = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={onSummaryChange}
      />,
    );

    await typeInto(container.querySelector("textarea")!, "An authored hook.");

    expect(onSummaryChange).toHaveBeenCalledWith("An authored hook.");

    cleanup();
  });

  it("previews the typed summary rather than the derived one", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary="An authored hook."
        onSummaryChange={() => {}}
      />,
    );

    expect(container.textContent).toContain("An authored hook.");

    cleanup();
  });

  it("renders both a lead and a grid card", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={() => {}}
      />,
    );

    expect(container.querySelectorAll("article").length).toBe(2);

    cleanup();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npx vitest run "src/app/projects/[slug]/articles/article-card-preview.test.tsx"
```
Expected: FAIL — cannot resolve `./ArticleCardPreview`.

- [ ] **Step 3: Write the presentational component**

Create `src/web-ui/src/app/projects/[slug]/articles/ArticleCardPreview.tsx`:

```tsx
"use client";

import { ArticleCard } from "@/components/ArticleCard";
import type { Article, ArticleListItem } from "@/lib/api";

const SUMMARY_MAX = 300;

interface Props {
  article: Article;
  summary: string;
  onSummaryChange: (value: string) => void;
}

// ArticleCard takes a list item, so adapt. `summary` on a list item is already
// resolved server-side — mirror that here by falling back to summary_display.
export function toListItem(
  article: Article,
  summaryOverride?: string,
): ArticleListItem {
  const summary = summaryOverride ?? article.summary;
  return {
    id: article.id,
    title: article.title,
    summary: summary || article.summary_display,
    slug: article.slug,
    state: article.state,
    published_at: article.published_at,
    global_visibility: article.global_visibility,
    channel: article.channel,
    hero_image_url: article.hero_image_url,
  } as ArticleListItem;
}

export function ArticleCardPreview({
  article,
  summary,
  onSummaryChange,
}: Props) {
  const item = toListItem(article, summary);
  const href = `/projects/${article.project.slug ?? article.project.id}/articles/${article.slug ?? ""}`;

  return (
    <div className="space-y-5">
      <ArticleCard article={item} href={href} variant="lead" />
      <div className="max-w-sm">
        <ArticleCard article={item} href={href} variant="grid" />
      </div>

      <div>
        <label
          htmlFor="article-summary"
          className="block text-sm font-medium text-foreground"
        >
          Summary
        </label>
        <textarea
          id="article-summary"
          value={summary}
          placeholder={article.summary_display}
          maxLength={SUMMARY_MAX}
          rows={3}
          onChange={(e) => onSummaryChange(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
        />
        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
          <span>Leave empty to use the start of the article.</span>
          <span>
            {summary.length}/{SUMMARY_MAX}
          </span>
        </div>
      </div>
    </div>
  );
}
```

The `<article>` element inside `ArticleCard` is what the "renders both a lead and a grid card" test counts.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npx vitest run "src/app/projects/[slug]/articles/article-card-preview.test.tsx"
```
Expected: 6 passed.

- [ ] **Step 5: Write the dialog shell**

Create `src/web-ui/src/app/projects/[slug]/articles/ArticleCardPreviewDialog.tsx`:

```tsx
"use client";

import { useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { Dialog } from "@/components/Dialog";
import { api } from "@/lib/api";
import type { Article } from "@/lib/api";
import { ArticleCardPreview } from "./ArticleCardPreview";

interface Props {
  article: Article;
  projectSlug: string;
  onClose: () => void;
  onSaved: (article: Article) => void;
}

export function ArticleCardPreviewDialog({
  article,
  projectSlug,
  onClose,
  onSaved,
}: Props) {
  const [summary, setSummary] = useState(article.summary);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setIsSaving(true);
    setError("");
    try {
      // "" is meaningful: it clears the override and returns the card to the
      // derived excerpt. The response carries a refreshed summary_display.
      const saved = await api.articles.update(projectSlug, article.id, {
        summary,
      });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save summary");
      setIsSaving(false);
    }
  };

  return (
    <Dialog isOpen onClose={onClose} className="max-w-2xl">
      <h2 className="text-lg font-semibold text-foreground">
        How this article will look in a list
      </h2>

      <div className="mt-4 max-h-[60vh] overflow-y-auto pr-1">
        <ArticleCardPreview
          article={article}
          summary={summary}
          onSummaryChange={setSummary}
        />
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <button
          onClick={onClose}
          disabled={isSaving}
          className="text-sm py-2 px-4 rounded-lg border border-border text-foreground hover:bg-muted transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary text-sm py-2 px-4"
        >
          {isSaving ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            "Save summary"
          )}
        </button>
      </div>
    </Dialog>
  );
}
```

- [ ] **Step 6: Typecheck, lint, and run the suite**

```bash
npm run lint && npx tsc --noEmit && npm test
```
Expected: green.

- [ ] **Step 7: Commit**

```bash
jj commit -m "Add article card preview dialog with summary editing"
```

---

### Task 9: Wire the preview button and guard published articles

**Files:**
- Modify: `src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts`
- Modify: `src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx`

**Interfaces:**
- Consumes: `ArticleCardPreviewDialog` from Task 8.
- Produces: `useArticleDraft` additionally returns `setArticle: (article: Article) => void` and `needsHeroImage: boolean` (true when the article is published and `form.hero_image_id` is null).

- [ ] **Step 1: Expose the two new values from the hook**

In `src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts`, add to the returned object (the `return { … }` at line 236):

```ts
    setArticle,
    needsHeroImage: article?.state === "published" && !form?.hero_image_id,
```

`setArticle` is the existing `useState` setter and needs no new code — the preview dialog uses it to push the saved article back after a summary change.

- [ ] **Step 2: Add the preview button and the guard**

In `src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx`:

Add the import:

```tsx
import { ArticleCardPreviewDialog } from "./ArticleCardPreviewDialog";
```

Add state next to `showPublishDialog`:

```tsx
  const [showCardPreview, setShowCardPreview] = useState(false);
  const [isOpeningPreview, setIsOpeningPreview] = useState(false);
```

Add the handler next to `handleDeleteClick`:

```tsx
  // The derived summary lives only in the backend, so the preview has to render
  // a saved article — otherwise it would show a stale excerpt for unsaved body
  // text. Save first; if that fails, draft.error already says why.
  const handlePreviewClick = async () => {
    setIsOpeningPreview(true);
    await draft.save();
    setIsOpeningPreview(false);
    setShowCardPreview(true);
  };
```

Disable Save when a published article has lost its hero — replace the Save button's `disabled` prop with:

```tsx
              disabled={
                draft.isSaving || draft.isPublishing || draft.needsHeroImage
              }
```

Add the preview button immediately before the Save button in the toolbar:

```tsx
            {draft.article && (
              <button
                onClick={handlePreviewClick}
                disabled={
                  draft.isSaving ||
                  draft.isPublishing ||
                  isOpeningPreview ||
                  draft.needsHeroImage
                }
                className="text-sm py-2 px-4 rounded-lg border border-border text-foreground hover:bg-muted transition-colors"
              >
                {isOpeningPreview ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  "Preview card"
                )}
              </button>
            )}
```

Add the inline warning immediately after `<HeroImageUploader … />`:

```tsx
        {draft.needsHeroImage && (
          <p className="text-sm text-amber-800" role="alert">
            Published articles need a hero image — add one before saving.
          </p>
        )}
```

Render the dialog next to `PublishDialog` at the end of the component:

```tsx
      {showCardPreview && draft.article && (
        <ArticleCardPreviewDialog
          article={draft.article}
          projectSlug={project.slug ?? project.id}
          onClose={() => setShowCardPreview(false)}
          onSaved={draft.setArticle}
        />
      )}
```

The button and dialog are gated on `draft.article` because a never-saved draft has no id to PATCH a summary onto.

- [ ] **Step 3: Typecheck, lint, and run the suite**

```bash
npm run lint && npx tsc --noEmit && npm test
```
Expected: green.

- [ ] **Step 4: Check it in the browser**

Start the app, log in with the credentials in `.env.claude`, and open an existing article for editing. Confirm:
- "Preview card" saves, then opens a dialog showing a lead card and a grid card with the real hero.
- The summary box is empty with the article's opening text as its placeholder; typing updates both cards live.
- Save summary closes the dialog; reopening shows the authored text as the value.
- Clearing the box and saving returns the placeholder and the derived excerpt.
- On a published article, removing the hero disables Save and shows the amber warning.

- [ ] **Step 5: Commit**

```bash
jj commit -m "Add Preview card button and block saving a published article with no hero"
```

---

### Task 10: End-to-end regression for hero removal

The bug that started this. It needs the app and backend running.

**Files:**
- Create: `src/web-ui/e2e/article-hero-removal.spec.ts`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Write the spec**

Create `src/web-ui/e2e/article-hero-removal.spec.ts`. Copy the `login` and `openBlankArticleEditor` helpers verbatim from `e2e/article-images.spec.ts` — they already handle finding a project without hard-coding a slug.

```ts
import { test, expect, type Page } from "@playwright/test";
import * as path from "path";

const FIXTURES = path.join(__dirname, "fixtures");
const HERO_IMAGE = path.join(FIXTURES, "inline-image.png");

// /api/auth/login is rate limited to 5/min per IP, so this file logs in once
// and runs serially.
test.describe.configure({ mode: "serial" });

// --- copy `login` and `openBlankArticleEditor` from article-images.spec.ts ---

// The clear control is icon-only with title="Remove hero image"
// (HeroImageUploader.tsx:45), so match on the title.
const removeHero = (page: Page) => page.getByTitle("Remove hero image");

// HeroImageUploader renders before ArticleEditor in ArticleAuthoringPage, and
// the editor's insert-image button has a hidden file input of its own, so the
// hero's is the first on the page.
const heroFileInput = (page: Page) =>
  page.locator('input[type="file"]').first();

// Saves and waits for the PATCH/POST itself rather than the "Draft saved"
// message, which clears after 2.5s and would race the second save.
async function saveDraft(page: Page) {
  const saved = page.waitForResponse(
    (r) => /\/api\/projects\/.*\/articles/.test(r.url()) && r.request().method() !== "GET",
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  await saved;
}

test("removing a hero image and saving actually removes it", async ({
  page,
}) => {
  await login(page);
  await openBlankArticleEditor(page);

  await page.fill('input[placeholder="Article title"]', "Hero removal test");
  await heroFileInput(page).setInputFiles(HERO_IMAGE);
  await expect(removeHero(page)).toBeVisible();

  await saveDraft(page);
  await expect(page).toHaveURL(/\/articles\/edit\/[0-9a-f-]+$/);
  const editUrl = page.url();

  await removeHero(page).click();
  await expect(removeHero(page)).toHaveCount(0);
  await saveDraft(page);

  // The regression: before the fix, the hero came back on reload.
  await page.goto(editUrl);
  await expect(page.getByRole("button", { name: "Save draft" })).toBeVisible();
  await expect(removeHero(page)).toHaveCount(0);
});
```

Projects cap at 10 images. This spec uploads one; if you run it repeatedly, delete the uploads from the project's image library or reuse the cleanup helper in `article-images.spec.ts`.

- [ ] **Step 2: Run the spec**

With the backend and web-ui running, from `src/web-ui/`:
```bash
source ../../.env.claude && npx playwright test e2e/article-hero-removal.spec.ts
```
Expected: 1 passed.

- [ ] **Step 3: Lint**

```bash
npm run lint
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
jj commit -m "Add e2e regression for article hero image removal"
```

---

### Task 11: Close the loop

**Files:**
- Modify: `openspec/changes/add-article-authoring/feedback.md`

- [ ] **Step 1: Run the full CI check**

From the repo root:
```bash
make ci
```
Expected: green. If it fails, fix it here rather than leaving it for a later task.

- [ ] **Step 2: Move the two addressed items to Done**

In `openspec/changes/add-article-authoring/feedback.md`, move these two lines under the existing `Done:` heading:

- "If we're going to select large wide images to represent the article, we should have the list of displaying articles be better at rendering those images. Right now it shows it as truncated icon."
- "Hero image doesn't get removed - click remove and save and it remains"

Leave the other items where they are — the preview button, edit-from-view-page and project tab default are untouched by this change.

- [ ] **Step 3: Commit**

```bash
jj commit -m "Mark article image feedback items as done"
```
