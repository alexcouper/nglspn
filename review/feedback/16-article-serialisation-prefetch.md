# 16. `PATCH` and `publish` serialise off a queryset with no image prefetch

**Finding:** Minor / backend review §14 — `_get_article` prefetches only
`listing_image__variants`, so every *Save draft* costs 1 + N extra queries to
serialise `ArticleOut.images`.
**Alex:** What do you suggest?
**Type:** fix proposal
**Effort:** S, extract one queryset helper, change one method to use it, one
optional in-memory pick, one test. Half a day with the test.

## What is actually happening

`services/articles/django_impl/handler.py:353-361`:

```python
def _get_article(self, article_id: UUID) -> Article:
    return (
        Article.objects.select_related("project", "channel", "author", "listing_image")
        .prefetch_related("listing_image__variants")
        .get(pk=article_id)
    )
```

That instance is what `update_article` (`:137`) and `publish` (`:167`) return, and
what `api/routers/articles.py:216` and `:245` hand back as `ArticleOut`.

`ArticleOut.resolve_images` (`api/schemas/article.py:148-159`) calls
`obj.images.all()` — one query, unprefetched — and each element is serialised as
`ProjectImageResponse`, whose `resolve_variants` (`api/schemas/project.py:54-56`)
calls `obj.variants.all()` — one query each. At 12 figures that is 13 avoidable
queries per save, growing linearly toward the 30-image article cap
(`services/images/handler_interface.py:16`).

**The right prefetch set already exists**, twice, in the query service:

`services/articles/django_impl/query.py:18-27` and `:29-42` —
`DjangoArticleQuery.get_by_id` and `get_by_project_and_slug` both do

```python
.select_related("project", "channel", "author", "listing_image")
# `images` is the listing-image wizard's selection list on ArticleOut.
.prefetch_related("listing_image__variants", "images__variants")
```

verbatim. So the list is already duplicated between the two query methods, and
the handler is a third, divergent copy. Three places, two behaviours.

Worth noting while here: `api/routers/articles.py:192` and `:234` *already* load a
fully-prefetched article through `_get_article_in_project` →
`REPO.articles.get_by_id`, then throw it away and return the handler's version.
The correct instance is fetched and discarded on every save.

## Proposed change

### Option 1 — add `"images__variants"` to `_get_article`

One word. Leaves three copies of the prefetch list, which is how this happened.
Rejected.

### Option 2 — extract one queryset builder in `query.py`, use it from all three *(recommended)*

`services/articles/django_impl/query.py`:

```python
def article_detail_queryset() -> QuerySet[Article]:
    """Everything `ArticleOut` reads, in four queries.

    `images` is the listing-image wizard's selection list on `ArticleOut`, and
    each of those serialises its variants — so an article with N figures costs
    1 + N queries to serialise without this. Used by the read path and by the
    write handler's re-read, because `PATCH` and `publish` return `ArticleOut`
    too and a second prefetch list would drift from this one.
    """
    return Article.objects.select_related(
        "project", "channel", "author", "listing_image"
    ).prefetch_related("listing_image__variants", "images__variants")


class DjangoArticleQuery(ArticleQueryInterface):
    def get_by_id(self, article_id: UUID) -> Article | None:
        return article_detail_queryset().filter(pk=article_id).first()

    def get_by_project_and_slug(self, project_slug: str, article_slug: str) -> Article | None:
        return (
            article_detail_queryset()
            .filter(project__slug=project_slug, slug=article_slug)
            .first()
        )
```

`services/articles/django_impl/handler.py`:

```diff
+from services.articles.django_impl.query import article_detail_queryset
@@
     def _get_article(self, article_id: UUID) -> Article:
         try:
-            return (
-                Article.objects.select_related(
-                    "project", "channel", "author", "listing_image"
-                )
-                .prefetch_related("listing_image__variants")
-                .get(pk=article_id)
-            )
+            return article_detail_queryset().get(pk=article_id)
         except Article.DoesNotExist as exc:
             raise ArticleNotFoundError from exc
```

Same package, so no layering violation — `services/articles/django_impl/__init__.py`
already imports both modules.

### Option 3 — re-read through `REPO.articles.get_by_id` in the router before returning

Costs an extra full round trip per save on top of what the router already threw
away, and leaves `_get_article` under-prefetched for every other caller. Rejected.

### One honest caveat on the arithmetic

`_apply_listing_image` in `auto` mode (`handler.py:267-271`) does

```python
image = article.images.uploaded().order_by("created_at").first()
```

A filtered queryset on a related manager **discards the prefetch** and issues a
fresh query, so this one stays regardless. Adding `images__variants` to
`_get_article` costs 2 extra queries on the read (one for images, one for
variants) and saves 1 + N on the serialisation. At 12 figures: −13 +2 = −11 net.
At 0 figures: +2. The cross-over is 2 images.

If you want the `auto` path's query too, it is the same rule
`ArticleOut.resolve_images` already applies in Python
(`api/schemas/article.py:155-159`) and would read off the prefetch:

```diff
-            image = article.images.uploaded().order_by("created_at").first()
+            # Read off the prefetch: `.uploaded()` on the related manager would
+            # issue a fresh query and throw it away. Same filter+sort as
+            # `ArticleOut.resolve_images`, so the wizard's list and `auto`'s
+            # pick stay in the same order.
+            image = next(
+                iter(sorted(
+                    (i for i in article.images.all() if i.is_uploaded),
+                    key=lambda i: i.created_at,
+                )),
+                None,
+            )
```

`is_uploaded` is the documented in-memory twin of `.uploaded()`
(`apps/projects/models.py:281-288`). This makes the change net-negative at every
image count. Recommended, but it is a behaviour-adjacent edit to the densest
method on the branch (`_apply_listing_image`, backend review §5) and the listing-
image state machine has 12 tests over it — so land it as a separate commit that
can be reverted on its own.

`create_article` (`api/routers/articles.py:81-90`) is a related but distinct case:
it serialises a bare `Article(...)` instance, so `project`, `author` and `images`
are each a fresh query. Not fixed by this change — it never goes through
`_get_article`. Out of scope, worth a note.

## Tests

The repo has two existing patterns. The Following-page scaling test
(`services/follows/django_impl/test_query.py:99-112`) asserts *invariance* rather
than an absolute number:

```python
def _count_queries(work: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as queries:
        work()
    return len(queries)


class TestListUserFollowsQueryCount:
    def test_does_not_query_per_followed_project(self):
        ...
        assert four_follows == one_follow
```

`django_assert_num_queries` also appears, in
`services/review/django_impl/test_query.py:267-289`, but pinned to `0`.

Use the invariance form — it fails on the actual defect (linear growth) and does
not need re-baselining when an unrelated query is added elsewhere. New class in
`services/articles/django_impl/test_handler.py`:

```python
def _article_with_figures(count: int) -> Article:
    article = ArticleFactory()
    for _ in range(count):
        article_image(article)
    return article


def _save_and_serialise(handler, article_id) -> None:
    article = handler.update_article(article_id, title="Edited")
    ArticleOut.from_orm(article)


@pytest.mark.django_db
class TestSaveDraftQueryCount:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_does_not_query_per_article_figure(self):
        one = _article_with_figures(1)
        twelve = _article_with_figures(12)

        one_figure = _count_queries(lambda: _save_and_serialise(self.handler, one.id))
        twelve_figures = _count_queries(
            lambda: _save_and_serialise(self.handler, twelve.id)
        )

        assert twelve_figures == one_figure
```

The `ArticleOut.from_orm(article)` call is the load-bearing part — the cost is in
serialisation, not in the handler, so a test that only counts `update_article`
would pass today and prove nothing. `article_image` is already in
`tests/factories.py:239`; lift `_count_queries` into a shared test helper rather
than copying it a second time.

Without the fix: 11 extra queries at 12 figures, so the assertion fails with
something like `24 != 13`. With option 2 alone it passes. With the
`_apply_listing_image` change as well it also passes and both numbers drop.

## Risks and what this does not cover

- **`article_detail_queryset()` becomes load-bearing for two paths at once.**
  Anyone tightening it for the read path now also changes what the write path
  returns. That is the intent, but it should be said in the docstring — it is
  written above.
- **Prefetch on a `.get()` is 3 queries where it was 1.** On an article with no
  figures every save gets 2 queries more expensive. Acceptable; the 30-image cap
  is where the risk is.
- **`api/routers/articles.py:192` and `:234` still fetch and discard a
  fully-prefetched article.** Removing that duplication means restructuring
  `_get_article_in_project` to hand its instance to the handler, which changes the
  handler signatures. Not proposed here — it is a bigger change than the query
  saving justifies.
- **No API shape change**, no migration, no OpenAPI regeneration.
- **Does not cover `create_article`**, which serialises an unsaved-relation
  instance and is the worse case per call, though it happens once per article
  rather than once per keystroke-batch.
