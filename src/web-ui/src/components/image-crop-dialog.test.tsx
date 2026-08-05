import { describe, expect, it, vi, beforeAll } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { ImageCropDialog } from "./ImageCropDialog";
import type { CropRect } from "./CroppedImage";

// ------------------------------------------------------------------ harness

const FRAME_WIDTH = 800;
// 4000x2000: wider than 16:9, so a full-width selection cannot reach 16:9 and
// the dialog has to zoom in. Exercises the joint scale/ratio constraint.
const SOURCE = { naturalWidth: 4000, naturalHeight: 2000 };

// Assigned rather than vi.stubGlobal'd: the shared setup calls
// vi.unstubAllGlobals() after every test, which would strip these after the
// first one. jsdom lays nothing out, so the frame's measured width is faked too.
beforeAll(() => {
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get(this: HTMLElement) {
      return this.dataset?.testid === "crop-frame" ? FRAME_WIDTH : 0;
    },
  });
  HTMLElement.prototype.setPointerCapture = () => {};
});

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

function openDialog(props: Partial<Parameters<typeof ImageCropDialog>[0]> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  return {
    onConfirm,
    onCancel,
    element: (
      <ImageCropDialog
        isOpen
        src="/hero.png"
        {...SOURCE}
        onConfirm={onConfirm}
        onCancel={onCancel}
        {...props}
      />
    ),
  };
}

function byTestId(container: HTMLElement, id: string): HTMLElement {
  return container.querySelector(`[data-testid="${id}"]`) as HTMLElement;
}

async function pointerDrag(target: HTMLElement, from: number, to: number) {
  await act(async () => {
    target.dispatchEvent(pointerEvent("pointerdown", from));
    target.dispatchEvent(pointerEvent("pointermove", to));
    target.dispatchEvent(pointerEvent("pointerup", to));
  });
}

function pointerEvent(type: string, clientY: number, clientX = 0) {
  const event = new Event(type, { bubbles: true }) as PointerEvent & {
    clientX: number;
    clientY: number;
    pointerId: number;
  };
  Object.assign(event, { clientX, clientY, pointerId: 1 });
  return event;
}

function confirmedCrop(onConfirm: ReturnType<typeof vi.fn>): CropRect {
  return onConfirm.mock.calls[0][0] as CropRect;
}

async function clickButton(container: HTMLElement, label: string) {
  const button = [...container.querySelectorAll("button")].find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  await act(async () => {
    button!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function ratioOf(container: HTMLElement): number {
  return Number(byTestId(container, "crop-frame").style.aspectRatio);
}

// ---------------------------------------------------------------- the tests

describe("ImageCropDialog", () => {
  it("opens on the largest 16:9 the source allows", async () => {
    const { element, onConfirm } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    expect(ratioOf(container)).toBeCloseTo(16 / 9, 4);
    await clickButton(container, "Use it");

    const crop = confirmedCrop(onConfirm);
    // A 4000x2000 source cannot show 16:9 across its full width, so the
    // selection is narrower than the whole image but uses its full height.
    expect(crop.h).toBeCloseTo(1, 4);
    expect(crop.w).toBeLessThan(1);
    expect(crop.ratio).toBeCloseTo(16 / 9, 4);

    cleanup();
  });

  it("keeps the selection inside the source when panning", async () => {
    const { element, onConfirm } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    // Drag far further than the image allows in both directions.
    await pointerDrag(byTestId(container, "crop-frame"), 500, -4000);
    await clickButton(container, "Use it");

    const crop = confirmedCrop(onConfirm);
    expect(crop.x).toBeGreaterThanOrEqual(0);
    expect(crop.y).toBeGreaterThanOrEqual(0);
    expect(crop.x + crop.w).toBeLessThanOrEqual(1.000001);
    expect(crop.y + crop.h).toBeLessThanOrEqual(1.000001);

    cleanup();
  });

  it("makes the selection taller when the bottom edge is dragged down", async () => {
    const { element } = openDialog();
    const { container, unmount: cleanup } = await mount(element);
    const before = ratioOf(container);

    await pointerDrag(byTestId(container, "crop-handle-bottom"), 0, 60);

    expect(ratioOf(container)).toBeLessThan(before);

    cleanup();
  });

  it("stops at 1:1 however far the edge is dragged", async () => {
    const { element } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    await pointerDrag(byTestId(container, "crop-handle-bottom"), 0, 5000);

    expect(ratioOf(container)).toBeCloseTo(1, 4);

    cleanup();
  });

  it("stops at 4:1 however far the edge is dragged the other way", async () => {
    const { element } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    await pointerDrag(byTestId(container, "crop-handle-bottom"), 5000, 0);

    expect(ratioOf(container)).toBeCloseTo(4, 4);

    cleanup();
  });

  it("shows the selection's reduced ratio", async () => {
    const { element } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    await pointerDrag(byTestId(container, "crop-handle-bottom"), 0, 5000);

    expect(byTestId(container, "crop-ratio").textContent).toBe("1 : 1");

    cleanup();
  });

  it("hides the edge handles and holds the ratio when one is locked", async () => {
    const { element, onConfirm } = openDialog({ lockRatio: 16 / 9 });
    const { container, unmount: cleanup } = await mount(element);

    expect(byTestId(container, "crop-handle-top")).toBeNull();
    expect(byTestId(container, "crop-handle-bottom")).toBeNull();

    await clickButton(container, "Use it");
    expect(confirmedCrop(onConfirm).ratio).toBeCloseTo(16 / 9, 4);

    cleanup();
  });

  it("starts from a stored selection rather than recentring it", async () => {
    const initial: CropRect = { x: 0.2, y: 0, w: 0.4, h: 0.8, ratio: 2 };
    const { element, onConfirm } = openDialog({ initial });
    const { container, unmount: cleanup } = await mount(element);

    await clickButton(container, "Use it");

    const crop = confirmedCrop(onConfirm);
    expect(crop.w).toBeCloseTo(0.4, 4);
    expect(crop.x).toBeCloseTo(0.2, 4);
    expect(crop.ratio).toBeCloseTo(2, 4);

    cleanup();
  });

  it("warns when the selection is too small to render sharply", async () => {
    const { element } = openDialog({ naturalWidth: 700, naturalHeight: 700 });
    const { container, unmount: cleanup } = await mount(element);

    expect(container.textContent).toContain("will look soft");

    cleanup();
  });

  it("does not warn when the selection is wide enough in the original", async () => {
    const { element } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    expect(container.textContent).not.toContain("will look soft");

    cleanup();
  });

  it("emits nothing on cancel", async () => {
    const { element, onConfirm, onCancel } = openDialog();
    const { container, unmount: cleanup } = await mount(element);

    await clickButton(container, "Cancel");

    expect(onCancel).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();

    cleanup();
  });
});
