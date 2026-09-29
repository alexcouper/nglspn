import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { ReportProblemDialog } from "./ReportProblemDialog";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";

const authState = vi.hoisted(() => ({
  value: { user: null as { email: string } | null },
}));

vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));
vi.mock("@/lib/api", () => ({
  api: { projects: { report: vi.fn() } },
}));

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

function renderDialog({ hasMakers = true } = {}) {
  return mount(
    <ReportProblemDialog
      isOpen
      onClose={() => {}}
      projectSlugOrId="dead-app"
      projectTitle="Dead App"
      hasMakers={hasMakers}
    />,
  );
}

function submitButton(container: HTMLElement) {
  return Array.from(container.querySelectorAll("button")).find(
    (b) => b.textContent === "Send report",
  ) as HTMLButtonElement;
}

async function choose(container: HTMLElement, reason: string) {
  const radio = container.querySelector(
    `input[value="${reason}"]`,
  ) as HTMLInputElement;
  await act(async () => radio.click());
}

async function type(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = Object.getPrototypeOf(el);
  const setter = Object.getOwnPropertyDescriptor(proto, "value")!.set!;
  await act(async () => {
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function submit(container: HTMLElement) {
  await act(async () => submitButton(container).click());
}

describe("ReportProblemDialog", () => {
  beforeEach(() => {
    authState.value = { user: null };
    vi.mocked(api.projects.report).mockReset();
    vi.mocked(api.projects.report).mockResolvedValue({
      id: "r1",
      reason: "site_down",
      created_at: "2026-09-29T00:00:00Z",
    });
  });

  it("renders nothing when closed", async () => {
    const { container, unmount: cleanup } = await mount(
      <ReportProblemDialog
        isOpen={false}
        onClose={() => {}}
        projectSlugOrId="dead-app"
        projectTitle="Dead App"
        hasMakers
      />,
    );
    expect(container.querySelector("form")).toBeNull();
    cleanup();
  });

  it("can't be sent until a reason is picked", async () => {
    const { container, unmount: cleanup } = await renderDialog();
    expect(submitButton(container).disabled).toBe(true);

    await choose(container, "wrong_link");

    expect(submitButton(container).disabled).toBe(false);
    cleanup();
  });

  it("sends the reason, details and contact address, then thanks", async () => {
    const { container, unmount: cleanup } = await renderDialog();
    await choose(container, "something_broken");
    await type(
      container.querySelector("#report-details") as HTMLTextAreaElement,
      "  Login fails  ",
    );
    await type(
      container.querySelector("#report-contact") as HTMLInputElement,
      "visitor@example.com",
    );

    await submit(container);

    expect(api.projects.report).toHaveBeenCalledWith("dead-app", {
      reason: "something_broken",
      details: "Login fails",
      contact_email: "visitor@example.com",
    });
    expect(container.textContent).toContain("Thanks for letting them know");
    expect(container.textContent).toContain("the makers hear about it");
    cleanup();
  });

  it("does not share a signed-in visitor's address unless they opt in", async () => {
    authState.value = { user: { email: "me@example.com" } };
    const { container, unmount: cleanup } = await renderDialog();
    expect(container.querySelector("#report-contact")).toBeNull();
    await choose(container, "site_down");

    await submit(container);

    expect(vi.mocked(api.projects.report).mock.calls[0][1].contact_email).toBe(
      "",
    );
    cleanup();
  });

  it("shares a signed-in visitor's address when they tick the box", async () => {
    authState.value = { user: { email: "me@example.com" } };
    const { container, unmount: cleanup } = await renderDialog();
    await choose(container, "site_down");
    const checkbox = container.querySelector(
      'input[type="checkbox"]',
    ) as HTMLInputElement;
    await act(async () => checkbox.click());

    await submit(container);

    expect(vi.mocked(api.projects.report).mock.calls[0][1].contact_email).toBe(
      "me@example.com",
    );
    cleanup();
  });

  it("explains a rate limit rather than failing silently", async () => {
    vi.mocked(api.projects.report).mockRejectedValue(
      new ApiRequestError("Too many requests", {}, 429),
    );
    const { container, unmount: cleanup } = await renderDialog();
    await choose(container, "site_down");

    await submit(container);

    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      "try again later",
    );
    expect(submitButton(container).disabled).toBe(false);
    cleanup();
  });

  it("tells the visitor an unclaimed project's report goes to the team", async () => {
    const { container, unmount: cleanup } = await renderDialog({
      hasMakers: false,
    });

    expect(container.textContent).toContain("has no maker on Naglasúpan");
    expect(container.textContent).toContain(
      "Only shared with the Naglasúpan team",
    );
    expect(container.textContent).not.toContain("shared with the makers");
    cleanup();
  });
});
