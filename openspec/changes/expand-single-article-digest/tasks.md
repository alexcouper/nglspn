# Tasks: expand single-article digest

All paths are relative to `src/django-backend/`.

## 1. Rendering article markdown for email

- [x] 1.1 Spike `nh3`: confirm `set_tag_attribute_values` applies after the
  allowlist strips author attributes, and that `class` and `style` from an
  author are gone. Add `nh3` to `pyproject.toml` and `uv sync`.
- [x] 1.2 Add `services/articles/render.py` with a block splitter that keeps
  fenced code and `:::gallery` blocks whole, a gallery flattener, and
  `render_for_email(body, images)` doing markdown, sanitise, inline styles,
  width/height removal and medium-variant substitution. Extension set shared
  with `render_broadcast_email` by a module constant, not copied.
- [x] 1.3 Add `excerpt_for_email(body, limit)` on the same splitter: whole body
  under the short threshold, otherwise whole blocks up to the limit.
- [x] 1.4 Tests in `services/articles/test_render.py`: style and class
  stripped, `figure`/`figcaption` kept, gallery flattened, fence not split by
  the excerpt, width/height dropped, variant substituted, no variant leaves the
  original.

## 2. The builder

- [x] 2.1 Add `services/email/django_impl/article_digest.py` with
  `build_article_digest(notifications)` returning subject, template name and
  context. Move `build_article_digest_entries` into it. Constants for the list
  cutoff and the excerpt thresholds at the top.
- [x] 2.2 Subject rule: project prefix unless `project.is_house_project`;
  `, and N more` for the lead layout; `N new articles - Naglasúpan` for the
  list.
- [x] 2.3 Sort newest first by `article.published_at or created_at`.
- [x] 2.4 Byline context: project title and URL, channel name, published date,
  author name when `author` is set and not `is_system_user`.
- [x] 2.5 Extend the digest query's prefetch in
  `services/notifications/django_impl/handler.py:323` with
  `article__images__variants` and `article__author`, so the renderer has the
  variants and the byline without extra queries.

## 3. Templates

- [x] 3.1 Move the entry markup from `article_digest.mjml` and `.txt` into an
  include and use it from the list template.
- [x] 3.2 Add `article_digest_single.{mjml,txt}`: byline, `{{ body_html|safe }}`
  inside `<mj-text>`, "Read on Naglasúpan" button, frequency link in the
  footer. Text part sends the raw markdown.
- [x] 3.3 Add `article_digest_lead.{mjml,txt}`: lead article with byline and
  excerpt HTML, "Continue reading" link when truncated, then the include for
  the rest.
- [x] 3.4 Delete `templates/email/article_notification.mjml` and `.txt`.

## 4. Wiring

- [x] 4.1 `send_article_digest_email` (`services/email/django_impl/handler.py:483`)
  calls the builder and uses its subject and template. `email_type` stays
  `ARTICLE_DIGEST`.
- [x] 4.2 `preview_digest_detail_view` (`apps/notifications/admin.py:175`) calls
  the builder for the article kind, drops its own context build, and accepts
  `?layout=single|lead|list` to force a template. Its `select_related` gains
  what the builder needs.
- [x] 4.3 Handler tests in `services/email/django_impl/test_handler.py`: the
  four subject cases from the spec, ordering, the body of a single article in
  the HTML part, the legacy excerpt tests retargeted at the builder module.
- [x] 4.4 Admin preview tests in `apps/notifications/tests/test_admin_preview.py`:
  one notification renders the single layout, the layout override works.

## 5. Verify

- [x] 5.1 `make lint`
- [x] 5.2 `make extra-tests` — no API change, so `backend-openapi.json` must
  still be in sync.
- [x] 5.3 `make test`
- [x] 5.4 `uv run python manage.py makemigrations --check --dry-run` — no model
  change, so nothing to make.
- [ ] 5.5 Open the admin preview for a recipient with one real article and
  check it in at least one mail client via a test send. Check an article with
  a gallery, a code fence and a table.
