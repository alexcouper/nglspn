import { describe, expect, it } from "vitest";
import {
  carriesImage,
  draggedArticleImageFrom,
  imageFilesFrom,
} from "./gallery-drop";

// jsdom has no DataTransfer, and the real one cannot be populated from a test
// anyway — the browser owns it. This stands in for the parts the helpers read.
function aDataTransfer({
  items = [],
  data = {},
}: {
  items?: { kind: string; type: string; file?: File }[];
  data?: Record<string, string>;
} = {}): DataTransfer {
  return {
    items: items.map((item) => ({
      kind: item.kind,
      type: item.type,
      getAsFile: () => item.file ?? null,
    })),
    types: Object.keys(data),
    getData: (type: string) => data[type] ?? "",
  } as unknown as DataTransfer;
}

function anImageFile(name = "chart.svg"): File {
  return new File(["<svg />"], name, { type: "image/svg+xml" });
}

function aLexicalImageDrag(
  overrides: Record<string, unknown> = {},
): Record<string, string> {
  return {
    "application/x-lexical-drag": JSON.stringify({
      type: "image",
      data: {
        src: "https://cdn.example/a.svg",
        altText: "A",
        key: "node-7",
        ...overrides,
      },
    }),
  };
}

describe("imageFilesFrom", () => {
  it("returns the dropped image files", () => {
    const file = anImageFile();
    const files = imageFilesFrom(
      aDataTransfer({ items: [{ kind: "file", type: "image/svg+xml", file }] }),
    );

    expect(files).toEqual([file]);
  });

  it("ignores non-image files", () => {
    const files = imageFilesFrom(
      aDataTransfer({
        items: [
          { kind: "file", type: "application/pdf", file: anImageFile("a.pdf") },
        ],
      }),
    );

    expect(files).toEqual([]);
  });

  it("ignores dragged text", () => {
    const files = imageFilesFrom(
      aDataTransfer({ items: [{ kind: "string", type: "text/plain" }] }),
    );

    expect(files).toEqual([]);
  });
});

describe("draggedArticleImageFrom", () => {
  it("reads an image dragged from elsewhere in the article", () => {
    const dragged = draggedArticleImageFrom(
      aDataTransfer({ data: aLexicalImageDrag() }),
    );

    expect(dragged).toEqual({
      src: "https://cdn.example/a.svg",
      alt: "A",
      nodeKey: "node-7",
    });
  });

  it("keeps a title when the dragged image has one", () => {
    const dragged = draggedArticleImageFrom(
      aDataTransfer({ data: aLexicalImageDrag({ title: "Cost of living" }) }),
    );

    expect(dragged?.title).toBe("Cost of living");
  });

  it("returns nothing for a drag that carries no lexical payload", () => {
    expect(draggedArticleImageFrom(aDataTransfer())).toBeNull();
  });

  it("returns nothing for a dragged node that is not an image", () => {
    const dragged = draggedArticleImageFrom(
      aDataTransfer({
        data: {
          "application/x-lexical-drag": JSON.stringify({
            type: "table",
            data: { key: "node-3" },
          }),
        },
      }),
    );

    expect(dragged).toBeNull();
  });

  it("returns nothing for a malformed payload", () => {
    const dragged = draggedArticleImageFrom(
      aDataTransfer({ data: { "application/x-lexical-drag": "{not json" } }),
    );

    expect(dragged).toBeNull();
  });
});

describe("carriesImage", () => {
  it("accepts a file drag before the file itself is readable", () => {
    // Mid-drag the items are in protected mode: the kind and type are
    // visible, `getAsFile` returns null.
    const dragging = aDataTransfer({
      items: [{ kind: "file", type: "image/png" }],
    });

    expect(imageFilesFrom(dragging)).toEqual([]);
    expect(carriesImage(dragging)).toBe(true);
  });

  it("accepts an image dragged from elsewhere in the article", () => {
    expect(carriesImage(aDataTransfer({ data: aLexicalImageDrag() }))).toBe(
      true,
    );
  });

  it("rejects a drag carrying only text", () => {
    expect(
      carriesImage(
        aDataTransfer({
          items: [{ kind: "string", type: "text/plain" }],
          data: { "text/plain": "hello" },
        }),
      ),
    ).toBe(false);
  });

  it("rejects a drag with nothing on it", () => {
    expect(carriesImage(null)).toBe(false);
  });
});
