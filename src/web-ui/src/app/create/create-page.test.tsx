import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

const { routerCalls } = vi.hoisted(() => ({
  routerCalls: { push: vi.fn(), refresh: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerCalls,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => ({ isReady: true, isLoading: false }),
}));
vi.mock("@/lib/api", () => ({
  api: {
    myProjects: { create: vi.fn() },
    tags: { listGrouped: vi.fn() },
  },
}));

const { api } = await import("@/lib/api");
const { default: CreateProjectPage } = await import("./page");

const GROUPS = [
  {
    category: { id: "c1", name: "Type", slug: "type", description: "", display_order: 0 },
    tags: [{ id: "t-oss", name: "Open source", slug: "open-source", description: null, color: null }],
  },
];

const REPLY = `Sure! Here it is:

\`\`\`json
{
  "format": "naglasupan.project/v1",
  "website_url": "https://example.is",
  "title": "Example",
  "tagline": "Does a thing",
  "description": "It does a thing.",
  "tags": ["Open source", "Blockchain"]
}
\`\`\``;

let root: Root;
let container: HTMLElement;

async function mount() {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(<CreateProjectPage />);
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

beforeEach(() => {
  vi.mocked(api.tags.listGrouped).mockReset().mockResolvedValue(GROUPS as never);
  vi.mocked(api.myProjects.create).mockReset().mockResolvedValue({ id: "p1" } as never);
  routerCalls.push.mockReset();
  return () => {
    act(() => root.unmount());
    container.remove();
  };
});

describe("create page, AI path", () => {
  it("previews a pasted reply and creates the draft with all of it", async () => {
    await mount();
    await click(button("Fill it in with AI"));
    await paste(REPLY);

    expect(container.textContent).toContain("This is what we'll fill in");
    expect(container.textContent).toContain("Does a thing");
    expect(container.textContent).toContain('Tag "Blockchain" doesn\'t exist here');

    await click(button("Create draft with these details"));

    expect(api.myProjects.create).toHaveBeenCalledWith({
      website_url: "https://example.is",
      title: "Example",
      tagline: "Does a thing",
      description: "It does a thing.",
      tag_ids: ["t-oss"],
      is_community_tipoff: false,
    });
    expect(routerCalls.push).toHaveBeenCalledWith("/my-projects/p1");
  });

  it("explains what is wrong and keeps create disabled", async () => {
    await mount();
    await click(button("Fill it in with AI"));
    await paste('{"title": "No url"}');

    expect(container.querySelector('[role="alert"]')?.textContent).toContain('"website_url" is missing.');
    expect(button("Create draft with these details").disabled).toBe(true);
  });

  it("carries the tipoff choice through", async () => {
    await mount();
    await click(button("Fill it in with AI"));
    await paste(REPLY);
    await click(container.querySelector<HTMLInputElement>("#ownership-tipoff")!);
    await click(button("Create draft with these details"));

    expect(vi.mocked(api.myProjects.create).mock.calls[0][0]).toMatchObject({
      is_community_tipoff: true,
    });
  });

  it("still works when the tag list fails to load", async () => {
    vi.mocked(api.tags.listGrouped).mockRejectedValue(new Error("down"));
    await mount();
    await click(button("Fill it in with AI"));
    await paste(REPLY);
    await click(button("Create draft with these details"));

    expect(vi.mocked(api.myProjects.create).mock.calls[0][0]).toMatchObject({ tag_ids: [] });
  });

  it("copies a prompt that lists the tags", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await mount();
    await click(button("Fill it in with AI"));
    await click(button("Copy prompt"));

    expect(writeText.mock.calls[0][0]).toContain("Type: Open source");
    expect(button("Copied!")).toBeTruthy();
  });

  it("keeps the plain link form as the default", async () => {
    await mount();
    expect(container.querySelector("#url")).not.toBeNull();
    expect(container.querySelector("#ai-output")).toBeNull();
  });
});
