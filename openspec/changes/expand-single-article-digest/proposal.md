# Expand the single-article digest into the article itself

Issue: [#104](https://github.com/alexcouper/nglspn/issues/104).

## Why

The article digest goes out with the subject "New articles - Naglasúpan" and a
list of entries: title, channel, a short excerpt and a link. In practice there is
almost always exactly one article in the batch, so the reader gets a generic
subject and a teaser for a thing they could have been given outright.

Two things make the fix cheap. Article bodies are markdown
(`apps/articles/models.py`, `Article.body`), and the broadcast email already
renders admin markdown into the mjml layout
(`services/email/django_impl/query.py:22`, `render_broadcast_email`). Broadcast
images are not attached: admin uploads them to S3 and inserts `![](cdn url)`;
they go out as remote `<img>` tags. Article images have exactly the same shape,
`![alt](https://cdn.naglasupan.is/<storage_key>)`, so the same approach applies.

## What Changes

- **Layout is chosen by batch size.** One article: the subject is the article
  title, prefixed with the project title unless the project is the house
  project (`Project.is_house_project`), and the body is the full article
  rendered from markdown with a byline and a link to the page. Two to four:
  the subject names the newest article and counts the rest, the newest gets a
  long excerpt, the others get today's entry treatment. Five or more: today's
  list, with a counted subject.
- **Articles order newest first**, by `published_at` with the notification's
  `created_at` as fallback. Same key as the bell's `_build_article_group`.
- **Article markdown gets one Python renderer for email**, in
  `services/articles/render.py` beside `summary.py`. It flattens `:::gallery`
  blocks, runs python-markdown with the broadcast's extensions, then sanitises
  and inline-styles the HTML with `nh3` (new dependency). Author `style`
  attributes are stripped, as `sanitize-schema.ts` does on the web.
- **One builder feeds both the sender and the admin preview.**
  `apps/notifications/admin.py:175` currently assembles its own context and
  picks the template itself, so a layout switch in the handler would not reach
  the preview. The build moves to one function both call.
- **The legacy `article_notification` templates are deleted.** Nothing renders
  them. `SentEmailType.ARTICLE_NOTIFICATION` stays for the historical rows.

Not breaking: no model field, migration or API change. `backend-openapi.json`
is untouched and no frontend file changes.

### Explicitly out of scope

- Who gets the digest and how often. Cadence, follow preferences and the
  `email_sent` bookkeeping in `send_article_digest`
  (`services/notifications/django_impl/handler.py:323`) are unchanged.
- The discussion digest.
- Syntax colouring in emailed code blocks. They come out monospace on grey.

## Capabilities

### Modified Capabilities

- `notifications`: a new requirement on the article digest email's subject and
  layout by batch size, and on how an article body is rendered for email.

## Impact

**Backend** (`src/django-backend/`):

- `services/articles/render.py` — new. Markdown to email HTML.
- `services/email/django_impl/article_digest.py` — new. Chooses the layout and
  builds subject, template name and context from a recipient's notifications.
  Absorbs `build_article_digest_entries` from `handler.py:113`.
- `services/email/django_impl/handler.py:483` — `send_article_digest_email`
  calls the builder; the hardcoded subject goes.
- `apps/notifications/admin.py:175` — the preview calls the builder.
- `templates/email/article_digest_single.{mjml,txt}` and
  `article_digest_lead.{mjml,txt}` — new. `article_digest.{mjml,txt}` stays
  for the list. The entry markup moves to a shared include.
- `templates/email/article_notification.{mjml,txt}` — deleted.
- `pyproject.toml` — `nh3` added.

**Not affected**: models and migrations, `send_article_digest` and its
cadence workers, `SentEmail` logging (all three layouts log as
`ARTICLE_DIGEST`; the subject tells them apart), every router, and
`src/web-ui/`.
