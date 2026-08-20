import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useStickyChromeOffset } from "./useStickyChromeOffset";

// ------------------------------------------------------------------ harness

// jsdom has no layout, so the measured element's height is stubbed on the
// prototype and its sticky offset comes from an inline style, which
// getComputedStyle does report.
function stubElementHeight(height: number) {
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get: () => height,
  });
}

function stubResizeObserver() {
  const callbacks: (() => void)[] = [];
  const disconnect = vi.fn();
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        callbacks.push(callback);
      }
      observe() {}
      unobserve() {}
      disconnect = disconnect;
    },
  );
  return { resize: () => act(() => callbacks.forEach((cb) => cb())), disconnect };
}

// `rendered` stands in for the authoring page's loading state, which returns a
// skeleton before the action bar exists.
function Harness({
  stickyTop,
  rendered,
  onOffset,
}: {
  stickyTop: string;
  rendered: boolean;
  onOffset: (value: number) => void;
}) {
  const { ref, offset } = useStickyChromeOffset();
  onOffset(offset);
  if (!rendered) return <span />;
  return <div ref={ref} style={{ position: "sticky", top: stickyTop }} />;
}

async function mountHarness({
  stickyTop = "56px",
  rendered = true,
}: { stickyTop?: string; rendered?: boolean } = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  let root: Root;
  const offsets: number[] = [];
  const render = (isRendered: boolean) =>
    root.render(
      <Harness
        stickyTop={stickyTop}
        rendered={isRendered}
        onOffset={(value) => offsets.push(value)}
      />,
    );
  await act(async () => {
    root = createRoot(container);
    render(rendered);
  });
  return {
    latestOffset: () => offsets[offsets.length - 1],
    show: async () => {
      await act(async () => render(true));
    },
    unmount: async () => {
      await act(async () => root.unmount());
      container.remove();
    },
  };
}

// -------------------------------------------------------------------- tests

describe("useStickyChromeOffset", () => {
  it("measures the element's own sticky offset plus its height", async () => {
    stubElementHeight(57);
    stubResizeObserver();

    const harness = await mountHarness({ stickyTop: "56px" });

    expect(harness.latestOffset()).toBe(113);
    await harness.unmount();
  });

  it("re-measures when the element changes height", async () => {
    stubElementHeight(57);
    const observer = stubResizeObserver();

    const harness = await mountHarness({ stickyTop: "56px" });
    stubElementHeight(77);
    observer.resize();

    expect(harness.latestOffset()).toBe(133);
    await harness.unmount();
  });

  it("treats an unpositioned element as having no offset of its own", async () => {
    stubElementHeight(57);
    stubResizeObserver();

    const harness = await mountHarness({ stickyTop: "auto" });

    expect(harness.latestOffset()).toBe(57);
    await harness.unmount();
  });

  it("measures an element that only appears after the first render", async () => {
    stubElementHeight(77);
    stubResizeObserver();

    const harness = await mountHarness({ rendered: false });
    expect(harness.latestOffset()).toBe(113); // the fallback

    await harness.show();

    expect(harness.latestOffset()).toBe(133);
    await harness.unmount();
  });

  it("stops observing once unmounted", async () => {
    stubElementHeight(57);
    const observer = stubResizeObserver();

    const harness = await mountHarness();
    await harness.unmount();

    expect(observer.disconnect).toHaveBeenCalled();
  });
});
