import type { CropRect } from "@/components/CroppedImage";
import { CROP_BACKGROUND } from "@/components/CroppedImage";

// The square the browser produces. Rendered at 28px in the nav and 96px on the
// profile, so 512 leaves room for high-density screens without a variant
// pipeline behind it. Mirrors nothing on the server: the backend stores what
// it is sent.
export const AVATAR_SIZE = 512;
export const AVATAR_MIME = "image/jpeg";
const AVATAR_QUALITY = 0.86;

export interface DrawRect {
  dx: number;
  dy: number;
  dw: number;
  dh: number;
}

// Where the whole source image lands on a `size`×`size` canvas so that the
// crop rectangle fills it. Drawing the whole image (rather than a sub-rect)
// is what lets a crop that extends past the source's edge come out with
// CROP_BACKGROUND in the overhang, the same as CroppedImage renders it.
export function drawRectFor(
  crop: CropRect,
  naturalWidth: number,
  naturalHeight: number,
  size: number = AVATAR_SIZE,
): DrawRect {
  const scale = size / (crop.w * naturalWidth);
  // `0 -` rather than unary minus: a crop at the origin would otherwise give -0.
  return {
    dx: 0 - crop.x * naturalWidth * scale,
    dy: 0 - crop.y * naturalHeight * scale,
    dw: naturalWidth * scale,
    dh: naturalHeight * scale,
  };
}

export interface LoadedImage {
  image: HTMLImageElement;
  // What the cropper needs as `src`. A data URL, not an object URL: the app's
  // Content-Security-Policy allows `data:` for images and not `blob:`.
  dataUrl: string;
  width: number;
  height: number;
}

export class NotAnImageError extends Error {}

// Reads a picked file into a decoded <img>. Rejects with NotAnImageError for
// anything the browser cannot decode, before any request is made.
export async function loadImageFile(file: File): Promise<LoadedImage> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new NotAnImageError("Could not read that file."));
    reader.readAsDataURL(file);
  });
  const image = new Image();
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new NotAnImageError("That file is not an image we can read."));
    image.src = dataUrl;
  });
  if (!image.naturalWidth || !image.naturalHeight) {
    throw new NotAnImageError("That file is not an image we can read.");
  }
  return { image, dataUrl, width: image.naturalWidth, height: image.naturalHeight };
}

// Draws the chosen region to a square canvas and encodes it. The canvas is a
// parameter so the drawing can be tested against a stub.
export async function renderAvatarBlob(
  source: LoadedImage,
  crop: CropRect,
  canvas: HTMLCanvasElement = document.createElement("canvas"),
): Promise<Blob> {
  canvas.width = AVATAR_SIZE;
  canvas.height = AVATAR_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas is not available");

  ctx.fillStyle = CROP_BACKGROUND;
  ctx.fillRect(0, 0, AVATAR_SIZE, AVATAR_SIZE);
  const { dx, dy, dw, dh } = drawRectFor(crop, source.width, source.height);
  ctx.drawImage(source.image, dx, dy, dw, dh);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Could not encode the avatar"))),
      AVATAR_MIME,
      AVATAR_QUALITY,
    );
  });
}
