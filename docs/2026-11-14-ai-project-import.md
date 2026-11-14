# Filling in a new project from an AI assistant

Issue: [#114](https://github.com/alexcouper/nglspn/issues/114).

Before this change, a new project meant creating a draft from its URL and then filling in
the title, tagline, description and tags on the edit page, one field at a time. `/create`
now has a second tab, **Fill it in with AI**:

1. **Copy prompt** (or **Download as file**). The site writes the prompt itself, so it
   carries the real field limits and the live tag list from `/api/tags/grouped`.
2. The maker gives it to any assistant, along with a URL, a README or some notes.
3. The maker pastes the reply, or uploads the `.json` file, and sees a preview with
   anything skipped. One click then creates the draft with every field filled in.

## Why bring-your-own-assistant

No server-side LLM call means no API key, no cost per submission, no new endpoint and no
rate limit to tune. The only request is the existing `POST /api/my-projects`, which already
accepted every field. The backend is unchanged.

## The format

`naglasupan.project/v1`, defined in
[`src/web-ui/src/lib/project-import.ts`](../src/web-ui/src/lib/project-import.ts). That
module is the format's one home: the prompt, the limits and the parser all live there, and
its tests check that the example in the prompt passes the parser.

- **Strict about content.** A field over its length limit (copied from
  `apps/projects/models.py`), a URL that isn't `http(s)`, a wrong type, or a different
  `format` version are all errors. Errors are listed together so the maker can fix them in
  one round trip with the assistant.
- **Forgiving about wrapping.** Code fences, prose around the JSON, a missing `format` key
  and unknown keys are fine. Unknown keys produce a warning, not an error.
- **Tags go by name, not id.** An assistant can't know tag UUIDs. Names and slugs are matched
  case-insensitively. A name that doesn't match is skipped with a warning and never created,
  because suggesting a new tag needs a category and goes through review.
- **Only fields a page renders.** `long_description`, `github_url`, `demo_url` and
  `tech_stack` are accepted by the API, but no page displays them. Asking for them would
  store text nobody sees. Add them to the format when a page shows them. Adding optional
  keys stays within v1, and a reader that predates them just warns about the unknown key.

## Not covered

- **Images.** A main image is still needed to publish, and it is uploaded on the edit page.
- **Importing into an existing draft.** The parser returns plain create fields, so wiring it
  into the edit page later is mostly UI work.
