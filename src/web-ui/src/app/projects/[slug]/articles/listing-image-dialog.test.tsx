import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { CropRect } from "@/components/CroppedImage";
import type { ProjectImage } from "@/lib/api";
import { ListingImageDialog } from "./ListingImageDialog";

vi.mock("@/lib/api", () => ({
  api: { myProjects: { deleteImage: vi.fn(() => Promise.resolve()) } },
}));

const uploadHandlers: {
  onUploadComplete?: (image: ProjectImage) => void;
} = {};

vi.mock("@/hooks/useImageUpload", () => ({
  useImageUpload: (options: {
    onUploadComplete?: (image: ProjectImage) => void;
  }) => {
    uploadHandlers.onUploadComplete = options.onUploadComplete;
    return { uploadFile: vi.fn(), isUploading: false };
  },
}));

const { api } = await import("@/lib/api");

// ------------------------------------------------------------------ harness

// The cropper measures its stage and observes resizes; jsdom lays nothing out.
beforeAll(() => {
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get: () => 600,
  });
});

beforeEach(() => {
  vi.clearAllMocks();
});

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

async function click(el: Element) {
  await act(async () => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function buttonLabelled(container: HTMLElement, label: string): HTMLElement {
  return [...container.querySelectorAll("button")].find(
    (b) => b.textContent?.trim() === label,
  )!;
}

function thumbnails(container: HTMLElement): HTMLElement[] {
  return [...container.querySelectorAll<HTMLElement>("button[aria-pressed]")];
}

// --------------------------------------------------------------- factories

function image(id: string, overrides: Partial<ProjectImage> = {}): ProjectImage {
  return {
    id,
    url: `https://cdn.example/${id}.png`,
    original_filename: `${id}.png`,
    width: 4000,
    height: 2000,
    variants: [],
    ...overrides,
  } as unknown as ProjectImage;
}

const STORED_CROP: CropRect = {
  x: 0.1,
  y: 0.2,
  w: 0.4,
  h: 0.225,
  ratio: 16 / 9,
};

function dialog(
  overrides: Partial<React.ComponentProps<typeof ListingImageDialog>> = {},
) {
  return (
    <ListingImageDialog
      projectId="p1"
      articleId="a1"
      images={[image("one"), image("two")]}
      currentImageId={null}
      currentCrop={null}
      onConfirm={() => {}}
      onRemove={() => {}}
      onClose={() => {}}
      {...overrides}
    />
  );
}

// ---------------------------------------------------------------- the tests

describe("ListingImageDialog", () => {
  it("offers every image uploaded for the article", async () => {
    const { container, unmount: cleanup } = await mount(dialog());

    expect(thumbnails(container)).toHaveLength(2);

    cleanup();
  });

  it("does not offer an image with no recorded dimensions", async () => {
    const { container, unmount: cleanup } = await mount(
      dialog({
        images: [image("one"), image("two", { width: null, height: null })],
      }),
    );

    expect(thumbnails(container)).toHaveLength(1);

    cleanup();
  });

  it("marks the current selection", async () => {
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "two" }),
    );

    const pressed = thumbnails(container).filter(
      (b) => b.getAttribute("aria-pressed") === "true",
    );
    expect(pressed).toHaveLength(1);
    expect(pressed[0].getAttribute("title")).toBe("two.png");

    cleanup();
  });

  it("keeps the stored framing when the current image is re-picked", async () => {
    const onConfirm = vi.fn();
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "one", currentCrop: STORED_CROP, onConfirm }),
    );

    await click(buttonLabelled(container, "Next"));
    await click(buttonLabelled(container, "Use it"));

    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ id: "one" }),
      STORED_CROP,
    );

    cleanup();
  });

  it("resets the framing when a different image is picked", async () => {
    const onConfirm = vi.fn();
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "one", currentCrop: STORED_CROP, onConfirm }),
    );

    await click(thumbnails(container)[1]);
    await click(buttonLabelled(container, "Next"));
    await click(buttonLabelled(container, "Use it"));

    const [chosen, crop] = onConfirm.mock.calls[0];
    expect(chosen.id).toBe("two");
    // A centred default rather than a rectangle drawn on the other image.
    expect(crop).not.toEqual(STORED_CROP);
    expect(crop.x + crop.w / 2).toBeCloseTo(0.5, 4);
    expect(crop.ratio).toBeCloseTo(16 / 9, 4);

    cleanup();
  });

  it("goes back to the selection step with the selection intact", async () => {
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "two" }),
    );

    await click(buttonLabelled(container, "Next"));
    await click(buttonLabelled(container, "Back"));

    const pressed = thumbnails(container).filter(
      (b) => b.getAttribute("aria-pressed") === "true",
    );
    expect(pressed[0].getAttribute("title")).toBe("two.png");

    cleanup();
  });

  it("changes nothing when cancelled", async () => {
    const onConfirm = vi.fn();
    const onRemove = vi.fn();
    const onClose = vi.fn();
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "one", onConfirm, onRemove, onClose }),
    );

    await click(thumbnails(container)[1]);
    await click(buttonLabelled(container, "Cancel"));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(onRemove).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledOnce();

    cleanup();
  });

  it("offers an image uploaded in the wizard, and frames it straight away", async () => {
    const { container, unmount: cleanup } = await mount(dialog());

    await act(async () => {
      uploadHandlers.onUploadComplete!(image("fresh"));
    });
    expect(buttonLabelled(container, "Use it")).toBeDefined();

    await click(buttonLabelled(container, "Back"));

    expect(thumbnails(container)).toHaveLength(3);
    const pressed = thumbnails(container).filter(
      (b) => b.getAttribute("aria-pressed") === "true",
    );
    expect(pressed[0].getAttribute("title")).toBe("fresh.png");

    cleanup();
  });

  it("deletes an upload the article never adopted", async () => {
    const { container, unmount: cleanup } = await mount(dialog());

    await act(async () => {
      uploadHandlers.onUploadComplete!(image("fresh"));
    });
    await click(buttonLabelled(container, "Cancel"));

    expect(api.myProjects.deleteImage).toHaveBeenCalledWith("p1", "fresh");

    cleanup();
  });

  it("removes the image without going through the framing step", async () => {
    const onRemove = vi.fn();
    const { container, unmount: cleanup } = await mount(
      dialog({ currentImageId: "one", onRemove }),
    );

    await click(buttonLabelled(container, "Remove image"));

    expect(onRemove).toHaveBeenCalledOnce();

    cleanup();
  });
});
