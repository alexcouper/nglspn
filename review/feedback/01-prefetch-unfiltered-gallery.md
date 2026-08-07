# 01. Two prefetch sites hand the icon resolver an unfiltered gallery

**Finding:** I1 (backend review §9) — the digest and the notification bell prefetch
`project.images` as a bare string, so `resolve_image_by_purpose` can pick an
article figure or a never-uploaded `PENDING` row as the project icon.
**Alex:** fix this
**Type:** fix proposal
**Effort:** S, three one-line prefetch replacements in one file, two imports, two
new tests. No migration, no API change, no OpenAPI regeneration.

## What is actually happening

`resolve_image_by_purpose` (`services/project/django_impl/query.py:84-105`) does no
filtering. It reads `list(project.images.all())` and falls through
role image → `is_main` → `images[0]` → `None`. Whatever the prefetch put in the
relation is what it picks from. `project_gallery_images()`
(`services/project/django_impl/query.py:37-48`) is the filter, and its docstring
already states the rule: *"Use this for every `Prefetch("images", ...)` on a
project-facing query"*.

Three sites in `services/notifications/django_impl/handler.py` do not:

| Line | Caller | String |
|---|---|---|
| `:328` | `send_article_digest` | `"article__project__images__variants"` |
| `:363` | `list_unread_groups_for_user`, discussion rows | `"discussion__project__images__variants"` |
| `:377` | `list_unread_groups_for_user`, article rows | `"article__project__images__variants"` |

Both consumers then call `REPO.project.get_project_icon_url(project)` —
`services/email/django_impl/handler.py:110` for the digest, and
`services/notifications/django_impl/handler.py:82` (discussion group) and `:119`
(article group) for the bell.

Concretely: project P was created as a tip-off and has no cover. An author
uploads a figure into an article on P, or a gallery PUT fails and leaves a
`PENDING` row at `display_order=0`. That row is `images[0]`. The digest email and
the bell dropdown then render `<img src>` at a `storage_key` that either belongs
to an unrelated article's inline figure or points at an object that was never
written.

`:363` predates the branch. It has the same defect and the same fix, so it goes
in the same change rather than staying as the one remaining example of the wrong
pattern.

## Repo-wide check for other bare `project__images` prefetches

`grep -rn "project__images\|images__variants" --include='*.py'` over
`src/django-backend` returns six hits. Three are the sites above. The other
three are:

- `services/follows/django_impl/query.py:39` — already correct
  (`Prefetch("project__images", queryset=project_gallery_images())`).
- `services/articles/django_impl/query.py:24` and `:39` —
  `.prefetch_related("listing_image__variants", "images__variants")`. This is
  `Article.images`, i.e. the article's *own* uploads, not `project.images`. It
  must **not** be narrowed by `project_gallery_images()` — that queryset filters
  `article__isnull=True`, which would empty the relation. Leave these alone.

Every other `Prefetch` on a project's gallery in the repo already goes through
`project_gallery_images()`: `services/project/django_impl/query.py:54,64,337`,
`api/routers/my_review.py:216`, `api/schemas/competition.py:71`,
`services/review/django_impl/query.py:94`. So the three above are the complete
set.

## Proposed change

One file: `services/notifications/django_impl/handler.py`.

Add the imports at module level. `services/follows/django_impl/query.py:13-17`
already imports from `services.project.django_impl.query` at module level from a
sibling service and is loaded earlier in `services/__init__.py`'s import order,
so this direction is proven to be cycle-free.

```diff
@@ services/notifications/django_impl/handler.py
 from django.utils import timezone
+from django.db.models import Prefetch

 from apps.articles.models import Article, ArticleState
 from apps.discussions.models import Discussion
 from apps.follows.models import FollowedChannel
 from apps.notifications.models import Notification, NotificationCadence
 from services.notifications import (
@@
 from services.notifications.handler_interface import NotificationHandlerInterface
+from services.project.django_impl.query import project_gallery_images
```

Site 1 — `send_article_digest`, `:326-329`:

```diff
             .prefetch_related(
                 "article__listing_image__variants",
-                "article__project__images__variants",
+                # `get_project_icon_url` falls back to `images[0]` with no
+                # filtering of its own, so the prefetch is the only thing
+                # keeping an article figure or a failed upload out of the
+                # project icon.
+                Prefetch(
+                    "article__project__images",
+                    queryset=project_gallery_images(),
+                ),
             )
```

Site 2 — `list_unread_groups_for_user`, discussion rows, `:361-365`:

```diff
         discussion_rows = list(
             REPO.notifications.list_unread_for_user(user_id).prefetch_related(
-                "discussion__project__images__variants"
+                Prefetch(
+                    "discussion__project__images",
+                    queryset=project_gallery_images(),
+                )
             )
         )
```

Site 3 — `list_unread_groups_for_user`, article rows, `:373-380`:

```diff
             REPO.notifications.list_unread_articles_for_user(user_id)
             .select_related("article__listing_image")
             .prefetch_related(
-                "article__project__images__variants",
+                Prefetch(
+                    "article__project__images",
+                    queryset=project_gallery_images(),
+                ),
                 "article__listing_image__variants",
             )
```

`project_gallery_images()` ends in `.prefetch_related("variants")`
(`services/project/django_impl/query.py:47`), so dropping the `__variants` tail
from the string loses nothing — `variant_url` still reads a prefetched relation
and the query count is unchanged.

This is the mechanical fix. The structural fix that stops it recurring is
architecture point 2 (`REPO.images`) — a named repository method is harder to
bypass than a convention in a docstring. That is a separate document; this one
should not wait for it.

## Tests

Two, both filling gaps the review already named (backend review, test coverage
gaps 3).

**1. Digest** — `services/email/django_impl/test_handler.py`, in
`TestArticleDigestExcerpt`'s file next to the existing `_article_notification`
helper. Every current fixture gives the article a `listing_image`, so
`_digest_article_image_url`'s fallback branch
(`services/email/django_impl/handler.py:110`) is never entered.

```python
def test_project_icon_fallback_ignores_article_uploads(self):
    project = ProjectFactory()
    other_article = ArticleFactory(project=project)
    article_image(other_article)            # first row on the project
    article = PublishedArticleFactory(project=project)   # no listing image
    NotificationFactory(
        recipient=UserFactory(), discussion=None, article=article,
        email_cadence=NotificationCadence.HOURLY,
    )

    handler.send_article_digest("hourly")

    entry = build_article_digest_entries([...])[0]
    assert entry["article_image_url"] is None
```

Simplest assertion that pins the defect: `article_image_url is None`, because the
project has no gallery image at all and the only candidate is an article figure.
A second case with `ProjectImageFactory(project=project, upload_status="pending")`
asserts the same for the `PENDING` row. These mirror
`services/follows/django_impl/test_query.py:130-148`
(`test_ignores_images_uploaded_for_an_article`,
`test_ignores_an_upload_that_never_completed`), which is the shape that already
guards the Following page.

**2. Bell** — `api/routers/test_notifications.py`, in
`TestGroupsEndpointArticleKind`:

```python
def test_project_icon_ignores_article_uploads(self, client, user, auth_headers):
    project = ProjectFactory()
    article_image(ArticleFactory(project=project))
    article = PublishedArticleFactory(project=project)
    NotificationFactory(recipient=user, discussion=None, article=article)

    response = client.get("/api/notifications/groups", **auth_headers)

    assert_that(response.json()[0]["project"]["image_url"], equal_to(None))
```

`article_image` and `ProjectImageFactory` are both already in
`tests/factories.py` (`:239`, `:202`).

Without the fix both tests fail with a URL instead of `None`, which is the exact
production symptom.

## Risks and what this does not cover

- `Prefetch` with a custom queryset cannot be combined with a second prefetch of
  the same relation on the same queryset. None of the three sites does that, so
  there is nothing to reconcile.
- Query counts are unchanged (three lookups become three narrower lookups), so
  no existing query-count assertion moves.
- This narrows the prefetch only. `resolve_image_by_purpose` still has no filter
  of its own, so any *future* caller that hands it an unfiltered relation
  reintroduces the bug. The belt-and-braces pattern that
  `ProjectResponse.resolve_images` uses (`api/schemas/project.py:104-111` —
  filter again in Python) is not applied here and is not proposed here;
  `REPO.images` is the better answer.
- Does not touch `services/articles/django_impl/query.py`, where
  `"images__variants"` is correct.
