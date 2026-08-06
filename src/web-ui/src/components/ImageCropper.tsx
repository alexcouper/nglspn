"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { CROP_BACKGROUND, CroppedImage, type CropRect } from "./CroppedImage";

// Zoom is the image's displayed width as a multiple of the crop box's width, so
// it is exactly `1 / crop.w`. Below 1 the image is narrower than the box and
// CROP_BACKGROUND shows at the edges — which is the point: a fixed-shape crop
// often wants the whole image with bands rather than a forced cover.
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 8;

// The slider is logarithmic. On a linear 0.25–8 track, 1x — where most images
// start and most adjustments happen — sits at 10% and the whole useful range is
// crushed against the left end.
const ZOOM_STEPS = 200;

// The crop box's width as a fraction of the stage, so there is always visible
// image around it to aim with.
const BOX_WIDTH_FRACTION = 0.6;
// Breathing room above and below the box, in px.
const STAGE_PADDING = 64;

export interface ImageCropperProps {
  src: string;
  naturalWidth: number;
  naturalHeight: number;
  value: CropRect | null;
  onChange: (crop: CropRect) => void;
  // The box's shape, fixed. The author can only zoom and pan — the output
  // shape is dictated by the layout it fills, e.g. a listing card's 16:9.
  lockRatio: number;
  // Source pixels across the box below which the result will look soft. A
  // warning, never a block.
  minSourceWidth?: number;
  previewLabel?: string;
}

// A crop picker that shows the whole image with the crop box drawn on top of
// it, rather than showing only what survives. Zoom scales the image while the
// box stays put, so zooming in narrows the focus; the box may be left sitting
// partly off the image, and what it takes from beyond the edge is
// CROP_BACKGROUND.
//
// Deliberately free of anything article-shaped: it takes an image and a
// rectangle and hands back a rectangle.
export function ImageCropper({
  src,
  naturalWidth,
  naturalHeight,
  value,
  onChange,
  lockRatio,
  minSourceWidth = 768,
  previewLabel = "Preview",
}: ImageCropperProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  const [stageWidth, setStageWidth] = useState(0);

  const source = useMemo(
    () => ({
      width: naturalWidth,
      height: naturalHeight,
      lockRatio,
    }),
    [naturalWidth, naturalHeight, lockRatio],
  );

  const crop = value ?? defaultCrop(source);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const measure = () => setStageWidth(stage.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  const boxWidth = stageWidth * BOX_WIDTH_FRACTION;
  const boxHeight = boxWidth / crop.ratio;
  const layout = layoutFor(crop, boxWidth, boxHeight, stageWidth, source);

  const setZoom = useCallback(
    (zoom: number) => onChange(withZoom(crop, clamp(zoom, MIN_ZOOM, zoomCeiling(source)), source)),
    [crop, onChange, source],
  );

  const pan = useCallback(
    (dxPx: number, dyPx: number) => {
      if (!layout.imageWidth || !layout.imageHeight) return;
      onChange({
        ...crop,
        x: crop.x - dxPx / layout.imageWidth,
        y: crop.y - dyPx / layout.imageHeight,
      });
    },
    [crop, layout.imageWidth, layout.imageHeight, onChange],
  );

  const drag = useDrag(pan);
  const sourcePixelWidth = Math.round(crop.w * naturalWidth);

  return (
    <div className="space-y-4">
      <div
        ref={stageRef}
        onPointerDown={drag.onPointerDown}
        onPointerMove={drag.onPointerMove}
        onPointerUp={drag.onPointerUp}
        onPointerCancel={drag.onPointerUp}
        onWheel={(event: ReactWheelEvent) =>
          setZoom((1 / crop.w) * (event.deltaY > 0 ? 0.94 : 1.06))
        }
        style={{ height: layout.stageHeight, touchAction: "none" }}
        className="relative w-full select-none overflow-hidden rounded-lg bg-[#d9dee6] cursor-move"
        data-testid="crop-stage"
      >
        {stageWidth > 0 && (
          <>
            {/* Behind the image, so the parts of the box the image does not
                reach show the same background the result will have rather than
                the stage's own colour. */}
            <div
              style={{ ...boxStyle(layout), backgroundColor: CROP_BACKGROUND }}
              className="pointer-events-none absolute"
              data-testid="crop-box-backdrop"
            />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={src}
              alt=""
              draggable={false}
              style={imageStyle(layout)}
              data-testid="crop-source"
            />
            {/* A light scrim only: the point of showing the whole image is that
                the author can see what they are leaving out. */}
            <div
              style={boxStyle(layout)}
              className="pointer-events-none absolute border-2 border-dashed border-white ring-1 ring-slate-900/50 shadow-[0_0_0_9999px_rgba(15,23,42,0.28)]"
              data-testid="crop-box"
            />
          </>
        )}
      </div>

      <div className="flex items-center gap-4">
        <label className="flex flex-1 items-center gap-2 text-sm text-muted-foreground">
          Zoom
          <input
            type="range"
            min={0}
            max={ZOOM_STEPS}
            step={1}
            value={zoomToSlider(1 / crop.w, source)}
            onChange={(event) =>
              setZoom(sliderToZoom(Number(event.target.value), source))
            }
            className="flex-1 accent-accent"
            aria-label="Zoom"
          />
        </label>
        <span
          className="text-sm font-medium tabular-nums text-muted-foreground"
          data-testid="crop-source-width"
        >
          {sourcePixelWidth}px
        </span>
      </div>

      <div className="flex items-start gap-3">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground pt-1">
          {previewLabel}
        </span>
        <div className="w-56 overflow-hidden rounded border border-border">
          <CroppedImage
            src={src}
            alt=""
            crop={crop}
            priority
            testId="crop-preview"
          />
        </div>
      </div>

      {sourcePixelWidth < minSourceWidth && (
        <p className="text-sm text-amber-700" role="status">
          This selection is only {sourcePixelWidth}px wide in the original, so it
          will look soft at full width.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- geometry

interface Source {
  width: number;
  height: number;
  lockRatio: number;
}

interface Layout {
  stageHeight: number;
  boxLeft: number;
  boxTop: number;
  boxWidth: number;
  boxHeight: number;
  imageLeft: number;
  imageTop: number;
  imageWidth: number;
  imageHeight: number;
}

// The crop that covers the box with no background showing, centred: the
// friendliest place to start. The author is free to zoom back out past it.
export function defaultCrop(source: Source): CropRect {
  const zoom = coveringZoom(source.lockRatio, source);
  return centred(1 / zoom, source.lockRatio, source);
}

// Below this the crop box reaches past the image on one axis. Not a limit —
// just where "no background showing" sits.
function coveringZoom(ratio: number, source: Source): number {
  return Math.max(1, source.width / (ratio * source.height));
}

// Exported so a caller driving the slider — a test, or a consumer wiring its
// own zoom control — can place it without re-deriving the log mapping.
export function zoomToSlider(zoom: number, source: Source): number {
  const ceiling = zoomCeiling(source);
  const t = Math.log(zoom / MIN_ZOOM) / Math.log(ceiling / MIN_ZOOM);
  return Math.round(clamp(t, 0, 1) * ZOOM_STEPS);
}

function sliderToZoom(position: number, source: Source): number {
  const ceiling = zoomCeiling(source);
  return MIN_ZOOM * (ceiling / MIN_ZOOM) ** (position / ZOOM_STEPS);
}

function zoomCeiling(source: Source): number {
  return Math.max(MAX_ZOOM, coveringZoom(source.lockRatio, source));
}

function centred(w: number, ratio: number, source: Source): CropRect {
  const h = (w * source.width) / (ratio * source.height);
  return { x: (1 - w) / 2, y: (1 - h) / 2, w, h, ratio };
}

// Zoom keeps the crop's centre where it is — otherwise the subject drifts out
// of frame as you adjust.
function withZoom(crop: CropRect, zoom: number, source: Source): CropRect {
  return resizedAboutCentre(crop, 1 / zoom, crop.ratio, source);
}

function resizedAboutCentre(
  crop: CropRect,
  w: number,
  ratio: number,
  source: Source,
): CropRect {
  const h = (w * source.width) / (ratio * source.height);
  return {
    x: crop.x + crop.w / 2 - w / 2,
    y: crop.y + crop.h / 2 - h / 2,
    w,
    h,
    ratio,
  };
}

function layoutFor(
  crop: CropRect,
  boxWidth: number,
  boxHeight: number,
  stageWidth: number,
  source: Source,
): Layout {
  // The box's width is what defines the crop: `crop.w` of the source spans it.
  const imageWidth = crop.w ? boxWidth / crop.w : 0;
  const imageHeight = (imageWidth * source.height) / source.width;
  const stageHeight = Math.round(boxHeight + STAGE_PADDING * 2);
  const boxLeft = (stageWidth - boxWidth) / 2;
  const boxTop = (stageHeight - boxHeight) / 2;

  return {
    stageHeight,
    boxLeft,
    boxTop,
    boxWidth,
    boxHeight,
    imageWidth,
    imageHeight,
    imageLeft: boxLeft - crop.x * imageWidth,
    imageTop: boxTop - crop.y * imageHeight,
  };
}

function imageStyle(layout: Layout): CSSProperties {
  return {
    position: "absolute",
    left: layout.imageLeft,
    top: layout.imageTop,
    width: layout.imageWidth,
    height: layout.imageHeight,
    maxWidth: "none",
    backgroundColor: CROP_BACKGROUND,
  };
}

function boxStyle(layout: Layout): CSSProperties {
  return {
    left: layout.boxLeft,
    top: layout.boxTop,
    width: layout.boxWidth,
    height: layout.boxHeight,
  };
}

// ---------------------------------------------------------------- input

function useDrag(pan: (dx: number, dy: number) => void) {
  const last = useRef<{ x: number; y: number } | null>(null);

  return {
    onPointerDown: (event: ReactPointerEvent) => {
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
      last.current = { x: event.clientX, y: event.clientY };
    },
    onPointerMove: (event: ReactPointerEvent) => {
      if (!last.current) return;
      const dx = event.clientX - last.current.x;
      const dy = event.clientY - last.current.y;
      last.current = { x: event.clientX, y: event.clientY };
      pan(dx, dy);
    },
    onPointerUp: () => {
      last.current = null;
    },
  };
}

function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}
