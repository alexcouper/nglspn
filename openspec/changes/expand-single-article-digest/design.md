## Context

`send_article_digest` (`services/notifications/django_impl/handler.py:323`)
collects a recipient's unsent article notifications for a cadence and hands the
list to `send_article_digest_email` (`services/email/django_impl/handler.py:483`).
That renders `article_digest.mjml` with one entry per notification from
`build_article_digest_entries` (`handler.py:113`): project, channel, title, a
plain-text excerpt from `services/articles/summary.py`, and a link. The subject
is the constant "New articles - Naglasúpan".

What is already in place and reused here:

| Piece | Where | Reused for |
|---|---|---|
| Markdown to mjml body | `render_broadcast_email`, `services/email/django_impl/query.py:22` | the extension set and the `<mj-text>{{ body_html\|safe }}</mj-text>` pattern |
| House project flag | `Project.is_house_project`, set by `anoint_house_project` (`apps/follows/services.py:48`) | the subject rule |
| Newest-first key | `_build_article_group`, `services/notifications/django_impl/handler.py` | ordering the batch |
| Web allowlist for raw HTML | `src/web-ui/src/app/projects/[slug]/articles/sanitize-schema.ts` | the email allowlist, minus highlighter classes |
| Admin preview | `preview_digest_detail_view`, `apps/notifications/admin.py:175` | the place to look at all three layouts |

What article markdown contains that broadcast markdown never does: the
`:::gallery` container directive (`gallery-mdast.ts`), fenced code that the web
colours with rehype-prism-plus, raw HTML from any `full_edit` contributor
(`figure`, `figcaption`, `<img width height>` from MDXEditor, `<div align>`),
and GFM tables.

Images in a body point at the original upload, `ProjectImage.url`
(`apps/projects/models.py`), not a variant. Originals can be several megabytes.

## Goals / Non-Goals

**Goals:**

- A one-article batch reads as the article: its title as the subject, the body
  in the email, a link at the end.
- The two-plus path stays alive and is visible in the admin preview, so it is
  dogfooded rather than rotting.
- Raw HTML in an article body is no more dangerous in an email than on the web.
- The sender and the admin preview cannot disagree about what goes out.

**Non-Goals:**

- Changing recipients, cadence or the `email_sent` bookkeeping.
- Pixel parity with the web article page.
- Touching the discussion digest.

## Decisions

### 1. Three layouts, chosen by batch size, from one builder

| Articles | Subject | Template |
|---|---|---|
| 1 | `<Project>: <Title>`, or `<Title>` for the house project | `article_digest_single` |
| 2 to 4 | `<Project>: <Title>, and N more`, same house rule on the lead | `article_digest_lead` |
| 5 or more | `N new articles - Naglasúpan` | `article_digest` (today's) |

A new module `services/email/django_impl/article_digest.py` exposes one
function, `build_article_digest(notifications)`, returning subject, template
name and context. `send_article_digest_email` and the admin preview both call
it. Today the preview duplicates the context build and names the template
itself; after this it has no opinion of its own.

The single and lead subjects drop the ` - Naglasúpan` suffix the other emails
carry. The sender name carries the brand, which is the same reason the house
project drops its own name from the subject.

The cutoff of four is a guess. It is a constant in the builder and the admin
preview is where to tune it against real batches.

### 2. The house project rule reads `is_house_project`, not a slug

The digest query already does `select_related("article__project")`, so
`article.project.is_house_project` costs nothing. A slug setting would have to
be kept in step with `anoint_house_project` by hand.

### 3. Newest first, by the bell's key

Sort by `article.published_at or notification.created_at`, descending. The
query orders by `created_at` ascending for the per-recipient grouping; the
builder re-sorts its own batch and the query is untouched.

### 4. Article markdown to email HTML lives in `services/articles/render.py`

Next to `summary.py`, for the same reason that module gives: one Python home
for walking an article body, so a second implementation cannot drift. Steps:

1. **Pre-process.** Split the markdown into blocks, treating a fenced code
   block and a `:::gallery ... :::` block each as one unit rather than breaking
   on every blank line. Flatten each gallery to its images, stacked, by
   dropping the fence lines. Python-markdown would otherwise print `:::gallery`
   as a paragraph.
2. **Render** with python-markdown and the broadcast's extensions, `extra` and
   `smarty`, so the two email surfaces stay in step.
3. **Sanitise and style in one pass** with `nh3.clean`. The tag and attribute
   allowlist mirrors `sanitize-schema.ts`: GitHub defaults plus `figure`,
   `figcaption`, `align` on `div`. `style` is not in the allowlist, so author
   styles are stripped, exactly as on the web. `set_tag_attribute_values` then
   puts our own inline styles on `img`, `pre`, `code`, `blockquote`, `table`,
   `th` and `td`. Email clients ignore stylesheets, and this avoids depending
   on whether the `mjml` package's engine honours `<mj-style inline>`.
4. **Images.** Drop MDXEditor's `width` and `height` attributes so
   `max-width: 100%` wins. Where the `src` matches a `ProjectImage` on the
   article, substitute the `medium` variant URL (768 px) when one exists. The
   variants are one prefetch on `article__images__variants`.

The plain-text part sends the raw markdown, which the broadcast already does.

Highlighter classes are deliberately absent from the allowlist. Prism's output
only exists on the web; python-markdown emits bare `<pre><code>`.

`nh3` is the maintained successor to bleach, a Rust binding with no Python
dependencies. It is new to this repo.

### 5. The lead excerpt is markdown, truncated by block

For the two-to-four layout the newest article shows its whole body when the
markdown is short, about 1200 characters, otherwise the first blocks up to about
800 characters followed by a "Continue reading" link. The block splitter from
decision 4 step 1 does the cutting, so a fence or a gallery is kept whole or
dropped whole, never cut in half. The excerpt then goes through the same render
pipeline. Both thresholds are constants beside the layout cutoff.

### 6. Byline matches the web header

Project title linked to the project page, channel name, publication date, and
the author's name when the author is not a system user. That is what
`ArticleRenderContent.tsx` shows under the title.

### 7. Delete `article_notification`, keep its enum value

`templates/email/article_notification.{mjml,txt}` are rendered by nothing.
Removing `SentEmailType.ARTICLE_NOTIFICATION` would need a migration and break
the admin display of the rows that already carry it, for no gain.

### 8. Templates: two new, one include

`article_digest_single` and `article_digest_lead` are new; `article_digest`
stays for the list. The per-entry markup becomes a Django include used by the
lead and list templates. `render_email` renders the Django template before
mjml compiles, so includes work today.

### 9. Admin preview gains a `?layout=` override

Dogfooding the fallback otherwise means manufacturing five unsent notifications
for one recipient. The override forces a template on the existing batch; the
subject and ordering still come from the builder.

## Risks / Trade-offs

- **`nh3` attribute order** → the design assumes `set_tag_attribute_values`
  applies after the allowlist strips author attributes. Task 1.1 is a spike
  confirming that, and that a `<span class="fixed inset-0">` style of abuse is
  rejected, before anything is built on it.
- **GFM strikethrough and task lists** → no python-markdown `extra` equivalent;
  they render as literal tildes and brackets. Rare in articles. `pymdown-
  extensions` fixes it if it turns out to matter.
- **Gmail clips HTML above about 100 KB** → images are remote, so a long single
  article stays well under that unless the text itself is very long. Not
  guarded against until it happens.
- **Thresholds are guesses** → four articles, 1200 and 800 characters. All are
  constants; the preview is where to tune them.
- **Behaviour change for recipients** → the single-article email is longer and
  its subject no longer starts with "New articles". Intended.
