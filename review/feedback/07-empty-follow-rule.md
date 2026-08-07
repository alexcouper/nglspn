# 07. The "an empty Follow is deleted" rule holds in only one place

**Finding:** I7 (backend review §10) — `unfollow_channel` is the sole enforcer of
"a Follow with no followed channels is deleted", and several paths produce that
state without going through it.
**Alex:** "Great point. Suggest some fixes."
**Type:** fix proposal
**Effort:** M — four small edits (query, handler, interface, one caller), one
new handler method, one optional data migration, and roughly six tests. No
schema change. One existing test's *name* becomes slightly wrong and needs
re-reading, not rewriting.

## What is actually happening

### (a) Every path that can empty a Follow

`FollowedChannel.channel` is `CASCADE` (`apps/follows/models.py:57-60`) and
`FollowedChannel.follow` is `CASCADE` (`:52-56`). Deleting a `Channel` therefore
removes rows out from under a `Follow` that nothing then re-examines.

1. **Channel deletion through the API.** `api/routers/channels.py:120-144` →
   `services/articles/django_impl/handler.py:209-223`. The endpoint refuses only
   two things: a channel with articles, and the last channel on a project. A
   project with channels A and B, where user U follows only A, loses U's single
   `FollowedChannel` when the owner reassigns A's articles to B and deletes A.
   No concurrency involved. This is the common case.
2. **Channel deletion through the Django admin.** `Channel` and
   `FollowedChannel` are both registered (`apps/follows/admin.py:6-10`, `:21-25`),
   so a staff user can delete either directly, bypassing `delete_channel`
   entirely. This matters for the choice of fix below: any solution that lives
   only in the service layer has a hole a `ModelAdmin` can walk through.
3. **The `unfollow_channel` race.** `services/follows/django_impl/handler.py:69-74`.
   Under READ COMMITTED, two concurrent `DELETE`s each see the other's row as
   still present at `:72`, so neither takes the `follow.delete()` branch. The
   `transaction.atomic()` at `:69` does nothing here — there is no lock on the
   `Follow` row.
4. **Historical rows from `follows/0004`.**
   `apps/follows/migrations/0004_sweep_both_off_rows.py:42` deletes every
   `FollowedChannel` with `email_enabled=False` and deliberately leaves the
   `Follow` rows (`:31-39`). Whatever the code does from now on, these rows are
   in the production database the moment the migration runs.
5. **A follow on a channel-less project** (marginal).
   `handler.py:26` enrols `Channel.objects.filter(project=project)`; if that is
   empty the `Follow` is born childless. Not reachable through the API — the
   `post_save` receiver at `apps/projects/signals.py:18-31` gives every project
   an "Updates" channel and `delete_channel` refuses the last one — but a
   `Project.objects.bulk_create` in a fixture or a shell session skips the
   signal.

### The consequence is confined to three read sites

Worth being precise about, because it decides where the fix belongs. Everything
that *acts* on a follow already keys on `FollowedChannel`, not `Follow`:

- `create_notifications_for_article` selects `FollowedChannel`
  (`services/notifications/django_impl/handler.py:200-207`), so a childless
  Follow already receives nothing. Correctly.
- The digest is driven off `Notification` rows, so likewise.

Only three reads still key on `Follow` existence:

- `DjangoFollowQuery.is_followed` (`services/follows/django_impl/query.py:69-72`),
  consumed by `api/routers/projects.py:181` and `api/routers/my_review.py:225`
  to fill `ProjectResponse.is_followed` — the project page's Follow button.
- `DjangoFollowQuery.get_state` (`:74-80`).
- `_follow_queryset` (`:20-41`), behind `list_user_follows` and
  `get_follow_preferences` — the Following page.

So the database is already, semantically, "not following". The three reads are
what lie about it.

### (c) Why recovery is trapped

`follow()` enrols channels only when `get_or_create` reports `created=True`
(`handler.py:25`). For a childless Follow, `created` is `False`, so pressing
"Follow" writes nothing and returns `is_followed=True` — a button that appears to
work and does nothing.

The comment at `:18-20` is not wrong, it is just scoped to a case that no longer
covers the field: "Re-following does not enrol channels added after the original
follow — that's the user's choice to make via `follow_channel()`". That reasoning
protects a *deliberate* untick. When there are zero rows there is no untick to
protect. The two situations are distinguishable in one predicate, so the rule
does not have to be given up to make recovery work.

Note the one recovery path that does work today: `follow_channel` only requires
the `Follow` to exist (`_resolve`, `:47-50`), so ticking a channel on the
Following page repopulates it. It is undiscoverable — the page shows the project
as followed with nothing ticked — but it must keep working, which rules out
making `_resolve` reject childless Follows.

## Proposed change

### Option 1 — Make the read path authoritative, and make `follow()` recover

`is_followed` / `get_state` / `_follow_queryset` require at least one
`FollowedChannel`. `follow()` enrols when the Follow has no channels.

Covers 1, 2, 3, 4 and 5 in one place, because it never asks how the state arose.
Race-proof by construction. No migration. Childless rows accumulate in the table
but are invisible and inert.

### Option 2 — Enforce the invariant on every write path

`select_for_update()` on the `Follow` in `unfollow_channel` (kills 3), a
`post_delete` receiver on `Channel` or a hook in `delete_channel` (kills 1, and 2
only if it is a signal), and a data migration (kills 4).

Loses on three counts. It needs the data migration that Option 1 does not. The
lock cannot be tested: the suite runs on SQLite (`project_showcase/settings.py:116-122`
defaults to SQLite and CI sets no `DATABASE_URL`, `.github/workflows/ci.yml:8-19`),
where Django's compiler emits no `FOR UPDATE` at all, so the fix is unverifiable
in CI and only exercised in production. And it leaves the invariant one new
write path away from being false again, with the read side still trusting it
absolutely.

### Option 3 — Option 1, plus the cheap half of Option 2 — **recommended**

Read path decides; `follow()` recovers; `delete_channel` prunes the Follows it
emptied; an optional one-off cleanup migration for the `0004` rows.

Correctness comes entirely from the read path, so nothing depends on the pruning
being exhaustive — which is what makes the admin hole (2) and the race (3)
acceptable rather than outstanding. The pruning is there so the table does not
silently grow a population of dead rows, and so `/following` does not need a
second filter later. Skip `select_for_update` — it buys nothing once the read
path is correct, and it cannot be tested here.

### Option 4 — A `Follow.is_effective` property

Rejected. A Python property cannot appear in a `filter()`, so `is_followed`
(`query.py:72`) and `_follow_queryset` (`:30-41`) — the three sites that are
actually wrong — cannot use it. It would only serve in-memory callers, of which
there are none. It adds a second statement of the rule beside the query one.

### Option 5 — Drop the rule; a childless Follow is a legitimate state

`unfollow_channel` stops deleting the `Follow`; the UI shows "following, no
channels selected". Superficially the simplest, and it does make the model
honest.

Rejected. It does not fix the `0004` cohort — it relabels them: those users still
show as following and still receive nothing, which is the complaint. It also
requires frontend work (`useChannelToggle.ts:53` keys `onProjectUnfollowed` off
`is_followed === false`) and changes a documented behaviour
(`handler_interface.py:38-45`) for no gain in the failing case.

---

### The edits (Option 3)

**1. `services/follows/django_impl/query.py` — the read path**

```diff
-from django.db.models import Prefetch, QuerySet
+from django.db.models import Count, Prefetch, QuerySet
```

```diff
+def _effective(follows: QuerySet[Follow]) -> QuerySet[Follow]:
+    """Follows that notify about something.
+
+    A Follow with no FollowedChannel rows sends nothing: the article fan-out
+    selects FollowedChannel, not Follow. Channel deletion cascades those rows
+    away and `follows/0004` left emptied Follows behind on purpose, so the
+    state exists in the database whatever the write paths do. This is where it
+    stops being visible. Counted rather than joined so the prefetches on
+    `_follow_queryset` are not duplicated per channel.
+    """
+    return follows.annotate(channel_count=Count("followed_channels")).filter(
+        channel_count__gt=0
+    )
+
+
 def _follow_queryset(user_id: UUID) -> QuerySet[Follow]:
```

```diff
-    return (
+    return _effective(
         Follow.objects.filter(user_id=user_id)
         .select_related("project")
         .prefetch_related(
             "followed_channels",
             Prefetch(
                 "project__channels",
                 queryset=Channel.objects.order_by("created_at"),
             ),
             Prefetch("project__images", queryset=project_gallery_images()),
         )
     )
```

```diff
     def is_followed(self, user_id: UUID | None, project: Project) -> bool:
         if user_id is None:
             return False
-        return Follow.objects.filter(user_id=user_id, project=project).exists()
+        return Follow.objects.filter(
+            user_id=user_id, project=project, followed_channels__isnull=False
+        ).exists()
 
     def get_state(self, user_id: UUID | None, project: Project) -> FollowState:
         if user_id is None:
             return FollowState(is_followed=False)
-        follow = Follow.objects.filter(user_id=user_id, project=project).first()
+        follow = _effective(
+            Follow.objects.filter(user_id=user_id, project=project)
+        ).first()
```

`is_followed` uses the join form rather than `_effective` deliberately:
`EXISTS` over a join is one query with no aggregate, and duplicate rows are
irrelevant to `.exists()`.

**2. `services/follows/django_impl/handler.py` — recovery**

```diff
     def follow(self, user_id: UUID, project: Project) -> FollowState:
         # First follow auto-enrols every current channel. Re-following does
         # not enrol channels added after the original follow — that's the
-        # user's choice to make via follow_channel().
+        # user's choice to make via follow_channel(). A Follow with no
+        # channels at all is the exception: there is no choice there to
+        # preserve, and it is reachable without the user doing anything (the
+        # owner deletes the last channel they followed). Without this branch,
+        # "Follow" is a button that writes nothing on a project the reader is
+        # told they do not follow.
         with transaction.atomic():
             follow, created = Follow.objects.get_or_create(
                 user_id=user_id, project=project
             )
-            if created:
+            if created or not follow.followed_channels.exists():
                 for channel in Channel.objects.filter(project=project):
                     FollowedChannel.objects.get_or_create(
                         follow=follow,
                         channel=channel,
                     )
         return FollowState(is_followed=True, created_at=follow.created_at)
```

This is the answer to Alex's (c): re-following enrols **only when there is
nothing to preserve**. It does not enrol channels added since, so the documented
behaviour and its test (`test_handler.py:41-62`) are untouched.

One inconsistency stays: on a channel-less project (path 5) `follow()` returns
`is_followed=True` while `is_followed()` returns `False`. Not reachable through
the API; not worth a branch. If it bothers, return
`FollowState(is_followed=follow.followed_channels.exists(), …)`.

**3. `services/follows/handler_interface.py` — say it**

```diff
     @abstractmethod
     def follow(self, user_id: UUID, project: Project) -> FollowState:
         """Create a Follow (idempotent). Returns the current state.
 
         On first follow, also creates a FollowedChannel row for every channel
         currently on the project. Re-following an already-followed project is
         a no-op: existing FollowedChannel rows are left alone, and no rows
         are added for channels that were created after the original follow.
+
+        The exception is a Follow that has no FollowedChannel rows left —
+        channel deletion cascades them away. That re-enrols every current
+        channel, because otherwise the Follow can never be made to notify
+        about anything again.
         """
+
+    @abstractmethod
+    def prune_empty_follows(self, project_id: UUID) -> int:
+        """Delete Follows on `project_id` that have no followed channels.
+
+        Called after a Channel is deleted, since FollowedChannel cascades and
+        may have taken a user's last row with it. Reads never trust this — see
+        `_effective` in the query service — it exists so the table does not
+        accumulate rows that mean nothing.
+        """
```

**4. `services/follows/django_impl/handler.py` — the pruner**

```python
    def prune_empty_follows(self, project_id: UUID) -> int:
        empty_ids = list(
            Follow.objects.filter(
                project_id=project_id, followed_channels__isnull=True
            ).values_list("pk", flat=True)
        )
        if not empty_ids:
            return 0
        deleted, _ = Follow.objects.filter(pk__in=empty_ids).delete()
        return deleted
```

Materialised to ids first: `.delete()` on a queryset carrying a join is legal
but generates a subquery whose shape depends on the backend, and this runs on
SQLite in tests and Postgres in production.

**5. `services/articles/django_impl/handler.py:209-223` — the caller**

```diff
         sibling_count = Channel.objects.filter(project=channel.project).count()
         if sibling_count <= 1:
             raise LastChannelError
 
-        channel.delete()
+        project_id = channel.project_id
+        channel.delete()
+        # FollowedChannel is CASCADE, so this may have removed a user's last
+        # followed channel. A Follow that notifies about nothing is not a
+        # state we keep — the same rule unfollow_channel applies.
+        from services import HANDLERS  # noqa: PLC0415
+
+        HANDLERS.follows.prune_empty_follows(project_id)
```

The local import matches the existing cross-service call at
`services/articles/django_impl/handler.py:160-162`.

Handler over `post_delete` receiver: `delete_channel` is the only API route to a
channel deletion, and a receiver would also fire during a `Project` cascade,
where the `Follow` rows are being deleted anyway — the raciness
`apps/projects/signals.py:33-45` already documents for a sibling case. The admin
route stays uncovered, which the read-path fix makes tolerable.

### (d) Do the `0004` rows need a migration?

**No — the read-path fix makes them harmless**, which is the direct answer.
Once `is_followed`, `get_state` and `_follow_queryset` require a child row, those
Follows stop appearing on the project page and on `/following`, and pressing
Follow re-enrols them. Nothing else reads `Follow` without joining
`FollowedChannel`.

A cleanup is still worth shipping in the same release, as `follows/0006`:

```python
def drop_empty_follows(apps, schema_editor):
    Follow = apps.get_model("follows", "Follow")
    empty_ids = list(
        Follow.objects.filter(followed_channels__isnull=True).values_list(
            "pk", flat=True
        )
    )
    deleted, _ = Follow.objects.filter(pk__in=empty_ids).delete()
    logger.info("follows.drop_empty_follows: rows_deleted=%d", deleted)
```

Reasons, in order: it makes `0004`'s own docstring true rather than leaving a
known-wrong state documented in the tree; it means the population of childless
rows is bounded rather than monotonic; and it removes the possibility of someone
later "optimising" `_effective` away on the grounds that the state cannot exist.
It is not load-bearing, so it can be dropped without weakening the fix.

**Which options cover the `0004` rows:** 1 and 3 (no migration needed — the read
path ignores them). Option 2 covers them only via the data migration. Options 4
and 5 do not cover them at all.

## Tests

`services/follows/django_impl/test_handler.py`:

- `test_follow_re_enrols_a_follow_left_with_no_channels` — follow, delete every
  `FollowedChannel` directly, `follow()` again, assert both channels are back.
- `test_follow_does_not_enrol_channels_added_since` — already exists as
  `test_second_follow_is_idempotent_and_does_not_auto_enrol_new_channels`
  (`:41-62`) and still passes; keep it, it is now the guard on the other side of
  the new predicate.
- `test_prune_empty_follows_deletes_only_the_childless_ones` — two users, one
  with a channel and one without, assert exactly one row goes.

`services/follows/django_impl/test_query.py`:

- `test_is_followed_is_false_when_the_follow_has_no_channels`
- `test_list_user_follows_omits_a_follow_with_no_channels`
- `test_get_follow_preferences_returns_none_for_a_follow_with_no_channels`

`services/articles/django_impl/` (channel handler tests) — this is coverage gap 4
in the review:

- `test_deleting_a_channel_drops_the_follows_it_emptied` — project with channels
  A and B; user follows the project; delete the user's `FollowedChannel` for B;
  `delete_channel(A)`; assert no `Follow` remains.
- `test_deleting_a_channel_keeps_a_follow_with_another_channel` — the negative.

End-to-end, in `api/routers/test_follows.py`, one test worth the money:

- `test_a_user_whose_last_channel_was_deleted_can_follow_again` — `GET` the
  project, assert `is_followed` is `False`; `POST /follow`; assert `is_followed`
  is `True` and the channel is enrolled. That is the whole user-visible story in
  one place.

Not tested: the `unfollow_channel` race. It needs two connections and does not
reproduce on SQLite. It is also no longer a correctness problem under Option 3 —
the read path returns `False` for the row it leaves behind.

## Risks and what this does not cover

- **`follows/0004`'s docstring becomes stale.** `:31-39` reasons at length that
  an emptied Follow is "a legacy-only state" that "still reports
  `is_following = true`". After this change the second clause is false. The
  migration is applied history and must not be edited; add a line to
  `openspec/changes/simplify-follow-and-cadence/` or the follow-ups file instead.
- **`is_followed` gains a join.** `EXISTS` over `follows ⋈ follow_channel_preferences`
  on the indexed FK, once per project detail page. Not a concern; it is the same
  shape as the `unfollow_channel` check that already runs per unfollow.
- **`_effective` adds a `GROUP BY` to the Following page query.** One aggregate
  over a user's own follows. If it ever shows up, swap for
  `.filter(followed_channels__isnull=False).distinct()`; the `Count` form is
  chosen only because `distinct()` interacts badly with people later adding
  `values()`.
- **The admin can still empty a Follow** (path 2) and nothing prunes it. That is
  by design here — the read path covers it — but it means the table's invariant
  is "eventually true", not "always true". Worth one sentence wherever
  `prune_empty_follows` is documented, so the next reader does not assume they
  can rely on it in a query.
- **Nothing here addresses the reverse asymmetry**: a channel created *after* a
  user follows is still not enrolled, so a project that adds a channel silently
  publishes to fewer people than the follower count suggests. Deliberate per
  `handler.py:18-20`, unchanged by this, and arguably the more interesting
  product question.
- **`apps/follows/services.py:36-45` and `:83-89`** still re-implement enrolment
  and will not pick up the new predicate. That is architecture finding 2 in the
  backend review; it does not produce the bug in question (both paths run
  `get_or_create` over all channels every time, so they are already effectively
  unconditional), but it is the reason this rule keeps needing to be restated.
