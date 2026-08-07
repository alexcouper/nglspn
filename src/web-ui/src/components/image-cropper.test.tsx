import { describe, expect, it, beforeAll } from "vitest";
import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { ImageCropper, defaultCrop, zoomToSlider } from "./ImageCropper";
import type { CropRect } from "./CroppedImage";

// ------------------------------------------------------------------ harness

const STAGE_WIDTH = 600;
// Wider than 16:9, so a full-width selection cannot cover a 16:9 box — the case
// where zooming out leaves background showing.
const SOURCE = { naturalWidth: 4000, naturalHeight: 2000 };
// The only shape the cropper produces now: a listing card.
const CARD_RATIO = 16 / 9;

// Assigned rather than vi.stubGlobal'd: the shared setup calls
// vi.unstubAllGlobals() after every test, which would strip these after the
// first one. jsdom lays nothing out, so the stage's width is faked too.
beforeAll(() => {
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get(this: HTMLElement) {
      return this.dataset?.testid === "crop-stage" ? STAGE_WIDTH : 0;
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

// The cropper is controlled, so tests drive it through a tiny stateful host and
// read the latest crop out of a ref rather than re-deriving it.
function Harness({
  onCrop,
  ...props
}: { onCrop: (crop: CropRect) => void } & Partial<
  Parameters<typeof ImageCropper>[0]
>) {
  const [crop, setCrop] = useState<CropRect | null>(props.value ?? null);
  return (
    <ImageCropper
      src="/listing.png"
      lockRatio={CARD_RATIO}
      {...SOURCE}
      {...props}
      value={crop}
      onChange={(next) => {
        setCrop(next);
        onCrop(next);
      }}
    />
  );
}

async function mountCropper(
  props: Partial<Parameters<typeof ImageCropper>[0]> = {},
) {
  const withRatio = { lockRatio: CARD_RATIO, ...props };
  const crops: CropRect[] = [];
  const mounted = await mount(
    <Harness onCrop={(crop) => crops.push(crop)} {...withRatio} />,
  );
  return { ...mounted, crops, latest: () => crops[crops.length - 1] };
}

function byTestId(container: HTMLElement, id: string): HTMLElement {
  return container.querySelector(`[data-testid="${id}"]`) as HTMLElement;
}

function pointerEvent(type: string, clientX: number, clientY: number) {
  const event = new Event(type, { bubbles: true }) as PointerEvent & {
    clientX: number;
    clientY: number;
    pointerId: number;
  };
  Object.assign(event, { clientX, clientY, pointerId: 1 });
  return event;
}

async function drag(
  target: HTMLElement,
  from: { x: number; y: number },
  to: { x: number; y: number },
) {
  await act(async () => {
    target.dispatchEvent(pointerEvent("pointerdown", from.x, from.y));
    target.dispatchEvent(pointerEvent("pointermove", to.x, to.y));
    target.dispatchEvent(pointerEvent("pointerup", to.x, to.y));
  });
}

// The slider's track is logarithmic, so a zoom has to be converted to a
// position before it can be typed in.
async function setZoom(
  container: HTMLElement,
  zoom: number,
  src = source(),
) {
  const slider = container.querySelector(
    'input[type="range"]',
  ) as HTMLInputElement;
  const setValue = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )!.set!;
  await act(async () => {
    setValue.call(slider, String(zoomToSlider(zoom, src)));
    slider.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function centreOf(crop: CropRect) {
  return { x: crop.x + crop.w / 2, y: crop.y + crop.h / 2 };
}

// ---------------------------------------------------------------- the tests

describe("defaultCrop", () => {
  it("covers the box with no background showing", () => {
    const crop = defaultCrop(source());

    // A 4000x2000 source is wider than 16:9, so covering means zooming in.
    expect(crop.w).toBeLessThan(1);
    expect(crop.h).toBeCloseTo(1, 4);
    expect(crop.ratio).toBeCloseTo(16 / 9, 4);
  });

  it("is centred on the image", () => {
    const crop = defaultCrop(source());

    expect(centreOf(crop)).toEqual({ x: 0.5, y: 0.5 });
  });
});

describe("ImageCropper", () => {
  it("shows the whole image with the crop box drawn over it", async () => {
    const { container, unmount: cleanup } = await mountCropper();

    expect(byTestId(container, "crop-source")).not.toBeNull();
    expect(byTestId(container, "crop-box")).not.toBeNull();
    expect(byTestId(container, "crop-preview")).not.toBeNull();

    cleanup();
  });

  it("keeps the box the same size on screen while zooming scales the image", async () => {
    const { container, unmount: cleanup } = await mountCropper();
    const box = byTestId(container, "crop-box");
    const before = { width: box.style.width, height: box.style.height };
    const imageBefore = byTestId(container, "crop-source").style.width;

    await setZoom(container, 3);

    expect(box.style.width).toBe(before.width);
    expect(box.style.height).toBe(before.height);
    expect(byTestId(container, "crop-source").style.width).not.toBe(imageBefore);

    cleanup();
  });

  it("narrows the focus as you zoom in", async () => {
    const { container, latest, unmount: cleanup } = await mountCropper();

    await setZoom(container, 2);
    const zoomedIn = latest().w;
    await setZoom(container, 4);

    expect(latest().w).toBeLessThan(zoomedIn);
    expect(latest().w).toBeCloseTo(0.25, 4);

    cleanup();
  });

  it("lets the box sit outside the image when zoomed out", async () => {
    const { container, latest, unmount: cleanup } = await mountCropper();

    await setZoom(container, 0.5);

    // Twice the image's width, so the surround renders as the background.
    expect(latest().w).toBeCloseTo(2, 2);
    expect(latest().x).toBeLessThan(0);

    cleanup();
  });

  it("keeps the crop centred as it zooms rather than drifting", async () => {
    const { container, latest, unmount: cleanup } = await mountCropper();

    await setZoom(container, 1);
    const before = centreOf(latest());
    await setZoom(container, 3);

    expect(centreOf(latest()).x).toBeCloseTo(before.x, 4);
    expect(centreOf(latest()).y).toBeCloseTo(before.y, 4);

    cleanup();
  });

  it("moves the crop the opposite way to a drag, so the image follows the pointer", async () => {
    const { container, latest, unmount: cleanup } = await mountCropper();

    await drag(byTestId(container, "crop-stage"), { x: 300, y: 200 }, { x: 380, y: 200 });

    expect(latest().x).toBeLessThan(0.5);

    cleanup();
  });

  it("holds the fixed shape through a zoom", async () => {
    const { container, latest, unmount: cleanup } = await mountCropper();

    await setZoom(container, 2.5);

    expect(latest().ratio).toBeCloseTo(CARD_RATIO, 4);

    cleanup();
  });

  it("draws no edge handles — the shape is not the author's to change", async () => {
    const { container, unmount: cleanup } = await mountCropper();

    expect(byTestId(container, "crop-handle-top")).toBeNull();
    expect(byTestId(container, "crop-handle-bottom")).toBeNull();

    cleanup();
  });

  it("reports how many source pixels wide the selection is", async () => {
    const { container, unmount: cleanup } = await mountCropper();

    expect(byTestId(container, "crop-source-width").textContent).toMatch(
      /^\d+px$/,
    );

    cleanup();
  });

  it("warns when the selection is too small to render sharply", async () => {
    const { container, unmount: cleanup } = await mountCropper({
      naturalWidth: 700,
      naturalHeight: 700,
    });

    expect(container.textContent).toContain("will look soft");

    cleanup();
  });

  it("does not warn when the selection is wide enough in the original", async () => {
    const { container, unmount: cleanup } = await mountCropper();

    expect(container.textContent).not.toContain("will look soft");

    cleanup();
  });
});

function source(): Parameters<typeof defaultCrop>[0] {
  return {
    width: SOURCE.naturalWidth,
    height: SOURCE.naturalHeight,
    lockRatio: CARD_RATIO,
  };
}
