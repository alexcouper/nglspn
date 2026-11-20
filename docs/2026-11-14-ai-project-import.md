# Improving a project's listing with an AI assistant

Issue: [#114](https://github.com/alexcouper/nglspn/issues/114).

Filling in a project's title, tagline, description and tags happens on its edit page
(`/my-projects/[id]`), one field at a time. The edit page now has an **Improve with AI** tab:

1. **Copy prompt** (or **Download as file**). The site writes the prompt itself. It carries
   the listing as it stands in the form (unsaved edits included), the real field limits, and
   the live tag list from `/api/tags/grouped`.
2. The maker gives it to any assistant, optionally adding a README, release notes or notes on
   what has changed.
3. The maker pastes the reply, or uploads the `.json` file, and sees only the fields that would
   change, plus anything skipped. **Apply to this project** fills the form and switches to the
   Description tab. Nothing is saved until the maker presses Save.

It lives on the edit page, not `/create`, because that is where the fields are, and because it
works the same for a fresh draft (empty fields: "fill in what's missing") and for an old listing
("revitalise it"). `/create` stays a one-field form: paste a link, get a draft.

## Why bring-your-own-assistant

No server-side LLM call means no API key, no cost per use, no new endpoint and no rate limit to
tune. Apply only changes form state, and Save uses the existing `PUT /api/my/projects/{id}`. The
backend is unchanged.

## The format

`naglasupan.project/v1`, defined in
[`src/web-ui/src/lib/project-import.ts`](../src/web-ui/src/lib/project-import.ts). That module
is the format's one home: the prompt, the limits and the parser all live there, and its tests
check that the example in the prompt passes the parser.

- **Strict about content.** A field over its length limit (copied from
  `apps/projects/models.py`), a URL that isn't `http(s)`, a wrong type, or a different `format`
  version are all errors. Errors are listed together so the maker can fix them in one round trip
  with the assistant.
- **Forgiving about wrapping.** Code fences, prose around the JSON, a missing `format` key and
  unknown keys are fine. Unknown keys produce a warning, not an error.
- **Every field is optional.** A field left out or empty keeps its current value. The prompt asks
  for the complete listing anyway, so the preview can show a real rewrite.
- **Tags go by name, not id.** An assistant can't know tag UUIDs. Names and slugs are matched
  case-insensitively. A name that doesn't match is skipped with a warning and never created,
  because suggesting a new tag needs a category and goes through review. If no name matches,
  the project's tags are left alone rather than cleared.
- **Only fields a page renders.** `long_description`, `github_url`, `demo_url` and `tech_stack`
  are accepted by the API, but no page displays them. Asking for them would store text nobody
  sees. Add them to the format when a page shows them. Adding optional keys stays within v1, and
  a reader that predates them just warns about the unknown key.

## Not covered

- **Images.** Uploaded on the same page, by hand.
