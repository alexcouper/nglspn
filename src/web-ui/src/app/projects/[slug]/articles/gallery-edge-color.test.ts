import { describe, expect, it } from "vitest";
import { dominantEdgeColor, type ImageBytes } from "./gallery-edge-color";

// ------------------------------------------------------------------ fixtures

type Rgba = [number, number, number, number];

const OPAQUE = 255;
const TRANSPARENT = 0;

const NEAR_WHITE: Rgba = [250, 250, 247, OPAQUE];
const CHARCOAL: Rgba = [24, 26, 32, OPAQUE];
const ORANGE: Rgba = [233, 142, 74, OPAQUE];

const SIZE = 50;

function buildImage(paint: (x: number, y: number) => Rgba): ImageBytes {
  const data = new Uint8ClampedArray(SIZE * SIZE * 4);
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const [r, g, b, a] = paint(x, y);
      data.set([r, g, b, a], (y * SIZE + x) * 4);
    }
  }
  return { data, width: SIZE, height: SIZE };
}

// The ring `dominantEdgeColor` reads is 2% of the shorter side, so one pixel
// at this fixture size.
function onRing(x: number, y: number) {
  return x === 0 || y === 0 || x === SIZE - 1 || y === SIZE - 1;
}

function imageWithEdge(edge: Rgba, centre: Rgba = ORANGE): ImageBytes {
  return buildImage((x, y) => (onRing(x, y) ? edge : centre));
}

/** An edge painted `edge` except for every nth pixel, which gets `stray`. */
function imageWithSpeckledEdge(edge: Rgba, stray: Rgba, everyNth: number) {
  let seen = 0;
  return buildImage((x, y) => {
    if (!onRing(x, y)) return ORANGE;
    return seen++ % everyNth === 0 ? stray : edge;
  });
}

// --------------------------------------------------------------------- tests

describe("dominantEdgeColor", () => {
  it("returns the colour filling a uniform edge", () => {
    expect(dominantEdgeColor(imageWithEdge(NEAR_WHITE))?.css).toBe("rgb(250 250 247)");
  });

  it("reads a dark edge as readily as a light one", () => {
    expect(dominantEdgeColor(imageWithEdge(CHARCOAL))?.css).toBe("rgb(24 26 32)");
  });

  it("marks a dark edge as needing light text over it", () => {
    expect(dominantEdgeColor(imageWithEdge(CHARCOAL))?.isDark).toBe(true);
  });

  it("does not mark a near-white edge as dark", () => {
    expect(dominantEdgeColor(imageWithEdge(NEAR_WHITE))?.isDark).toBe(false);
  });

  it("ignores the middle of the image when it disagrees with the edge", () => {
    const mostlyOrange = buildImage((x, y) => (onRing(x, y) ? NEAR_WHITE : ORANGE));
    expect(dominantEdgeColor(mostlyOrange)?.css).toBe("rgb(250 250 247)");
  });

  it("averages within a bucket so near-identical edge pixels do not quantise", () => {
    const jittered = buildImage((x, y) => {
      if (!onRing(x, y)) return ORANGE;
      return x % 2 === 0 ? [250, 250, 247, OPAQUE] : [252, 250, 247, OPAQUE];
    });
    expect(dominantEdgeColor(jittered)?.css).toBe("rgb(251 250 247)");
  });

  it("tolerates a minority of stray pixels in the edge", () => {
    const speckled = imageWithSpeckledEdge(NEAR_WHITE, ORANGE, 5);
    expect(dominantEdgeColor(speckled)?.css).toBe("rgb(250 250 247)");
  });

  it("returns null when the edge is mostly transparent", () => {
    const cutOut = imageWithEdge([0, 0, 0, TRANSPARENT]);
    expect(dominantEdgeColor(cutOut)).toBeNull();
  });

  it("still samples an edge whose corners are cut out", () => {
    const inCorner = (v: number) => v < 3 || v >= SIZE - 3;
    const rounded = buildImage((x, y) => {
      if (!onRing(x, y)) return ORANGE;
      return inCorner(x) && inCorner(y) ? [0, 0, 0, TRANSPARENT] : NEAR_WHITE;
    });
    expect(dominantEdgeColor(rounded)?.css).toBe("rgb(250 250 247)");
  });

  it("returns null when the edge has no dominant colour", () => {
    const halfAndHalf = buildImage((x, y) => {
      if (!onRing(x, y)) return ORANGE;
      return x % 2 === 0 ? NEAR_WHITE : CHARCOAL;
    });
    expect(dominantEdgeColor(halfAndHalf)).toBeNull();
  });
});
