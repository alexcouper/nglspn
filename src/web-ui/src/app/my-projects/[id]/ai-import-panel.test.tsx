import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { ProjectFormData } from "./ProjectDetail";

vi.mock("@/lib/api", () => ({
  api: { tags: { listGrouped: vi.fn() } },
}));

const { api } = await import("@/lib/api");
const { AiImportPanel } = await import("./AiImportPanel");

const GROUPS = [
  {
    category: { id: "c1", name: "Type", slug: "type", description: "", display_order: 0 },
    tags: [
      { id: "t-oss", name: "Open source", slug: "open-source", description: null, color: "#0a0" },
      { id: "t-saas", name: "SaaS", slug: "saas", description: null, color: null },
    ],
  },
];

const CURRENT: ProjectFormData = {
  title: "Example",
  tagline: "Old tagline",
  website_url: "https://example.is",
  description: "Old description.",
  tag_ids: ["t-saas"],
};

const REPLY = `Sure! Here it is:

\`\`\`json
{
  "format": "naglasupan.project/v1",
  "website_url": "https://example.is",
  "title": "Example",
  "tagline": "Does a thing, better",
  "description": "It does a thing.",
  "tags": ["Open source", "Blockchain"]
}
\`\`\``;

let root: Root;
let container: HTMLElement;
let onApply: ReturnType<typeof vi.fn>;

async function mount(current: ProjectFormData = CURRENT) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  onApply = vi.fn();
  await act(async () => {
    root.render(<AiImportPanel current={current} onApply={onApply} />);
  });
}

function button(name: string): HTMLButtonElement {
  const found = [...container.querySelectorAll("button")].find((b) => b.textContent === name);
  if (!found) throw new Error(`no button ${name}`);
  return found as HTMLButtonElement;
}

async function click(el: HTMLElement) {
  await act(async () => {
    el.click();
  });
}

async function paste(text: string) {
  const textarea = container.querySelector<HTMLTextAreaElement>("#ai-output")!;
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  await act(async () => {
    setter.call(textarea, text);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function previewLabels() {
  return [...container.querySelectorAll("dt")].map((dt) => dt.textContent);
}

beforeEach(() => {
  vi.mocked(api.tags.listGrouped).mockReset().mockResolvedValue(GROUPS as never);
  return () => {
    act(() => root.unmount());
    container.remove();
  };
});

describe("AI import on the edit page", () => {
  it("copies a prompt carrying the current listing and the tag list", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await mount();
    await click(button("Copy prompt"));

    const prompt = writeText.mock.calls[0][0] as string;
    expect(prompt).toContain('"tagline": "Old tagline"');
    expect(prompt).toContain('"description": "Old description."');
    // Current tags go by name, not id.
    expect(prompt).toContain('"SaaS"');
    expect(prompt).not.toContain("t-saas");
    expect(prompt).toContain("Type: Open source, SaaS");
    expect(button("Copied!")).toBeTruthy();
  });

  it("previews only what changes, then hands it to the form", async () => {
    await mount();
    await paste(REPLY);

    expect(previewLabels()).toEqual(["Tagline", "Description", "Tags"]);
    expect(container.textContent).toContain("Does a thing, better");
    expect(container.textContent).toContain('Tag "Blockchain" doesn\'t exist here');

    await click(button("Apply to this project"));

    expect(onApply).toHaveBeenCalledWith(
      {
        website_url: "https://example.is",
        title: "Example",
        tagline: "Does a thing, better",
        description: "It does a thing.",
        tag_ids: ["t-oss"],
      },
      [{ id: "t-oss", name: "Open source", slug: "open-source", color: "#0a0" }],
    );
    // Cleared, so the box doesn't keep offering a reply that's already applied.
    expect(container.querySelector<HTMLTextAreaElement>("#ai-output")!.value).toBe("");
  });

  it("disables apply when the reply changes nothing", async () => {
    await mount();
    await paste(JSON.stringify({ title: "Example", tags: ["SaaS"] }));

    expect(container.textContent).toContain("nothing to apply");
    expect(button("Apply to this project").disabled).toBe(true);
  });

  it("explains what is wrong and keeps apply disabled", async () => {
    await mount();
    await paste(JSON.stringify({ title: "x".repeat(101), website_url: "ftp://nope" }));

    const alert = container.querySelector('[role="alert"]')?.textContent;
    expect(alert).toContain('"title" is 101 characters; the limit is 100.');
    expect(alert).toContain('"website_url" must be a link');
    expect(button("Apply to this project").disabled).toBe(true);
  });

  it("still applies text fields when the tag list fails to load", async () => {
    vi.mocked(api.tags.listGrouped).mockRejectedValue(new Error("down"));
    await mount();
    await paste(REPLY);
    await click(button("Apply to this project"));

    const [fields] = onApply.mock.calls[0];
    expect(fields.tagline).toBe("Does a thing, better");
    // No tag matched, so the project's tags are left alone.
    expect(fields.tag_ids).toBeUndefined();
  });
});
