## 1. Remove the platform_updates broadcast type

- [ ] 1.1 Delete `PLATFORM_UPDATES` from `BroadcastEmailType` in `apps/emails/models.py:9`.
- [ ] 1.2 Generate the `choices` `AlterField` migration in `apps/emails/migrations/` (`uv run python manage.py makemigrations emails`). Confirm `makemigrations --check --dry-run` is clean afterwards.
- [ ] 1.3 Reduce `BROADCAST_CHANNEL_BY_EMAIL_TYPE` in `services/users/django_impl/query.py:15` to `{"competition_results": "Competition Winners"}`.
- [ ] 1.4 Verify by hand that a historic `BroadcastEmail` row with `email_type="platform_updates"` still loads in the admin change view and that `resolve_broadcast_recipients` returns an empty QuerySet for it rather than raising.

## 2. Repair the test fixtures broken by step 1

- [ ] 2.1 `tests/factories.py:166` — `make_broadcast_follower` indexes `BROADCAST_CHANNEL_BY_EMAIL_TYPE`; decide whether it keeps taking an `email_type` or takes a channel name, and update the docstring.
- [ ] 2.2 Rewrite the `"platform_updates"` callers in `tests/test_broadcast_emails.py` onto `competition_results` where the assertion is about the mechanism; delete the ones that only restate a `competition_results` case.
- [ ] 2.3 Same for `tests/test_inactive_user_emails.py` and `services/users/django_impl/test_query.py`.
- [ ] 2.4 Add a test that `list_opted_in_for_broadcast_type("platform_updates")` returns empty and does not raise.
- [ ] 2.5 `make test` green before starting section 3.

## 3. Merge the channels

- [ ] 3.1 Write `apps/follows/migrations/0006_merge_product_updates_into_updates.py`, depending on `follows/0005_drop_legacy_booleans` and `articles/0005_alter_article_listing_image`.
- [ ] 3.2 Forward function, inside one `transaction.atomic()`: resolve the house project via `is_house_project=True`; return with a `logger.warning` if absent. Fetch "Updates" and "Product Updates" by name; return if "Product Updates" is absent (already merged / fresh install).
- [ ] 3.3 Reassign articles: `Article.objects.filter(channel=updates).update(channel=product_updates)`. Must precede the delete — `Article.channel` is `on_delete=PROTECT`.
- [ ] 3.4 Delete the "Updates" channel (cascades its `FollowedChannel` rows), then rename "Product Updates" to `"Updates"`. Order is forced by `unique_together = (("project", "name"))`.
- [ ] 3.5 Handle the no-"Updates"-channel case by skipping to the rename.
- [ ] 3.6 Reverse function: a no-op with a docstring explaining that cascaded follower rows cannot be reconstructed, following `follows/0004_sweep_both_off_rows.py`.

## 4. Update the tests that assert the old channel shape

- [ ] 4.1 `apps/follows/tests/test_anoint_house_project.py` — expects three channels; now two.
- [ ] 4.2 `apps/follows/tests/test_auto_follow_signal.py` — same.
- [ ] 4.3 `services/follows/django_impl/test_integration.py` and `services/notifications/django_impl/test_article_fanout.py` — replace "Product Updates" references.
- [ ] 4.4 `make lint` and `make test` green.

## 5. Verify end to end

- [ ] 5.1 On a seeded local database: `make seed`, confirm the house project has exactly "Updates" and "Competition Winners", and that the surviving "Updates" follower count matches the pre-migration "Product Updates" count.
- [ ] 5.2 Publish an article on the house project's "Updates" channel and confirm `event=house_channel_article_enqueued` lines appear for its followers.
- [ ] 5.3 Confirm the Django admin offers only "Competition Results" as a broadcast `email_type`.

## 6. Before deploying

- [ ] 6.1 Count articles per house channel on production. Record the number in the PR — it is what tells you whether the unsubscribe event affects anyone in practice.
- [ ] 6.2 Record the pre-migration follower counts for "Updates" and "Product Updates" in the PR, so the post-deploy check in the design's migration plan has something to compare against.
