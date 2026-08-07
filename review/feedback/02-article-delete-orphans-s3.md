# 02. Deleting an article orphans its S3 objects irrecoverably

**Finding:** I2 (backend review §11) — `delete_article` does a queryset `.delete()`,
`ProjectImage.article` is `CASCADE`, so rows and their `storage_key`s vanish and
the S3 objects become unreachable.
**Alex:** What do you suggest here?
**Type:** fix proposal
**Effort:** M, one new model + migration, one `pre_delete` receiver, one task,
one management command, and tests. Roughly a day including the sweep-interval
decision. Option (a) below is an hour, but I do not recommend it.

## What is actually happening

`services/articles/django_impl/handler.py:169-172`:

```python
def delete_article(self, article_id: UUID) -> None:
    deleted, _ = Article.objects.filter(pk=article_id).delete()
```

`ProjectImage.article` is `on_delete=CASCADE` (`apps/projects/models.py:238-241`),
and `ImageVariant` cascades from `ProjectImage`. Storage deletion lives only in
`HANDLERS.images.delete_image` (`services/images/django_impl/handler.py:103-123`),
which this path never calls — and a queryset `.delete()` would bypass a model
`delete()` override anyway. `grep -rn "delete_object"` returns exactly two call
sites, both inside that one method.

So: author uploads 8 figures (up to 3 WebP variants each), deletes the draft, and
32 objects stay in the bucket with no row that names them. Not a leak that can be
reconciled later — the keys are gone with the rows.

Two things widen the problem beyond article delete:

1. **`services/project/django_impl/handler.py:171-173`** — `project.delete()` has
   exactly the same shape and orphans the project's entire gallery *and* every
   article image on it.
2. **`useArticleDraft.ts:162`** (finding I4) sweeps "untouched" drafts on unmount
   and `isUntouched` tests `article.images.length === 0`, which inline uploads
   never update. So the leak is not only reached by a deliberate delete — it is
   reached by navigating away mid-upload, which is the common case.

The related known leak, `FOLLOW_UPS.md` item 5, is a different shape: `PENDING`
rows *survive*, holding a key for an object that may or may not exist. That one is
reconcilable because the row is still there. This one is not.

## Proposed change

### Option (a) — delete images through `HANDLERS.images.delete_image` first

```python
def delete_article(self, article_id: UUID) -> None:
    from services import HANDLERS
    for image in ProjectImage.objects.filter(article_id=article_id):
        HANDLERS.images.delete_image(image)
    deleted, _ = Article.objects.filter(pk=article_id).delete()
```

- **Correctness on a mid-way storage failure:** poor. `delete_image` wraps the
  *variant* deletes in `try/except` (`:105-111`) but not the original
  (`:113`), so an S3 error on image 5 of 8 raises out of the loop with 4 images
  already deleted from the database and the article still present. The author sees
  a 500, retries, and the article now has 4 fewer figures than its body references.
- **Transaction safety:** none. Storage deletes are not transactional. Put the
  loop inside `transaction.atomic()` and a later DB failure rolls the rows back
  while the objects are already gone — broken images in a live article, which is
  worse than a leak. Leave it outside and a crash between loop and delete leaves
  rows pointing at deleted objects.
- **Does it fix the `PENDING` leak?** No.
- **Cost:** up to 30 images × 4 synchronous S3 round trips inside a `DELETE`
  request. Same request-path-heavy-work objection as I3.
- **Coverage:** article delete only. `project.delete()` still leaks.

### Option (b) — record the keys, drain them in a worker *(recommended)*

Write the storage keys to a tombstone table as part of the same transaction that
deletes the rows, and have a periodic task delete the objects and clear the
tombstones.

**Model** — `apps/projects/models.py`, next to `ProjectImage`:

```python
class OrphanedStorageObject(models.Model):
    """A storage key whose owning row is gone.

    Written by a `pre_delete` receiver rather than by each delete path, because
    `ProjectImage` rows disappear by cascade from `Article` and `Project` as
    well as by explicit deletion, and a caller that forgets is exactly how the
    keys were lost in the first place.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "orphaned_storage_objects"
        indexes = [models.Index(fields=["attempts", "created_at"])]
```

**Receiver** — `apps/projects/signals.py` (already exists, already wired from
`ProjectsConfig.ready()`, `apps/projects/apps.py:7-10`):

```python
@receiver(pre_delete, sender=ProjectImage)
def record_orphaned_image_object(sender, instance, **kwargs):
    OrphanedStorageObject.objects.get_or_create(storage_key=instance.storage_key)


@receiver(pre_delete, sender=ImageVariant)
def record_orphaned_variant_object(sender, instance, **kwargs):
    OrphanedStorageObject.objects.get_or_create(storage_key=instance.storage_key)
```

The mechanism detail that makes this work: Django's deletion collector normally
"fast-deletes" cascaded rows with a single `DELETE ... WHERE` and no signals, but
it only takes that path when the model has **no** `pre_delete`/`post_delete`
receivers. Registering these receivers disables fast-delete for `ProjectImage` and
`ImageVariant`, so cascades from `Article` *and* from `Project` both fire. This is
worth a comment in the receiver, because someone will later "optimise" it back.

The receivers run inside Django's deletion transaction, so the tombstones and the
row deletions commit or roll back together. That is the property option (a) cannot
have.

**Task** — `api/tasks/images.py`, mirroring the shape already there:

```python
@task()
def sweep_orphaned_storage_objects(batch_size: int = 500) -> None:
    from services import HANDLERS
    HANDLERS.images.sweep_orphaned_objects(batch_size=batch_size)
```

with the implementation on `DjangoImageHandler` alongside `delete_image`: take
`OrphanedStorageObject.objects.order_by("created_at")[:batch_size]`, call
`storage_service.delete_object(key)` per row (S3 `DeleteObject` on a missing key
is a success, so this is idempotent), delete the tombstone on success, and on
failure `attempts += 1` with `last_error` set. Log a count. Rows past some attempt
ceiling stay for inspection rather than being retried forever.

**Schedule** — `apps/projects/management/commands/enqueue_storage_sweep.py`,
following the `enqueue_digest` / `enqueue_notification_cleanup` seam
(`apps/notifications/management/commands/enqueue_notification_cleanup.py`): the
cron names a CLI, not a Python symbol. This needs a CronJob in the infra repo,
same as B1 — worth landing together with that change rather than as a second
infra round trip.

**`delete_article` itself does not change.** That is the point: the fix is in a
place no future delete path can bypass.

### Option (c) — change the FK to `SET_NULL` plus a reaper

Rejected, and on the repo's own stated grounds. `apps/projects/models.py:231-237`
says explicitly:

> CASCADE, not SET_NULL: an unlinked article image is indistinguishable from a
> project one and would surface in the gallery.

`project_gallery_images()` filters `article__isnull=True`, so `SET_NULL` promotes
every deleted article's figures straight into the project's gallery, its cover
candidate pool (`_gallery_queryset`, `services/images/django_impl/handler.py:181-185`)
and its image cap. It converts a storage leak into a visible data corruption. It
would need a second discriminator column to be safe, at which point the model
comment's "there is no separate flag that could disagree with it" stops being
true. Not worth it.

### Recommendation

Option (b). It is the only one where a storage failure is recoverable rather than
either loud-and-partial (a) or silently wrong (c); it is the only one that also
covers `project.delete()`; and it is the only one that keeps the S3 round trips
out of the request path.

**On the `PENDING` leak (`FOLLOW_UPS.md` item 5):** (b) does not fix it by itself
— a `PENDING` row is never deleted, so nothing fires `pre_delete`. But it supplies
the missing half. Once the tombstone drain exists, closing item 5 is a small
addition to the same sweep task: delete `ProjectImage` rows with
`upload_status=PENDING` older than a threshold, which now routes their keys
through the tombstone table by construction. That is worth stating in the change
description so the two are not solved twice.

## Tests

`services/images/django_impl/` — a new `test_orphaned_objects.py`, plus one case in
`services/articles/django_impl/test_handler.py::TestDelete`. All use the existing
factories (`article_image`, `ProjectImageFactory`, `ArticleFactory` in
`tests/factories.py:239,202,214`).

Recording:

```python
def test_deleting_an_article_records_every_image_key(self):
    article = ArticleFactory()
    keys = {article_image(article).storage_key for _ in range(3)}

    DjangoArticleHandler().delete_article(article.id)

    assert set(
        OrphanedStorageObject.objects.values_list("storage_key", flat=True)
    ) == keys
```

Assert the same for variant keys (`ImageVariantFactory` does not exist yet —
create variants directly, as `services/images/django_impl/test_handler.py` already
does for the variant-generation tests), and the same again for
`HANDLERS.project.delete(project.id, owner.id)`, which is the path option (a)
would not have covered.

Draining:

```python
def test_sweep_deletes_the_object_and_clears_the_row(self):
    OrphanedStorageObject.objects.create(storage_key="projects/images/x.jpg")

    with patch("services.storage.storage_service.delete_object") as delete_object:
        DjangoImageHandler().sweep_orphaned_objects()

    delete_object.assert_called_once_with("projects/images/x.jpg")
    assert not OrphanedStorageObject.objects.exists()


def test_sweep_keeps_the_row_and_counts_the_attempt_on_failure(self):
    row = OrphanedStorageObject.objects.create(storage_key="k")

    with patch(
        "services.storage.storage_service.delete_object",
        side_effect=RuntimeError("boom"),
    ):
        DjangoImageHandler().sweep_orphaned_objects()

    row.refresh_from_db()
    assert row.attempts == 1
    assert "boom" in row.last_error
```

The failure case is the one that matters — it is the property option (a) cannot
provide, so it should be the test that documents why the design is what it is.

Also worth adding while in here: the storage-cleanup test the review names as
coverage gap 5, asserting `storage_service.delete_object` is reached for each of a
deleted article's images end-to-end through
`api/routers/test_articles.py::test_owner_can_delete`.

## Risks and what this does not cover

- **New DDL.** One `CREATE TABLE`, additive, no drain window — unlike B2, this can
  ship with the app.
- **Fast-delete regression risk.** The whole mechanism depends on `ProjectImage`
  and `ImageVariant` having a `pre_delete` receiver. If someone later removes the
  receiver, or deletes rows via `_raw_delete()` / raw SQL / a data migration, keys
  are lost silently again. Worth an explicit test that a *cascaded* delete records
  keys, not only a direct one — that is the case fast-delete would break.
- **Unbounded growth if the sweep is never scheduled.** The tombstone table grows
  one row per deleted image forever. The CronJob is a hard dependency, and the
  same infra-repo sequencing problem as B1 applies: nothing in this repo will tell
  you the sweep is not running. A cheap guard is a warning log when the oldest
  tombstone is older than a day.
- **Does not retroactively recover anything.** Objects orphaned before this ships
  stay orphaned; their keys are already gone. If that matters, it is an S3
  inventory diff against `project_images.storage_key`, which is a separate,
  one-off job.
- **Does not address the frontend cause** (I4). The draft sweep will still delete
  drafts out from under an in-flight upload; this change only means the bytes get
  cleaned up when it does.
