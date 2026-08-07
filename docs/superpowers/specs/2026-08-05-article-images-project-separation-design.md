# Article Images vs Project Images — Design

Date: 2026-08-05
Status: design (pre-implementation)

## Summary

Images uploaded from the article editor currently appear in the project's public
image gallery. They should not — project images describe the project, article
images belong to the article that used them.

Add `ProjectImage.source` (`project` | `article`), set it at upload time, and
exclude article-sourced images from every project-facing read path, from the
per-project image cap, and from automatic main-image promotion.

Backend and frontend. One migration, and OpenAPI regeneration because both
`PresignedUploadRequest` and `ArticleResponse` change.

## Root cause

The article editor's inline image button and its hero uploader both call
`uploadProjectImage()` (`src/web-ui/src/lib/uploadProjectImage.ts:29`), which
posts to `/api/my/projects/{id}/images/upload-url` and creates a plain
`ProjectImage` row (`src/django-backend/api/routers/my_projects.py:255`). Nothing
on that row records where the upload came from.

The project page then renders the lot: `ProjectResponse.resolve_images` returns
`obj.images.all()` (`src/django-backend/api/schemas/project.py:106`) and
`ProjectDetailContent` shows every non-icon image
(`src/web-ui/src/app/projects/[slug]/ProjectDetailContent.tsx:35-41`).

Two further consequences of the same missing distinction:

- `/complete` promotes the first image on a project with no main image to
  `is_main=True` (`my_projects.py:311-316`). An article image can therefore
  become the project's card and listing image, and can satisfy the `main_image`
  publish precondition (`services/project/django_impl/handler.py:238`).
- Article images count against `MAX_IMAGES_PER_PROJECT`, so writing a few
  articles can lock an owner out of adding genuine project images.

## Data model

`apps/projects/models.py`, alongside the existing `UploadStatus`:

```python
class ImageSource(models.TextChoices):
    PROJECT = "project", "Project"
    ARTICLE = "article", "Article"
```

On `ProjectImage`:

```python
source = models.CharField(
    max_length=20,
    choices=ImageSource.choices,
    default=ImageSource.PROJECT,
    db_index=True,
)
```

`TextChoices` is already str-based, matching the other sixteen choices classes in
the backend.

Indexed because every project-facing query gains an `exclude(source=ARTICLE)`.

**No backfill.** The migration adds the column with `default="project"`, so every
existing row — including article images uploaded before this change — stays
visible in project galleries. Owners clean those up by hand. A body-URL scan to
retro-classify them was considered and rejected: it would mis-flag any image
deliberately used in both places.

## Write path — `api/routers/my_projects.py`

- `PresignedUploadRequest` (`api/schemas/project.py:119`) gains
  `source: str = "project"`. `get_upload_url` validates it against
  `ImageSource.values` and returns 400 on anything else, mirroring the existing
  content-type validation, then stores it on the new row.
- The image-count check (line 242) additionally excludes article-sourced images.
  Article images are **uncapped**, following the precedent that icons are
  excluded from the cap rather than inventing a second limit.
- `/complete`'s main-image promotion (lines 311-316) skips article-sourced
  images. An article upload can then never become the project's card image nor
  satisfy the `main_image` publish precondition.

`display_order` for article images is left as-is — it is meaningless for them,
but harmless, and not worth a branch.

## Read path

Five call sites repeat the same prefetch:

- `services/project/django_impl/query.py:42` (discover)
- `services/project/django_impl/query.py:57` (project detail and lists)
- `services/project/django_impl/query.py:335` (competition winners)
- `api/routers/my_review.py:262` (review queue)
- `api/schemas/competition.py:73` (competition project lists)

Extract them into one helper in `services/project/django_impl/query.py`:

```python
def project_gallery_images() -> QuerySet[ProjectImage]:
    """Images that describe the project itself — excludes article uploads."""
    return (
        ProjectImage.objects.filter(upload_status=UploadStatus.UPLOADED)
        .exclude(source=ImageSource.ARTICLE)
        .prefetch_related("variants")
    )
```

and use it in all five `Prefetch("images", ...)` clauses. That single change
covers project detail, discover, project listings, competitions and the review
queue.

`ProjectResponse.resolve_images` (`api/schemas/project.py:106`) also filters
explicitly, since the schema can be reached with an unfiltered prefetch and
should not depend on its caller's queryset.

`resolve_image_by_purpose` and `to_list_item`
(`services/project/django_impl/query.py:80,128`) both fall back to `images[0]`.
They read from the prefetched relation, so the helper covers them — no change of
their own.

## Article hero

Excluding article images from `project.images` breaks the editor's hero lookup:
`useArticleDraft.ts:77` finds the hero by searching `project.images` for
`loaded.hero_image_id`. After this change that search returns nothing and the
hero preview vanishes when editing an existing article.

Fix at the source. `ArticleResponse` (`api/schemas/article.py:54-57`) exposes
only `hero_image_url` — a bare URL with no variants. Add:

```python
hero_image: ProjectImageResponse | None
```

resolved from `obj.hero_image`. `articles/django_impl/query.py` already
`select_related("hero_image")`; add `prefetch_related("hero_image__variants")`
so the variants do not become an N+1.

`hero_image_url` stays — `ArticleListItem` and the public article page use it,
and it is the cheaper field for list responses.

`useArticleDraft` then reads `loaded.hero_image` directly and drops
`project.images` from its dependency array.

## Frontend

- `uploadProjectImage` (`src/lib/uploadProjectImage.ts`): `UploadOptions` gains
  `source?: "project" | "article"`, defaulting to `"project"`, passed through to
  `getImageUploadUrl`. `MyProjectsClient.getImageUploadUrl` takes it as a
  parameter and puts it in the body.
- `useImageUpload` (`src/hooks/useImageUpload.ts`) accepts `source` in its
  options and forwards it.
- Two call sites pass `"article"`: `useImageUploadStatus.ts:27` (inline body
  images) and the `useImageUpload` call in `ArticleAuthoringPage.tsx:45` (hero).
- Every project-side call site is unchanged — the default covers them.

Regenerate types after the backend lands: `make extract-openapi` in
`src/django-backend/`, then `npm run generate-types` in `src/web-ui/`.

## Testing

Backend (`api/routers/test_project_images.py`, `test_articles.py`):

- An article-sourced upload does not appear in `ProjectResponse.images`.
- An article-sourced upload is not promoted to `is_main` on a project with no
  main image, and does not satisfy the `main_image` publish precondition.
- Article-sourced images do not count toward `MAX_IMAGES_PER_PROJECT` — a
  project at the cap can still take an article upload, and a project with ten
  article images can still take a project image.
- `source` outside the choices returns 400.
- `ArticleResponse.hero_image` serialises with variants.
- A project-sourced upload still behaves exactly as before (regression guard on
  the default).

`ProjectImageFactory` (`tests/factories.py:202`) needs no change — it does not
declare `source`, so the model default applies and tests pass
`source=ImageSource.ARTICLE` through as a kwarg.

Frontend:

- The hero image renders when editing an existing article, with `project.images`
  empty — proving the lookup no longer depends on it.
- Inline and hero uploads from the article editor send `source: "article"`;
  the project image manager sends `"project"`.

E2E (`e2e/article-images.spec.ts`, `e2e/article-hero-removal.spec.ts`): both
specs clean up by finding their uploads in `project.images`, which this change
makes invisible. They record the `image_id` the backend returns from
`/images/upload-url` instead. `article-images.spec.ts` also gains a case
asserting an inserted image never reaches the project's gallery — matched on id,
not filename, because a pre-fix upload of the same fixture can legitimately
still be there.

## Out of scope

Deleting an article leaves its images orphaned in S3 with no UI to reach them.
This change makes that slightly worse, since those images are now invisible in
the project gallery too. Tracked separately — not bundled here.
