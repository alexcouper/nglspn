# 12. `derive_summary` has a second implementation

**Finding:** Architecture point 3 / backend review §15 — `summary.py` claims to be
the only place a summary is derived; the notification bell derives its own from
raw markdown and ignores the authored summary.
**Alex:** This sounds bad, can we propose a fix?
**Type:** fix proposal
**Effort:** S, one line of behaviour change, one rename, two tests. Under an hour.

## What is actually happening

`services/articles/summary.py:1-6` states the invariant:

> Lives only here — a second implementation in TypeScript would drift, so the
> frontend previews a saved article rather than deriving client-side.

`services/notifications/django_impl/handler.py:47-51`:

```python
def _body_excerpt(text: str) -> str:
    text = text.strip()
    if len(text) <= _BODY_EXCERPT_MAX:
        return text
    return text[:_BODY_EXCERPT_MAX].rstrip() + "…"
```

`str.strip()` and a 240-character slice. `_build_article_group` calls it on
`article.body` at `:123`.

**Does it ignore the authored summary?** Yes, completely. `article.summary` is
never read on this path — `_build_article_group` (`:102-129`) touches
`article.published_at`, `body`, `id`, `slug`, `title`, `channel.name` and
`listing_image`, and nothing else. Every other surface prefers it:

| Surface | Code |
|---|---|
| Article detail / editor | `api/schemas/article.py:130-131` — `obj.summary or derive_summary(obj.body)` |
| Article listing card | `api/schemas/article.py:187-188` — same |
| Digest email | `services/email/django_impl/handler.py:121-123` — same, `limit=500` |
| Notification bell | `handler.py:123` — `_body_excerpt(article.body)` |

`src/web-ui/src/components/NotificationGroupItem.tsx:49` renders the result as
plain text in a `truncate` / `line-clamp-2` div. So an article opening
`# Why we rewrote the indexer\n\n![diagram](https://…/x.png)\n\nWe…` shows in the
bell as `# Why we rewrote the indexer ![diagram](https://…`, with the author's
summary — which exists precisely for this — unused.

The docstring's claim is not merely stale; the drift it warns about has already
happened, in Python rather than TypeScript.

## Is `_body_excerpt` still correct for its other caller?

Its other caller is `_build_group` at `:86`, on `latest.discussion.body`.

Checked end to end. Discussion bodies are **plain text, not markdown**:

- Authored in a bare `<textarea>` with no toolbar and no editor —
  `src/web-ui/src/components/NewDiscussionModal.tsx:88-97`.
- Stored as an unadorned `TextField` — `apps/discussions/models.py:27`.
- Rendered as text with `whitespace-pre-wrap`, not through any markdown pipeline
  — `src/web-ui/src/app/projects/[slug]/discussions/DiscussionList.tsx:276-278`
  and `:157-159`.

So `_body_excerpt` is correct there, and running `derive_summary` over a
discussion body would be **actively wrong**, not merely unnecessary:

- `_LINK_RE` (`summary.py:18`) rewrites `[see](this)` — a literal thing people
  type in comments — to `see`.
- `_HTML_TAG_RE` (`:19`) silently deletes `<Foo>` from a comment about generics.
- `_HEADING_LINE_RE` (`:16`) deletes any line starting `# `, which in a plain-text
  comment is a hash tag or a shell prompt.
- `_LINE_MARKER_RE` (`:20`) strips `> ` from quoted text, which is the one
  markdown-ish convention people actually use in comments and the one place the
  marker carries meaning.

**Verdict: `_body_excerpt` stays, for discussions only.** It should not go
entirely, and it should not be redirected through `derive_summary`. What it should
do is stop looking like a general-purpose excerpt helper, because that is how it
ended up on the article path.

## Proposed change

`services/notifications/django_impl/handler.py`. Three edits.

**1. Rename and document the plain-text helper** (`:47-51`):

```diff
-def _body_excerpt(text: str) -> str:
+def _plain_text_excerpt(text: str) -> str:
+    """Truncate a body that is already plain text.
+
+    Discussion bodies only. They are typed into a bare textarea and rendered
+    with `whitespace-pre-wrap`, so there is no markup to flatten — and running
+    `derive_summary` over one would mangle literal `[a](b)`, `<T>` and `> `
+    that a commenter meant literally. Articles are markdown: use
+    `derive_summary`.
+    """
     text = text.strip()
     if len(text) <= _BODY_EXCERPT_MAX:
         return text
     return text[:_BODY_EXCERPT_MAX].rstrip() + "…"
```

Update the one remaining call at `:86` to the new name.

**2. Use the shared derivation for articles** (`:123`):

```diff
+from services.articles.summary import derive_summary
@@ def _build_article_group
-        latest_body_excerpt=_body_excerpt(article.body),
+        # Same rule as every other article surface (`ArticleOut.summary_display`,
+        # `ArticleListItem.summary`, the digest email): the authored summary wins,
+        # and the fallback is the one derivation in `services/articles/summary.py`.
+        latest_body_excerpt=article.summary or derive_summary(
+            article.body, limit=_BODY_EXCERPT_MAX
+        ),
```

`derive_summary`'s `limit` parameter already exists (`summary.py:27`) and is
already used with a non-default value by the digest
(`services/email/django_impl/handler.py:99,122`), so passing `_BODY_EXCERPT_MAX`
here is the established pattern rather than a new one. It also gives a better
truncation than the current slice: `_truncate` (`summary.py:44-48`) cuts on a word
boundary and trims trailing punctuation.

**3. Fix the docstring's claim.** `services/articles/summary.py:1-6` says "a second
implementation in TypeScript would drift". After this change the statement is true
again, but it should also say what the module is *for*, so the next person does
not read it as a frontend-only concern:

```diff
-Used when an article has no authored summary. Lives only here — a second
-implementation in TypeScript would drift, so the frontend previews a saved
-article rather than deriving client-side.
+Used when an article has no authored summary. Every surface that shows an
+article excerpt goes `article.summary or derive_summary(article.body)`:
+`ArticleOut.summary_display`, `ArticleListItem.summary`, the digest email and
+the notification bell. Lives only here — a second implementation would drift,
+in Python as easily as in TypeScript, so the frontend previews a saved article
+rather than deriving client-side.
+
+Discussion bodies are NOT markdown and must not come through here; see
+`services/notifications/django_impl/handler.py::_plain_text_excerpt`.
```

There is no import-cycle concern: `services/articles/summary.py` imports only
`re`.

## Tests

`services/notifications/django_impl/test_in_app.py` has no article-group coverage
at all today (`grep article` returns nothing in that file), so this adds the first.

```python
@pytest.mark.django_db
class TestArticleGroupExcerpt:
    def test_prefers_the_authored_summary(self, handler):
        user = UserFactory()
        article = PublishedArticleFactory(
            body="## Ignored\n\nDerived from the body.",
            summary="The authored summary.",
        )
        NotificationFactory(recipient=user, discussion=None, article=article)

        (group,) = handler.list_unread_groups_for_user(user.id)

        assert group.latest_body_excerpt == "The authored summary."

    def test_flattens_markdown_when_there_is_no_summary(self, handler):
        user = UserFactory()
        article = PublishedArticleFactory(
            body="# Why we rewrote the indexer\n\n"
                 "![diagram](https://cdn.example.com/x.png)\n\n"
                 "We replaced the crawler.",
        )
        NotificationFactory(recipient=user, discussion=None, article=article)

        (group,) = handler.list_unread_groups_for_user(user.id)

        assert group.latest_body_excerpt == "We replaced the crawler."
```

Both fail today: the first returns `## Ignored\n\nDerived from the body.`, the
second returns the raw markdown.

And one that pins the discussion side so a future tidy-up does not "unify" the two
helpers:

```python
    def test_a_discussion_excerpt_keeps_literal_markdown_characters(self, handler):
        user = UserFactory()
        discussion = DiscussionFactory(body="Try [this](that) with <T> please")
        NotificationFactory(recipient=user, discussion=discussion)

        (group,) = handler.list_unread_groups_for_user(user.id)

        assert group.latest_body_excerpt == "Try [this](that) with <T> please"
```

That one passes today and is the point — it is the regression guard, not a fix.

The mirror-image assertions already exist for the digest at
`services/email/django_impl/test_handler.py:446-470`
(`TestArticleDigestExcerpt`), so the two paths end up covered the same way.

## Risks and what this does not cover

- **`derive_summary` returns `""` for a body with nothing extractable** — a body
  that is only a heading and an image, for instance (`summary.py:41`).
  `_body_excerpt` would have returned the raw markdown. So the bell goes from
  "wrong text" to "no text" in that case. That is the correct trade — the digest
  and the listing card already behave this way
  (`api/schemas/article.py:130-131`) — but the bell UI should be checked to
  confirm an empty `latest_body_excerpt` renders as an empty line rather than a
  collapsed layout. `NotificationGroupItem.tsx:49` renders it into a fixed-class
  `div`, so it degrades to an empty line. Fine.
- **`derive_summary` is regex work on every bell open**, once per article group,
  capped at `limit=50` groups (`handler.py:387`). The digest already does the same
  on a larger limit. Not a concern.
- **No API shape change**, so no OpenAPI regeneration and no frontend change.
  `latest_body_excerpt` is already a `str`.
- **Does not address the wider "one rule, several homes" pattern** — the 16:9
  card ratio (backend review §3) is the same class of problem in six files across
  two languages, and is not touched here.
