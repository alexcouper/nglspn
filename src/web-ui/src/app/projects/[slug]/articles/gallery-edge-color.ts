/**
 * The colour an image's outer edge is sitting on, for painting behind it.
 *
 * A chart exported with its own near-white background inside a card with a
 * slightly different near-white background draws a visible box. Filling the
 * space around the image with the image's own edge colour removes the seam.
 */

export interface EdgeColor {
  /** The colour itself, ready for a `background-color`. */
  css: string;
  /**
   * Whether text has to go light over it. The caption and dots sit on this
   * colour too, and a dark screenshot would otherwise get slate-grey text on
   * a near-black card.
   */
  isDark: boolean;
}

export interface ImageBytes {
  /** RGBA, four bytes per pixel, as `CanvasRenderingContext2D.getImageData` gives it. */
  data: Uint8ClampedArray;
  width: number;
  height: number;
}

/** Width of the border strip that gets read, as a fraction of the shorter side. */
const RING_FRACTION = 0.02;

/** Below this share of opaque pixels the edge is a cut-out, not a background. */
const MIN_OPAQUE_SHARE = 0.5;

/**
 * Share of the opaque ring one colour must hold to count as *the* edge
 * colour. A photo whose edges run light at the top and dark at the bottom has
 * no single answer, and guessing one looks worse than not trying.
 */
const MIN_DOMINANT_SHARE = 0.6;

/** Pixels within this many steps of each channel count as the same colour. */
const BUCKET_BITS = 3;

/** Anything below this alpha is treated as see-through rather than blended. */
const MIN_ALPHA = 250;

/** The image is scaled into a canvas this wide, so a huge PNG costs the same as a small one. */
const SAMPLE_WIDTH = 96;

/** Relative luminance below which the fill needs light text over it. */
const DARK_BELOW_LUMINANCE = 0.5;

interface Bucket {
  count: number;
  r: number;
  g: number;
  b: number;
}

/** WCAG relative luminance, 0 for black and 1 for white. */
function relativeLuminance(r: number, g: number, b: number): number {
  const linear = (channel: number) => {
    const v = channel / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
}

/**
 * The dominant colour of `image`'s border ring, or null when the ring is
 * mostly transparent or holds no majority colour.
 */
export function dominantEdgeColor({ data, width, height }: ImageBytes): EdgeColor | null {
  const ring = Math.max(1, Math.round(Math.min(width, height) * RING_FRACTION));
  const buckets = new Map<number, Bucket>();
  let ringPixels = 0;
  let opaquePixels = 0;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (x >= ring && y >= ring && x < width - ring && y < height - ring) continue;
      ringPixels++;

      const i = (y * width + x) * 4;
      if (data[i + 3] < MIN_ALPHA) continue;
      opaquePixels++;

      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const key = ((r >> BUCKET_BITS) << 16) | ((g >> BUCKET_BITS) << 8) | (b >> BUCKET_BITS);
      const bucket = buckets.get(key);
      if (bucket) {
        bucket.count++;
        bucket.r += r;
        bucket.g += g;
        bucket.b += b;
      } else {
        buckets.set(key, { count: 1, r, g, b });
      }
    }
  }

  if (ringPixels === 0) return null;
  if (opaquePixels / ringPixels < MIN_OPAQUE_SHARE) return null;

  let winner: Bucket | null = null;
  for (const bucket of buckets.values()) {
    if (!winner || bucket.count > winner.count) winner = bucket;
  }
  if (!winner || winner.count / opaquePixels < MIN_DOMINANT_SHARE) return null;

  // Average the bucket's real pixels rather than returning its centre, so the
  // answer is not visibly quantised against the image it has to match.
  const { count, r, g, b } = winner;
  const channel = (total: number) => Math.round(total / count);
  const [red, green, blue] = [channel(r), channel(g), channel(b)];
  return {
    css: `rgb(${red} ${green} ${blue})`,
    isDark: relativeLuminance(red, green, blue) < DARK_BELOW_LUMINANCE,
  };
}

/**
 * `dominantEdgeColor` for a loaded `<img>`, or null if the pixels cannot be
 * read — an image the canvas refuses to hand back (cross-origin without CORS
 * headers) is not an error, it just means no colour and the caller's default
 * background stands.
 */
export function sampleEdgeColor(image: HTMLImageElement): EdgeColor | null {
  const { naturalWidth, naturalHeight } = image;
  if (!naturalWidth || !naturalHeight) return null;

  const width = Math.min(SAMPLE_WIDTH, naturalWidth);
  const height = Math.max(1, Math.round((width * naturalHeight) / naturalWidth));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return null;

  try {
    context.drawImage(image, 0, 0, width, height);
    return dominantEdgeColor(context.getImageData(0, 0, width, height));
  } catch {
    return null;
  }
}
