import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { Avatar, initialsFor } from "./Avatar";

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

function avatarSlot(container: HTMLElement) {
  return container.querySelector('[role="img"], img') as HTMLElement;
}

describe("initialsFor", () => {
  it("takes the first letter of each name", () => {
    expect(initialsFor("Sigrún", "Helgadóttir")).toBe("SH");
  });

  it("copes with one name", () => {
    expect(initialsFor("Sigrún", "")).toBe("S");
    expect(initialsFor("", "Helgadóttir")).toBe("H");
  });

  it("ignores whitespace-only names", () => {
    expect(initialsFor("  ", "Helgadóttir")).toBe("H");
    expect(initialsFor("  ", "")).toBe("");
  });
});

describe("Avatar", () => {
  it("renders the image with the display name as alt text", async () => {
    const { container, unmount: cleanup } = await mount(
      <Avatar src="https://cdn.example/a.jpg" firstName="Sigrún" lastName="Helgadóttir" size={96} />,
    );
    const img = avatarSlot(container) as HTMLImageElement;
    expect(img.tagName).toBe("IMG");
    expect(img.getAttribute("src")).toBe("https://cdn.example/a.jpg");
    expect(img.getAttribute("alt")).toBe("Sigrún Helgadóttir");
    cleanup();
  });

  it("falls back to initials labelled with the display name", async () => {
    const { container, unmount: cleanup } = await mount(
      <Avatar src={null} firstName="Sigrún" lastName="Helgadóttir" size={96} />,
    );
    const slot = avatarSlot(container);
    expect(slot.textContent).toBe("SH");
    expect(slot.getAttribute("aria-label")).toBe("Sigrún Helgadóttir");
    cleanup();
  });

  it("shows a glyph, not empty text, when there is no name", async () => {
    const { container, unmount: cleanup } = await mount(
      <Avatar src={null} firstName="" lastName="" size={48} />,
    );
    const slot = avatarSlot(container);
    expect(slot.textContent).toBe("");
    expect(slot.querySelector("svg")).not.toBeNull();
    expect(slot.getAttribute("aria-label")).toBe("Anonymous");
    cleanup();
  });
});
