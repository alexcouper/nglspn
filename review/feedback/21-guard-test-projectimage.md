# 21. The router ORM guard test omits the model the router actually queries

**Finding:** Minor — `api/routers/test_articles.py:902` enumerates `Article` /
`Channel` / `FollowedChannel` but not `ProjectImage`, which is the model
`articles.py:292` hand-queries.
**Alex:** "what do you suggest?"
**Type:** fix proposal
**Effort:** S — five lines in two test files. Sequencing matters more than the
edit: as written below it fails until `11-repo-images.md` lands.

## What is actually happening

```python
@pytest.mark.django_db
class TestRouterHasNoOrmAccess:
    """Spec invariant — `api/routers/articles.py` SHALL NOT reference
    `Article.objects`, `Channel.objects`, or `FollowedChannel.objects`
    directly. All DB access goes through HANDLERS / REPO.
    """

    def test_no_orm_imports(self) -> None:
        src = Path(__file__).resolve().parent.parent / "routers" / "articles.py"
        text = src.read_text()
        for forbidden in (
            "Article.objects",
            "Channel.objects",
            "FollowedChannel.objects",
        ):
            assert forbidden not in text, (
                f"{forbidden} must not appear in api/routers/articles.py"
            )
```

It reads the router's source as text and asserts three substrings are absent.
Not imports, despite the method name — `from apps.articles.models import Article`
would pass. It is a check on the *manager access spelling*, nothing more.

A near-identical copy guards `channels.py` at `api/routers/test_channels.py:334-346`.

### Why `ProjectImage` was omitted

Not because the code would fail it. **Adding `"ProjectImage.objects"` to the
list would pass today, unchanged, and would keep passing after the images
refactor — it is a no-op.** The string never appears in `articles.py`. The
router's ORM access is spelled differently:

- `api/routers/articles.py:29` — `from apps.projects.models import Project, ProjectImage, UploadStatus`
- `api/routers/articles.py:292` — `get_object_or_404(ProjectImage, id=image_id, article=article, **filters)`

`get_object_or_404` takes the model class and reaches `_default_manager` itself,
so no `.objects` is written. The guard's shape cannot see it. That is the actual
defect: the test does not assert what its docstring claims ("All DB access goes
through HANDLERS / REPO"), it asserts one of several ways of writing DB access.

So the honest answer to "was it deliberate?" is: it does not matter which, because
the obvious extension would not have caught anything either way. The backend
review's own suggested direction — "extend the string list to `ProjectImage`" —
rests on that wrong premise.

### Why the bare name cannot simply be banned

`ProjectImage` must stay importable in `articles.py` after the refactor: it is the
return annotation on `_get_article_image_or_404` and on
`complete_article_image_upload` (`:356`). Annotating a Django model in a router
signature is not ORM access — every router in this codebase does it. A guard on
the bare token `ProjectImage` would be wrong in principle and unsatisfiable in
practice.

## Proposed change

Ban the two spellings that *are* database access, and say so in the docstring.

**`api/routers/test_articles.py:895-912`:**

```diff
 @pytest.mark.django_db
 class TestRouterHasNoOrmAccess:
-    """Spec invariant — `api/routers/articles.py` SHALL NOT reference
-    `Article.objects`, `Channel.objects`, or `FollowedChannel.objects`
-    directly. All DB access goes through HANDLERS / REPO.
-    """
+    """Spec invariant — `api/routers/articles.py` SHALL NOT reach the database
+    directly. All DB access goes through HANDLERS / REPO.
+
+    Two spellings, because banning `<Model>.objects` alone misses the one the
+    file actually used: `get_object_or_404(ProjectImage, ...)` takes the model
+    class and reaches `_default_manager` itself, writing no `.objects` at all.
+    Model names are not banned — they are legitimate return annotations.
+    """
 
     def test_no_orm_imports(self) -> None:
         src = Path(__file__).resolve().parent.parent / "routers" / "articles.py"
         text = src.read_text()
         for forbidden in (
             "Article.objects",
             "Channel.objects",
             "FollowedChannel.objects",
+            "ProjectImage.objects",
+            "get_object_or_404",
         ):
             assert forbidden not in text, (
                 f"{forbidden} must not appear in api/routers/articles.py"
             )
```

`"ProjectImage.objects"` is kept even though it is vacuous today: it costs
nothing and it is the spelling someone will reach for next.

Rename `test_no_orm_imports` → `test_no_direct_orm_access` while there. The
current name says imports and the test has never checked imports.

The `@pytest.mark.django_db` marker on the class is dead — the test reads a file
and touches no database. Harmless, but it charges a transaction per run. Drop it
if you are touching the class anyway; the same applies to `test_channels.py:333`.

**`api/routers/test_channels.py:337-346`** — apply the same two additions.
`channels.py` has no `get_object_or_404` and no `ProjectImage` (verified), so it
passes immediately. Worth doing so the two copies of this guard do not drift; the
long-term answer is one parametrised test over a list of router files, which is
the right shape once a third router earns a guard.

## Does this have to land with `11-repo-images.md`?

**Yes, for the `get_object_or_404` line.** `api/routers/articles.py:5` imports it
and `:292` calls it, so the assertion fails on the current tree. Landing this
test alone turns CI red.

Three ways to sequence it, in preference order:

1. **Same change, test first.** Write the guard extension as the first commit of
   the `REPO.images` work and watch it fail, then make it pass by removing the
   `get_object_or_404` call. This is the repo's stated TDD preference and the
   test is genuinely the specification of the refactor.
2. **Same change, test last.** Works; loses the demonstration that the guard bites.
3. **Separately, `ProjectImage.objects` only.** Lands today, green, and asserts
   nothing. Not worth a commit.

`test_channels.py` has no such constraint and can go whenever.

## Tests

The change *is* a test. Verification is two commands:

```bash
cd src/django-backend && uv run pytest api/routers/test_articles.py::TestRouterHasNoOrmAccess
```

Expect a failure on `get_object_or_404` before the images refactor and a pass
after. Then the same for `test_channels.py::TestRouterHasNoOrmAccess`, which
should pass at both points.

## Risks and what this does not cover

- **It is still a substring scan.** `from django.shortcuts import get_object_or_404 as fetch`
  defeats it, as does `ProjectImage._default_manager`, `Article.objects` written
  through a local alias, or any `select_related` chain off a model handed in. It
  raises the cost of the mistake; it does not make it impossible. Say that in the
  docstring rather than letting the next reader over-trust it.
- **`get_object_or_404` is banned by name, not by argument.** If `articles.py`
  ever legitimately needs it for something that is not a model — it will not —
  the guard is wrong. Acceptable.
- **`my_projects.py` gets no guard.** It cannot: `_get_editable_project_or_404`
  (`:38-42`) uses `get_object_or_404(Project, …)` and `update_image_roles`
  (`:300-305`) writes through `project.images…update()` and `image.save()`. Both
  are noted in `11-repo-images.md` as follow-on work. When they are gone,
  `my_projects.py` is the third file that wants this guard and the point at which
  the three copies should collapse into one parametrised test.
- **The docstring says "SHALL NOT", implying a spec.** If there is an openspec
  requirement behind it, the wording change here should be reflected there too;
  I have not gone looking for it.
