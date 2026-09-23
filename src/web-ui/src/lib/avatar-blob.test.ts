import { describe, expect, it, vi } from "vitest";
import type { CropRect } from "@/components/CroppedImage";
import { AVATAR_SIZE, drawRectFor, renderAvatarBlob, type LoadedImage } from "./avatarBlob";

function squareCrop(overrides: Partial<CropRect> = {}): CropRect {
  return { x: 0.25, y: 0, w: 0.5, h: 1, ratio: 1, ...overrides };
}

describe("drawRectFor", () => {
  it("maps the crop onto the whole canvas for a 2:1 source", () => {
    // A 2000×1000 source; the middle 1000×1000 square is the crop.
    const rect = drawRectFor(squareCrop(), 2000, 1000, 512);

    expect(rect.dw).toBe(1024);
    expect(rect.dh).toBe(512);
    expect(rect.dx).toBe(-256);
    expect(rect.dy).toBe(0);
  });

  it("leaves a margin when the crop overhangs the source", () => {
    // Zoomed out: the crop is wider than the image, so the image sits inside
    // the canvas with background either side.
    const rect = drawRectFor(squareCrop({ x: -0.25, w: 1.5, y: -0.5, h: 1.5 }), 1000, 1000, 600);

    expect(rect.dw).toBe(400);
    expect(rect.dx).toBe(100);
    expect(rect.dy).toBe(200);
  });

  it("defaults to the avatar size", () => {
    const rect = drawRectFor(squareCrop({ x: 0, w: 1, h: 1 }), 800, 800);

    expect(rect.dw).toBe(AVATAR_SIZE);
  });
});

describe("renderAvatarBlob", () => {
  function stubCanvas() {
    const ctx = { fillStyle: "", fillRect: vi.fn(), drawImage: vi.fn() };
    const blob = new Blob(["jpeg"], { type: "image/jpeg" });
    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ctx),
      toBlob: vi.fn((cb: (b: Blob | null) => void) => cb(blob)),
    } as unknown as HTMLCanvasElement;
    return { canvas, ctx, blob };
  }

  const source: LoadedImage = {
    image: {} as HTMLImageElement,
    dataUrl: "data:image/png;base64,",
    width: 2000,
    height: 1000,
  };

  it("paints the background, draws the framed region and encodes a JPEG", async () => {
    const { canvas, ctx, blob } = stubCanvas();

    const result = await renderAvatarBlob(source, squareCrop(), canvas);

    expect(result).toBe(blob);
    expect(canvas.width).toBe(AVATAR_SIZE);
    expect(canvas.height).toBe(AVATAR_SIZE);
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, AVATAR_SIZE, AVATAR_SIZE);
    expect(ctx.drawImage).toHaveBeenCalledWith(source.image, -256, 0, 1024, 512);
    expect(vi.mocked(canvas.toBlob).mock.calls[0][1]).toBe("image/jpeg");
  });

  it("rejects when the canvas cannot encode", async () => {
    const { canvas } = stubCanvas();
    vi.mocked(canvas.toBlob).mockImplementation((cb: (b: Blob | null) => void) => cb(null));

    await expect(renderAvatarBlob(source, squareCrop(), canvas)).rejects.toThrow(
      /encode/,
    );
  });
});
