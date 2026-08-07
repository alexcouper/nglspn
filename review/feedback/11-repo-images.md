# 11. There is no `REPO.images`, so routers hand-roll `ProjectImage` filters

**Finding:** Architecture point 2 (backend review §1) — four router call sites
query `ProjectImage` directly; `article__isnull=True` is written out three times.
**Alex:** "Fix this and have things use REPO.images"
**Type:** fix proposal
**Effort:** M — two new files (~90 lines), one line in `services/__init__.py`,
five call-site rewrites in two routers, and eight `Prefetch` sites converted if
the second half is taken. Mechanical; the risk is in the call sites' 404
behaviour, not the query service.

## What is actually happening

`services/images/` has a write side and no read side: `handler_interface.py`,
`exceptions.py`, `django_impl/handler.py`, `django_impl/__init__.py`. There is
no `query_interface.py` and no `images` field on `QueryServices`
(`services/__init__.py:62-73`).

### The five direct queries, as they stand

Read, not guessed:

| Site | Query | Filters |
|---|---|---|
| `api/routers/articles.py:289-292` (`_get_article_image_or_404`, a helper) | `get_object_or_404(ProjectImage, id=…, article=article, **filters)` | `article=article` + whatever the caller passes |
| — called at `articles.py:361-363` | | `upload_status=PENDING` |
| — called at `articles.py:388` | | none |
| `api/routers/my_projects.py:253-259` (`complete_upload`) | `get_object_or_404(ProjectImage, …)` | `project=`, `article__isnull=True`, `upload_status=PENDING` |
| `api/routers/my_projects.py:282-287` (`update_image_roles`) | `get_object_or_404(ProjectImage.objects.uploaded(), …)` | `project=`, `article__isnull=True` |
| `api/routers/my_projects.py:321-323` (`delete_image`) | `get_object_or_404(ProjectImage, …)` | `project=`, `article__isnull=True` |

Three spellings of "uploaded": `upload_status=PENDING` inline, `.uploaded()` as a
queryset method, and nothing at all. Three hand-written `article__isnull=True`.

### `project_gallery_images()` is a different shape to the same rule

`services/project/django_impl/query.py:37-48` returns the *set* (`uploaded()` +
`article__isnull=True` + `prefetch_related("variants")`), for use inside
`Prefetch`. The routers need a *single row by id*, which that function does not
give them, which is why they reach past it. It is used at eight places:

- `services/project/django_impl/query.py:54,64,337`
- `services/review/django_impl/query.py:94`
- `services/follows/django_impl/query.py:39`
- `api/routers/my_review.py:24,216` — a **router** importing a `django_impl`
  module function
- `api/schemas/competition.py:12,71` — a **schema** doing the same

The last two are the same layering violation as the finding itself, in a
different costume. They are the reason I would not stop at "add the four
methods".

### What must not be merged

`DjangoImageHandler._gallery_queryset` (`services/images/django_impl/handler.py:181-185`)
looks like `project_gallery_images()` but is not: it also `exclude(is_icon=True)`,
because it defines "counts against the cap / eligible to become the cover".
`project_gallery_images()` must *include* icons, because
`resolve_image_by_purpose` (`services/project/django_impl/query.py:84-105`) looks
for `is_icon` in what it is handed. Two genuinely different sets. Leave the
handler's alone.

## Proposed change

### Option 1 — `REPO.images` for the row lookups only

New query service with `get_gallery_image` / `get_article_image`; rewrite the
five call sites; leave `project_gallery_images()` where it is.

Fixes the finding as written. Leaves the images domain with its read rules split
across two packages, leaves the router and the schema importing `django_impl`
directly, and leaves I1's fix with no obvious home.

### Option 2 — `REPO.images` for lookups *and* the prefetch — **recommended**

Option 1, plus: move `project_gallery_images()` into the images query service as
`gallery_images()`, add `gallery_prefetch(lookup)`, and convert all eight
existing `Prefetch("…images", queryset=…)` sites plus I1's three.

Costs eight extra one-line edits. Buys the thing that was actually asked for: one
home. After it, "images that describe the project" exists once, and there is no
way to write a project-facing prefetch without going through it — which is the
whole content of I1.

### Option 3 — Move the function, re-export the old name from `services/project`

Rejected. An alias means `grep project_gallery_images` still finds the project
package and the next reader has to follow two hops to learn where the rule
lives. Eight import lines is not worth that.

---

### New file: `services/images/query_interface.py`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import Prefetch, QuerySet

    from apps.articles.models import Article
    from apps.projects.models import Project, ProjectImage, UploadStatus


class ImageQueryInterface(ABC):
    """Reads over `ProjectImage`.

    Two rules live here and nowhere else. A project's own images are the rows
    with no `article` — a project endpoint that forgets that is an
    IDOR-adjacent bug with nothing to catch it. An article's images are the
    rows with that `article`, and nothing else about the project.
    """

    @abstractmethod
    def gallery_prefetch(self, lookup: str = "images") -> Prefetch:
        """`Prefetch` for a project's own images, at any relation depth.

        Use for every prefetch that will reach `resolve_image_by_purpose` or a
        project gallery: it does no filtering of its own and will otherwise
        fall back to an article figure or a row whose PUT never landed.
        `lookup` is the relation path — `"images"`,
        `"article__project__images"`, `"winner__images"`.
        """

    @abstractmethod
    def get_gallery_image(
        self,
        project: Project,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        """One of `project`'s own images. `None` if absent, or an article's."""

    @abstractmethod
    def get_article_image(
        self,
        article: Article,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        """One of `article`'s images. `None` if absent, or another article's."""
```

`status` replaces the three ad-hoc spellings. `None` means "any state", which is
what `articles.py:388` and `my_projects.py:321` want — a delete must be able to
reach an abandoned `PENDING` row, and there is a test for that
(`test_article_images.py:320`).

### New file: `services/images/django_impl/query.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Prefetch

from apps.projects.models import ProjectImage
from services.images.query_interface import ImageQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.articles.models import Article
    from apps.projects.models import Project, UploadStatus


def gallery_images() -> QuerySet[ProjectImage]:
    """Images that describe the project itself.

    Excludes article uploads, which live on the project but belong to an
    article. Moved here from `services/project/django_impl/query.py`: the rule
    is about images, and the row-level lookups that enforce the same rule are
    in this module.
    """
    return (
        ProjectImage.objects.uploaded()
        .filter(article__isnull=True)
        .prefetch_related("variants")
    )


def gallery_prefetch(lookup: str = "images") -> Prefetch:
    return Prefetch(lookup, queryset=gallery_images())


class DjangoImageQuery(ImageQueryInterface):
    def gallery_prefetch(self, lookup: str = "images") -> Prefetch:
        # Module-level function, not this method: query services import each
        # other's module functions directly (see follows/query.py:13), and
        # only callers holding the container come through here.
        return gallery_prefetch(lookup)

    def get_gallery_image(
        self,
        project: Project,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        qs = ProjectImage.objects.filter(
            pk=image_id, project=project, article__isnull=True
        )
        if status is not None:
            qs = qs.filter(upload_status=status)
        return qs.first()

    def get_article_image(
        self,
        article: Article,
        image_id: UUID | str,
        *,
        status: UploadStatus | None = None,
    ) -> ProjectImage | None:
        qs = ProjectImage.objects.filter(pk=image_id, article=article)
        if status is not None:
            qs = qs.filter(upload_status=status)
        return qs.first()
```

### Wiring

`services/images/django_impl/__init__.py`:

```diff
 from .handler import DjangoImageHandler
+from .query import DjangoImageQuery, gallery_images, gallery_prefetch

-__all__ = ["DjangoImageHandler"]
+__all__ = [
+    "DjangoImageHandler",
+    "DjangoImageQuery",
+    "gallery_images",
+    "gallery_prefetch",
+]
```

`services/__init__.py`:

```diff
-from services.images.django_impl import DjangoImageHandler
+from services.images.django_impl import DjangoImageHandler, DjangoImageQuery
 from services.images.handler_interface import ImageHandlerInterface
+from services.images.query_interface import ImageQueryInterface
```

```diff
 class QueryServices:
     articles: ArticleQueryInterface = field(default_factory=DjangoArticleQuery)
     discussions: DiscussionQueryInterface = field(default_factory=DjangoDiscussionQuery)
     email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
     follows: FollowQueryInterface = field(default_factory=DjangoFollowQuery)
+    images: ImageQueryInterface = field(default_factory=DjangoImageQuery)
     notifications: NotificationQueryInterface = field(
         default_factory=DjangoNotificationQuery
     )
```

### What moves out of `project_gallery_images()`, what stays

Moves: the whole function. Every line of it is a statement about which
`ProjectImage` rows count, and none of it mentions a project attribute.

Stays in `services/project/django_impl/query.py`: `resolve_image_by_purpose`
(`:84-105`) and `variant_url` (`:108-113`). Those are "which of these images do I
show for this purpose" — project presentation, not set membership. They are also
the reason `gallery_images()` must not exclude icons.

Stays in `services/images/django_impl/handler.py`: `_is_gallery_image` (`:172-179`)
and `_gallery_queryset` (`:181-185`). Different set — see above. Worth adding one
comment there pointing at `gallery_images()` and saying why they differ, since
they are now in the same package and the near-duplication will otherwise read as
an oversight.

Delete from `services/project/django_impl/__init__.py:5,13` the
`project_gallery_images` export.

### Call-site rewrites

**`api/routers/articles.py`**

```diff
-from django.shortcuts import get_object_or_404
 from ninja import Router
```

```diff
 def _get_article_image_or_404(
-    article: Article, image_id: UUID, **filters: Any
-) -> ProjectImage:
-    return get_object_or_404(ProjectImage, id=image_id, article=article, **filters)
+    article: Article, image_id: UUID, *, status: UploadStatus | None = None
+) -> ProjectImage | tuple[int, dict[str, str]]:
+    image = REPO.images.get_article_image(article, image_id, status=status)
+    if image is None:
+        return 404, {"detail": "Image not found"}
+    return image
```

Returning a tuple rather than raising `Http404` matches the file's own
`_get_article_in_project` (`:57-63`), so the router has one error convention
instead of two. The `typing.Any` import at `:1` becomes unused if nothing else
needs it — check before deleting; `payload` typing does not use it.

`complete_article_image_upload` (`:361-369`):

```diff
     image = _get_article_image_or_404(
-        article, image_id, upload_status=UploadStatus.PENDING
+        article, image_id, status=UploadStatus.PENDING
     )
+    if isinstance(image, tuple):
+        return image
     try:
         return HANDLERS.images.complete_upload(
             image, width=payload.width, height=payload.height
         )
```

`delete_article_image` (`:384-389`):

```diff
     article = _get_editable_article(slug, article_id, request.auth.id)
     if isinstance(article, tuple):
         return article
 
-    HANDLERS.images.delete_image(_get_article_image_or_404(article, image_id))
+    image = _get_article_image_or_404(article, image_id)
+    if isinstance(image, tuple):
+        return image
+
+    HANDLERS.images.delete_image(image)
     return 204, None
```

`ProjectImage` and `UploadStatus` stay imported at `:29` — as a return
annotation and an enum value respectively. Neither is ORM access. This matters
for the guard test; see `21-guard-test-projectimage.md`.

**`api/routers/my_projects.py`** — `complete_upload` (`:250-259`):

```diff
     project = _get_editable_project_or_404(project_id, request.auth)
-    # `article__isnull` keeps this endpoint off article uploads: those are
-    # addressed under the articles router and completed there.
-    image = get_object_or_404(
-        ProjectImage,
-        id=image_id,
-        project=project,
-        article__isnull=True,
-        upload_status=UploadStatus.PENDING,
-    )
+    # `get_gallery_image` keeps this endpoint off article uploads: those are
+    # addressed under the articles router and completed there.
+    image = REPO.images.get_gallery_image(
+        project, image_id, status=UploadStatus.PENDING
+    )
+    if image is None:
+        return 404, {"detail": "Image not found"}
```

`update_image_roles` (`:281-287`):

```diff
     project = _get_editable_project_or_404(project_id, request.auth)
-    image = get_object_or_404(
-        ProjectImage.objects.uploaded(),
-        id=image_id,
-        project=project,
-        article__isnull=True,
-    )
+    image = REPO.images.get_gallery_image(
+        project, image_id, status=UploadStatus.UPLOADED
+    )
+    if image is None:
+        return 404, {"detail": "Image not found"}
```

`delete_image` (`:315-325`):

```diff
 def delete_image(
     request: HttpRequest,
     project_id: str,
     image_id: str,
-) -> tuple[int, None]:
+) -> tuple[int, None] | tuple[int, dict[str, str]]:
     project = _get_editable_project_or_404(project_id, request.auth)
-    image = get_object_or_404(
-        ProjectImage, id=image_id, project=project, article__isnull=True
-    )
+    image = REPO.images.get_gallery_image(project, image_id)
+    if image is None:
+        return 404, {"detail": "Image not found"}
     HANDLERS.images.delete_image(image)
     return 204, None
```

`get_object_or_404` stays imported in `my_projects.py` — `_get_editable_project_or_404`
(`:38-42`) still uses it on `Project`. That is the same violation one model over
and should be `REPO.project.get_by_id`, but it is not this finding; leaving it
means `my_projects.py` cannot get a guard test yet.

**Prefetch sites (Option 2 only)** — each becomes
`REPO.images.gallery_prefetch(<lookup>)` in routers and schemas, and
`gallery_prefetch(<lookup>)` imported from `services.images.django_impl.query` in
query services:

- `services/project/django_impl/query.py:54,64` → `gallery_prefetch()`
- `services/project/django_impl/query.py:337` → `gallery_prefetch("winner__images")`
- `services/review/django_impl/query.py:94` → `gallery_prefetch()`
- `services/follows/django_impl/query.py:39` → `gallery_prefetch("project__images")`
- `api/routers/my_review.py:216` → `REPO.images.gallery_prefetch()`; drop the
  `django_impl` import at `:24`
- `api/schemas/competition.py:71` → `REPO.images.gallery_prefetch()`; the
  `to_list_item` import at `:12` stays

## Interaction with I1, and whether they land together

I1 is `services/notifications/django_impl/handler.py:328` and `:377` passing the
bare string `"article__project__images__variants"`, plus the pre-existing
discussion path at `:363`. With `gallery_prefetch` those become:

```diff
             .prefetch_related(
                 "article__listing_image__variants",
-                "article__project__images__variants",
+                REPO.images.gallery_prefetch("article__project__images"),
             )
```

and likewise `gallery_prefetch("discussion__project__images")` at `:363`.

**Land them together.** Not because I1 depends on this — it could be fixed today
with `Prefetch("article__project__images", queryset=project_gallery_images())` —
but because the reason I1 happened is that the correct spelling was verbose,
lived in another domain's package, and was easy not to know about. Fixing the
bug without the helper leaves the next prefetch exactly as likely to be written
as a bare string. One commit for the query service, one for the call sites, one
for I1, in a single change.

## Tests

New `services/images/django_impl/test_query.py` — the rules, once, at the level
they now live:

- `test_gallery_image_excludes_an_article_upload`
- `test_gallery_image_excludes_an_image_on_another_project`
- `test_gallery_image_honours_the_status_filter` (pending row invisible when
  `status=UPLOADED`, visible when `status=None`)
- `test_article_image_excludes_another_articles_upload`
- `test_article_image_excludes_a_project_gallery_image`
- `test_gallery_prefetch_narrows_a_nested_relation` — build a project with one
  gallery image, one article figure and one `PENDING` row, prefetch through
  `gallery_prefetch("article__project__images")`, assert one row. This is the
  test that would have caught I1.

Existing coverage that must stay green unchanged, and is the real safety net for
the call-site rewrites:

- `api/routers/test_project_images.py:713`, `:728`, `:744`, `:765` — the project
  endpoints refusing article images.
- `api/routers/test_article_images.py:278`, `:290`, `:320`, `:330` — the article
  endpoints refusing other articles' and the project's images, and deleting an
  abandoned `PENDING` row.

Add `api/routers/test_articles.py::TestRouterHasNoOrmAccess` extension — see
`21-guard-test-projectimage.md`. It fails before this change and passes after,
which is the point.

## Risks and what this does not cover

- **404 response bodies change.** `get_object_or_404` gives Django Ninja's
  `{"detail": "Not Found"}`; the rewrite gives `{"detail": "Image not found"}`.
  Status codes are unchanged, and no test asserts the body on these paths —
  checked: the `detail` assertions in `test_project_images.py` and
  `test_article_images.py` are all on 400s. Frontend impact nil; nothing renders
  a 404 body from these endpoints.
- **No OpenAPI change.** All five endpoints already declare `404: Error`
  (`articles.py:340-346,374`, `my_projects.py:240,271,311`). Run
  `make extract-openapi` anyway and confirm a zero diff — that is cheaper than
  discovering otherwise.
- **`my_projects.py` still takes `image_id: str`.** An id that is not a valid
  UUID reaches `filter(pk=…)` and raises `ValidationError` → 500, exactly as it
  does today via `get_object_or_404`. Changing the annotation to `UUID` fixes it
  and turns it into a 422, but it alters the OpenAPI parameter format and forces
  a `npm run generate-types`. Worth doing; worth doing separately.
- **`update_image_roles` still writes through the ORM in the router**
  (`my_projects.py:300-305`: `project.images.exclude(...).update(...)` and
  `image.save()`). This change moves its *read* into `REPO.images` and leaves the
  write where it is, which is a visible inconsistency in one function. The clean
  version is `HANDLERS.images.set_roles(image, is_main=…, is_hero=…, is_usage=…)`
  — the exclusivity rule ("clear this role from every other image") is business
  logic sitting in a view. Out of scope here; it should be the next commit, and
  until it lands `my_projects.py` cannot be given a guard test.
- **`gallery_prefetch` does not stop anyone writing a bare string prefetch.**
  Nothing can, short of a lint rule. What it does is make the correct form
  shorter than the wrong one, and give it one place to be found.
- **Moving `project_gallery_images` touches eight files.** All import-line edits,
  all caught by `make lint` and the existing suite if wrong. The one to think
  about is `api/schemas/competition.py:71`: a schema reaching for `REPO` at
  module import time risks a cycle. It is inside a `classmethod` body
  (`:65-73`), and `api/schemas/user.py:39` already does a deferred
  `from services import HANDLERS  # noqa: PLC0415` for the same reason — follow
  that pattern rather than adding a module-level import.
