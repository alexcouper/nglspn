import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { User } from "@/lib/api";

const { authState, router } = vi.hoisted(() => ({
  authState: {
    value: {
      user: null as User | null,
      isAuthenticated: true,
      isLoading: false,
      refreshUser: vi.fn(),
    },
  },
  router: { push: vi.fn() },
}));

vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));
vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => ({ isLoading: false, isReady: true }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api", () => ({
  api: {
    auth: {
      updateCurrentUser: vi.fn(),
      removeAvatar: vi.fn(),
      getAvatarUploadUrl: vi.fn(),
      completeAvatarUpload: vi.fn(),
    },
  },
}));
vi.mock("@/lib/avatarBlob", () => {
  class NotAnImageError extends Error {}
  return {
    NotAnImageError,
    loadImageFile: vi.fn(),
    renderAvatarBlob: vi.fn(),
  };
});
vi.mock("@/lib/avatarUpload", () => ({ uploadAvatar: vi.fn() }));

const { api } = await import("@/lib/api");
const { loadImageFile, NotAnImageError } = await import("@/lib/avatarBlob");
const { default: ProfilePage } = await import("./page");

// ------------------------------------------------------------------ mounting

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

// --------------------------------------------------------------- factories

function user(overrides: Partial<User> = {}): User {
  return {
    id: "user-1",
    email: "sigrun@example.is",
    first_name: "Sigrún",
    last_name: "Helgadóttir",
    info: "Landscape architect in **Vesturbær**.",
    is_verified: true,
    is_system_user: false,
    avatar_url: null,
    created_at: "2025-03-12T10:00:00Z",
    groups: [],
    opt_in_to_external_promotions: true,
    discussion_email_frequency: "hourly",
    article_email_frequency: "hourly",
    pending_onboarding_steps: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------- helpers

function typeInto(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), "value")!.set!;
  setter.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

function buttonNamed(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find((b) =>
    b.textContent?.trim() === label,
  ) as HTMLButtonElement;
}

async function click(el: Element | undefined) {
  expect(el).toBeDefined();
  await act(async () => {
    (el as HTMLElement).click();
  });
}

function field(container: HTMLElement, id: string) {
  return container.querySelector(`#${id}`) as HTMLInputElement | HTMLTextAreaElement;
}

function alertText(container: HTMLElement): string {
  return [...container.querySelectorAll('[role="alert"]')].map((el) => el.textContent).join(" ");
}

// ---------------------------------------------------------------- the tests

describe("the profile edit page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.value = {
      user: user(),
      isAuthenticated: true,
      isLoading: false,
      refreshUser: vi.fn().mockResolvedValue(null),
    };
    vi.mocked(api.auth.updateCurrentUser).mockResolvedValue(user());
  });

  it("saves the three public fields and returns to the public page", async () => {
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    await act(async () => {
      typeInto(field(container, "info"), "Something new.");
    });
    await click(buttonNamed(container, "Save changes"));

    expect(api.auth.updateCurrentUser).toHaveBeenCalledWith({
      first_name: "Sigrún",
      last_name: "Helgadóttir",
      info: "Something new.",
    });
    expect(authState.value.refreshUser).toHaveBeenCalled();
    expect(router.push).toHaveBeenCalledWith("/users/user-1");
    cleanup();
  });

  it("cancels back to the public page without saving", async () => {
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    const cancel = [...container.querySelectorAll("a")].find(
      (a) => a.textContent?.trim() === "Cancel",
    );
    expect(cancel?.getAttribute("href")).toBe("/users/user-1");
    expect(api.auth.updateCurrentUser).not.toHaveBeenCalled();
    cleanup();
  });

  it("refuses to save with both names empty", async () => {
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    await act(async () => {
      typeInto(field(container, "firstName"), "");
      typeInto(field(container, "lastName"), "   ");
    });
    await click(buttonNamed(container, "Save changes"));

    expect(alertText(container)).toContain("At least one name");
    expect(api.auth.updateCurrentUser).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
    cleanup();
  });

  it("previews the About text with the public renderer, images excluded", async () => {
    authState.value.user = user({ info: "Hello **there** ![x](https://example.com/a.png)" });
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    await click(buttonNamed(container, "Preview"));

    const preview = container.querySelector('[data-testid="about-preview"]')!;
    expect(preview.querySelector("strong")?.textContent).toBe("there");
    expect(preview.querySelector("img")).toBeNull();
    expect(container.querySelector("#info")).toBeNull();
    cleanup();
  });

  it("removes the avatar and refreshes the user", async () => {
    authState.value.user = user({ avatar_url: "https://cdn.example/a.jpg" });
    vi.mocked(api.auth.removeAvatar).mockResolvedValue(user());
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    await click(buttonNamed(container, "Remove"));

    expect(api.auth.removeAvatar).toHaveBeenCalled();
    expect(authState.value.refreshUser).toHaveBeenCalled();
    cleanup();
  });

  it("offers no Remove without an avatar", async () => {
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    expect(buttonNamed(container, "Remove")).toBeUndefined();
    cleanup();
  });

  it("reports a file that is not an image and makes no request", async () => {
    vi.mocked(loadImageFile).mockRejectedValue(new NotAnImageError("That file is not an image we can read."));
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    const input = container.querySelector("#avatar-file") as HTMLInputElement;
    const file = new File(["nope"], "notes.txt", { type: "text/plain" });
    await act(async () => {
      Object.defineProperty(input, "files", { value: [file], configurable: true });
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    expect(alertText(container)).toContain("not an image");
    expect(api.auth.getAvatarUploadUrl).not.toHaveBeenCalled();
    cleanup();
  });

  it("links to the account settings page", async () => {
    const { container, unmount: cleanup } = await mount(<ProfilePage />);

    expect(container.querySelector('a[href="/profile/settings"]')).not.toBeNull();
    cleanup();
  });
});
