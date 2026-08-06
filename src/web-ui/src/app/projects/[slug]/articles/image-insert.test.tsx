import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { buildAltTextSavePayload } from "./buildAltTextSavePayload";
import { ImageAltDialog } from "./ImageAltDialog";
import { useImageUploadStatus } from "./useImageUploadStatus";

vi.mock("@/lib/uploadProjectImage", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/uploadProjectImage")
  >("@/lib/uploadProjectImage");
  return { ...actual, uploadProjectImage: vi.fn() };
});

const { uploadProjectImage } = await import("@/lib/uploadProjectImage");
const uploadMock = vi.mocked(uploadProjectImage);

// ---------------------------------------------------------------- factories

function editingImage(
  overrides: Partial<{
    src: string;
    altText: string;
    title: string;
  }> = {},
) {
  return {
    src: "https://images.naglasupan.is/projects/abc/hero.png",
    altText: "",
    title: "",
    ...overrides,
  };
}

function projectImage(url: string) {
  return { url } as Awaited<ReturnType<typeof uploadProjectImage>>;
}

function imageFile(name = "screenshot.png") {
  return new File(["binary"], name, { type: "image/png" });
}

// ------------------------------------------------------------------ mounting

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

function altInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector<HTMLInputElement>("input#image-alt");
  if (!input) throw new Error("alt text input not found");
  return input;
}

function buttonLabelled(container: HTMLElement, label: string) {
  const button = Array.from(container.querySelectorAll("button")).find(
    (b) => b.textContent?.trim() === label,
  );
  if (!button) throw new Error(`no button labelled "${label}"`);
  return button;
}

async function typeInto(input: HTMLInputElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )!.set!;
  await act(async () => {
    setValue.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function click(element: Element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

// --------------------------------------------------------- hook test harness

function renderUploadStatus(projectId: string, articleId = "article-1") {
  const captured = {} as ReturnType<typeof useImageUploadStatus>;

  function Harness() {
    Object.assign(captured, useImageUploadStatus(projectId, articleId));
    return null;
  }

  return { captured, mounted: mount(<Harness />) };
}

// ---------------------------------------------------------------- the tests

describe("buildAltTextSavePayload", () => {
  it("echoes the existing src back so saving does not blank the image", () => {
    const payload = buildAltTextSavePayload(
      editingImage({ src: "https://cdn/one.png" }),
      "A screenshot",
    );

    expect(payload.src).toBe("https://cdn/one.png");
  });

  it("echoes the existing title back so saving does not blank it", () => {
    const payload = buildAltTextSavePayload(
      editingImage({ title: "Figure 1" }),
      "A screenshot",
    );

    expect(payload.title).toBe("Figure 1");
  });

  it("substitutes an empty string for a missing title", () => {
    const payload = buildAltTextSavePayload({ src: "https://cdn/one.png" }, "");

    expect(payload.title).toBe("");
  });

  it("replaces the alt text with the edited value", () => {
    const payload = buildAltTextSavePayload(
      editingImage({ altText: "old" }),
      "new",
    );

    expect(payload.altText).toBe("new");
  });
});

describe("ImageAltDialog", () => {
  it("prefills the field with the image's current alt text", async () => {
    const { container, unmount } = await mount(
      <ImageAltDialog initialAltText="Existing alt" onSave={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(altInput(container).value).toBe("Existing alt");

    unmount();
  });

  it("saves the edited alt text", async () => {
    const onSave = vi.fn();
    const { container, unmount } = await mount(
      <ImageAltDialog initialAltText="" onSave={onSave} onCancel={vi.fn()} />,
    );

    await typeInto(altInput(container), "A wide screenshot of the dashboard");
    await click(buttonLabelled(container, "Save"));

    expect(onSave).toHaveBeenCalledWith("A wide screenshot of the dashboard");

    unmount();
  });

  it("cancels without saving", async () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    const { container, unmount } = await mount(
      <ImageAltDialog initialAltText="Existing alt" onSave={onSave} onCancel={onCancel} />,
    );

    await typeInto(altInput(container), "discarded");
    await click(buttonLabelled(container, "Cancel"));

    expect(onCancel).toHaveBeenCalled();
    expect(onSave).not.toHaveBeenCalled();

    unmount();
  });
});

describe("useImageUploadStatus", () => {
  it("reports uploading while the upload is in flight", async () => {
    let resolveUpload!: (value: { url: string }) => void;
    uploadMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve as (value: { url: string }) => void;
      }),
    );
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    let uploading!: Promise<string>;
    await act(async () => {
      uploading = captured.uploadImage(imageFile());
    });

    expect(captured.status).toEqual({ kind: "uploading" });

    await act(async () => {
      resolveUpload(projectImage("https://cdn/uploaded.png"));
      await uploading;
    });

    unmount();
  });

  it("returns the uploaded url and goes back to idle on success", async () => {
    uploadMock.mockResolvedValue(projectImage("https://cdn/uploaded.png"));
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    let url!: string;
    await act(async () => {
      url = await captured.uploadImage(imageFile());
    });

    expect(url).toBe("https://cdn/uploaded.png");
    expect(captured.status).toEqual({ kind: "idle" });

    unmount();
  });

  it("surfaces the failure message instead of swallowing it", async () => {
    uploadMock.mockRejectedValue(new Error("File size must be less than 10MB"));
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    await act(async () => {
      await expect(captured.uploadImage(imageFile())).rejects.toThrow();
    });

    expect(captured.status).toEqual({
      kind: "error",
      message: "File size must be less than 10MB",
    });

    unmount();
  });

  it("falls back to a generic message when the failure has none", async () => {
    uploadMock.mockRejectedValue("something odd");
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    await act(async () => {
      await expect(captured.uploadImage(imageFile())).rejects.toBeDefined();
    });

    expect(captured.status).toEqual({
      kind: "error",
      message: "Image upload failed",
    });

    unmount();
  });

  it("clears the error when dismissed", async () => {
    uploadMock.mockRejectedValue(new Error("network down"));
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    await act(async () => {
      await expect(captured.uploadImage(imageFile())).rejects.toThrow();
    });
    await act(async () => {
      captured.dismissError();
    });

    expect(captured.status).toEqual({ kind: "idle" });

    unmount();
  });
});

describe("article image source", () => {
  it("tags inline body uploads as article-sourced so they stay off the project page", async () => {
    uploadMock.mockResolvedValue(projectImage("https://cdn/uploaded.png"));
    const { captured, mounted } = renderUploadStatus("project-1");
    const { unmount } = await mounted;

    await act(async () => {
      await captured.uploadImage(imageFile());
    });

    expect(uploadMock).toHaveBeenCalledWith(
      "project-1",
      expect.any(File),
      expect.objectContaining({ source: "article" }),
    );

    unmount();
  });
});
