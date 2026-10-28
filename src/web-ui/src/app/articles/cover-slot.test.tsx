import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { CropRect } from "@/components/CroppedImage";
import { CoverSlot } from "./CoverSlot";

const CROP: CropRect = { x: 0, y: 0.1, w: 1, h: 0.6, ratio: 16 / 9 };

function handlers() {
  return { onPick: vi.fn(), onRemove: vi.fn() };
}

async function mount(props: React.ComponentProps<typeof CoverSlot>) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<CoverSlot {...props} />);
  });
  return {
    container,
    cleanup: () => {
      act(() => root.unmount());
      container.remove();
    },
  };
}

function click(container: HTMLElement, label: string) {
  const button = Array.from(container.querySelectorAll("button")).find((b) =>
    b.textContent?.includes(label),
  );
  if (!button) throw new Error(`no button labelled ${label}`);
  act(() => button.click());
}

describe("CoverSlot", () => {
  it("offers to add a cover when the article has none", async () => {
    const h = handlers();
    const { container, cleanup } = await mount({
      imageUrl: null,
      crop: null,
      ...h,
    });

    click(container, "Add a cover image");

    expect(h.onPick).toHaveBeenCalled();
    cleanup();
  });

  it("renders the cover as the page will, with change and remove", async () => {
    const h = handlers();
    const { container, cleanup } = await mount({
      imageUrl: "https://cdn.example/one.png",
      crop: CROP,
      ...h,
    });

    const image = container.querySelector('[data-testid="article-listing-image"] img');
    expect(image?.getAttribute("src")).toBe("https://cdn.example/one.png");

    click(container, "Remove cover");
    expect(h.onRemove).toHaveBeenCalled();
    click(container, "Change");
    expect(h.onPick).toHaveBeenCalled();
    cleanup();
  });
});
