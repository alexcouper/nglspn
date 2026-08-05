"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { Dialog } from "./Dialog";
import type { CropRect } from "./CroppedImage";

// A hero wider than 4:1 is a hairline; taller than 1:1 is a tower. Mirrors
// MIN_RATIO/MAX_RATIO in services/articles/crop.py — the server rejects
// anything outside these, so the handles stop here rather than letting the
// author draw something that fails on save.
const MIN_RATIO = 1;
const MAX_RATIO = 4;

// Below the `medium` variant width, so the selection will render soft. A
// warning, not a block: the author may know the image is decorative.
const MIN_SOURCE_WIDTH = 768;

const MAX_ZOOM = 6;

// Dragging an edge by one pixel moves it at both ends, so the selection height
// changes by two.
const EDGE_TO_HEIGHT = 2;

interface Props {
  isOpen: boolean;
  src: string;
  naturalWidth: number;
  naturalHeight: number;
  initial?: CropRect | null;
  // Fixes the frame's shape and hides the handles. 16/9 for listing cards.
  lockRatio?: number;
  title?: string;
  confirmLabel?: string;
  onConfirm: (crop: CropRect) => void;
  onCancel: () => void;
}

// State lives in normalised source coordinates, so confirming is a
// pass-through: there is no conversion step at save time to get wrong.
// `scale` is how much bigger the source is than the frame, so the selection
// width is `1 / scale`.
interface View {
  scale: number;
  centreX: number;
  centreY: number;
  ratio: number;
}

export function ImageCropDialog({
  isOpen,
  src,
  naturalWidth,
  naturalHeight,
  initial,
  lockRatio,
  title = "Choose the framing",
  confirmLabel = "Use it",
  onConfirm,
  onCancel,
}: Props) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [frameWidth, setFrameWidth] = useState(0);
  const source = useMemo(
    () => ({ width: naturalWidth, height: naturalHeight, lockRatio }),
    [naturalWidth, naturalHeight, lockRatio],
  );
  const [view, setView] = useState<View>(() => initialView(initial, source));

  // Swapping the image must not inherit the previous selection. Done during
  // render rather than in an effect: an effect would paint the old crop over
  // the new image for a frame first. Callers mount this only while it is open,
  // so the common reset comes from remounting.
  const [renderedSrc, setRenderedSrc] = useState(src);
  if (src !== renderedSrc) {
    setRenderedSrc(src);
    setView(initialView(initial, source));
  }

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const measure = () => setFrameWidth(frame.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(frame);
    return () => observer.disconnect();
  }, [isOpen]);

  const update = useCallback(
    (change: Partial<View>) =>
      setView((prev) => clampView({ ...prev, ...change }, source)),
    [source],
  );

  const crop = useMemo(() => toCrop(view, source), [view, source]);
  const minScale = minScaleFor(view.ratio, source);

  const pan = useCallback(
    (dx: number, dy: number) =>
      setView((prev) =>
        clampView({ ...prev, centreX: prev.centreX + dx, centreY: prev.centreY + dy }, source),
      ),
    [source],
  );
  const drag = useDrag(pan, frameWidth, view.scale);

  const resizeBy = useCallback(
    (deltaPixels: number) =>
      setView((prev) => resize(prev, deltaPixels, frameWidth, source)),
    [frameWidth, source],
  );

  const selectionPixelWidth = Math.round(crop.w * naturalWidth);
  const isLowResolution = selectionPixelWidth < MIN_SOURCE_WIDTH;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onCancel}
      // Full-screen under `sm`: a crop frame inside a padded modal on a 375px
      // screen leaves nothing to aim at. The column layout keeps the controls
      // pinned — a near-square selection is tall enough to push them off the
      // bottom of the viewport otherwise.
      className="max-w-3xl max-h-[calc(100vh-4rem)] flex flex-col max-sm:rounded-none max-sm:max-h-screen max-sm:min-h-screen"
    >
      <h2 className="text-lg font-semibold text-foreground shrink-0">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground shrink-0">
        Drag to move the image.
        {lockRatio ? "" : " Drag the top or bottom edge to change the shape."}
      </p>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto">
      <div
        ref={frameRef}
        onPointerDown={drag.onPointerDown}
        onPointerMove={drag.onPointerMove}
        onPointerUp={drag.onPointerUp}
        onPointerCancel={drag.onPointerUp}
        onWheel={(event: ReactWheelEvent) =>
          update({ scale: view.scale * (event.deltaY > 0 ? 0.95 : 1.05) })
        }
        style={{ aspectRatio: String(crop.ratio), touchAction: "none" }}
        className="relative w-full overflow-hidden rounded-lg bg-muted cursor-move select-none"
        data-testid="crop-frame"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt=""
          draggable={false}
          style={{
            position: "absolute",
            width: `${100 / crop.w}%`,
            height: `${100 / crop.h}%`,
            left: `${(-crop.x / crop.w) * 100}%`,
            top: `${(-crop.y / crop.h) * 100}%`,
            maxWidth: "none",
          }}
        />
        {!lockRatio && (
          <>
            <EdgeHandle edge="top" onDrag={resizeBy} />
            <EdgeHandle edge="bottom" onDrag={resizeBy} />
          </>
        )}
      </div>
      </div>

      <div className="mt-4 flex shrink-0 items-center gap-4">
        <label className="flex flex-1 items-center gap-2 text-sm text-muted-foreground">
          Zoom
          <input
            type="range"
            min={minScale}
            max={Math.max(minScale, MAX_ZOOM)}
            step={0.01}
            value={view.scale}
            onChange={(event) => update({ scale: Number(event.target.value) })}
            className="flex-1 accent-accent"
            aria-label="Zoom"
          />
        </label>
        <span
          className="text-sm font-medium tabular-nums text-foreground"
          data-testid="crop-ratio"
        >
          {formatRatio(crop.w * naturalWidth, crop.h * naturalHeight)}
        </span>
      </div>

      {isLowResolution && (
        <p className="mt-3 shrink-0 text-sm text-amber-700" role="status">
          This selection is only {selectionPixelWidth}px wide in the original, so
          it will look soft at full width.
        </p>
      )}

      <div className="mt-5 flex shrink-0 justify-end gap-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
        <button
          onClick={() => onConfirm(crop)}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent/90"
        >
          {confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------- geometry

interface Source {
  width: number;
  height: number;
  lockRatio?: number;
}

function initialView(initial: CropRect | null | undefined, source: Source): View {
  if (initial) {
    return clampView(
      {
        scale: 1 / initial.w,
        centreX: initial.x + initial.w / 2,
        centreY: initial.y + initial.h / 2,
        ratio: source.lockRatio ?? initial.ratio,
      },
      source,
    );
  }
  // No stored selection: the largest 16:9 the source allows, centred — which is
  // exactly what an uncropped article already looks like.
  return clampView(
    { scale: 1, centreX: 0.5, centreY: 0.5, ratio: source.lockRatio ?? 16 / 9 },
    source,
  );
}

// The selection must fit inside the source. Its height is
// `(w * W) / (ratio * H)` and `w = 1 / scale`, so h <= 1 requires
// `scale >= W / (ratio * H)`. That is what stops a short, wide image from
// offering a tall crop it cannot fill, and it is the same constraint the
// backend's derive_card_crop resolves by shrinking the width.
function minScaleFor(ratio: number, source: Source): number {
  return Math.max(1, source.width / (ratio * source.height));
}

function clampView(view: View, source: Source): View {
  const ratio = source.lockRatio ?? clamp(view.ratio, MIN_RATIO, MAX_RATIO);
  const minScale = minScaleFor(ratio, source);
  const scale = clamp(view.scale, minScale, Math.max(minScale, MAX_ZOOM));
  const w = 1 / scale;
  const h = (w * source.width) / (ratio * source.height);
  return {
    ratio,
    scale,
    centreX: clamp(view.centreX, w / 2, 1 - w / 2),
    centreY: clamp(view.centreY, h / 2, 1 - h / 2),
  };
}

function toCrop(view: View, source: Source): CropRect {
  const w = 1 / view.scale;
  const h = (w * source.width) / (view.ratio * source.height);
  // clampView already keeps the centre far enough from the edges for the whole
  // selection to sit inside the source, so no clamping is needed here.
  return {
    x: view.centreX - w / 2,
    y: view.centreY - h / 2,
    w,
    h,
    ratio: view.ratio,
  };
}

function resize(
  view: View,
  deltaPixels: number,
  frameWidth: number,
  source: Source,
): View {
  if (!frameWidth) return view;
  const currentHeight = frameWidth / view.ratio;
  const nextHeight = Math.max(1, currentHeight + deltaPixels);
  return clampView({ ...view, ratio: frameWidth / nextHeight }, source);
}

function useDrag(
  pan: (dx: number, dy: number) => void,
  frameWidth: number,
  scale: number,
) {
  const last = useRef<{ x: number; y: number } | null>(null);

  return {
    onPointerDown: (event: ReactPointerEvent) => {
      if ((event.target as HTMLElement).dataset.handle) return;
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
      last.current = { x: event.clientX, y: event.clientY };
    },
    onPointerMove: (event: ReactPointerEvent) => {
      if (!last.current || !frameWidth) return;
      const dx = event.clientX - last.current.x;
      const dy = event.clientY - last.current.y;
      last.current = { x: event.clientX, y: event.clientY };
      // Frame pixels to source fractions: the frame shows 1/scale of the width,
      // so the whole source spans `frameWidth * scale` pixels on screen.
      const sourcePixelWidth = frameWidth * scale;
      pan(-dx / sourcePixelWidth, -dy / sourcePixelWidth);
    },
    onPointerUp: () => {
      last.current = null;
    },
  };
}

function EdgeHandle({
  edge,
  onDrag,
}: {
  edge: "top" | "bottom";
  onDrag: (deltaPixels: number) => void;
}) {
  const last = useRef<number | null>(null);

  return (
    <div
      data-handle={edge}
      data-testid={`crop-handle-${edge}`}
      role="separator"
      aria-label={`Drag to change the ${edge} edge`}
      onPointerDown={(event: ReactPointerEvent) => {
        event.stopPropagation();
        (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
        last.current = event.clientY;
      }}
      onPointerMove={(event: ReactPointerEvent) => {
        if (last.current === null) return;
        const delta = event.clientY - last.current;
        last.current = event.clientY;
        // Dragging the top edge up and the bottom edge down both make the
        // selection taller, so the top handle's delta is inverted.
        onDrag((edge === "top" ? -delta : delta) * EDGE_TO_HEIGHT);
      }}
      onPointerUp={() => {
        last.current = null;
      }}
      className={`absolute inset-x-0 h-6 cursor-ns-resize flex items-center justify-center ${
        edge === "top" ? "top-0" : "bottom-0"
      }`}
    >
      <span className="h-1 w-10 rounded-full bg-white/80 shadow" />
    </div>
  );
}

// ---------------------------------------------------------------- display

function formatRatio(pixelWidth: number, pixelHeight: number): string {
  const w = Math.max(1, Math.round(pixelWidth));
  const h = Math.max(1, Math.round(pixelHeight));
  const divisor = gcd(w, h);
  const a = w / divisor;
  const b = h / divisor;
  // A reduced pair like 1600:899 tells the author nothing, so anything that
  // stays unwieldy falls back to a decimal.
  if (a > 50 || b > 50) return `${(w / h).toFixed(2)} : 1`;
  return `${a} : ${b}`;
}

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}
