"use client";

import { useEffect, useState } from "react";

// Where the sticky chrome ends before anything has been measured: the site nav
// (h-14 plus its border) and a one-line action bar. First paint only, and
// environments without layout — the real number comes from the element.
const FALLBACK_OFFSET_PX = 113;

/**
 * Measures where a sticky element comes to rest, so something below it can
 * stick clear of it rather than underneath.
 *
 * Measured rather than hard-coded because the action bar's height moves: a long
 * breadcrumb or a save message wraps once the row is narrow enough.
 */
export function useStickyChromeOffset() {
  // A callback ref, not a ref object: the authoring page renders a skeleton
  // first, so the element appears a render or two after the hook mounts.
  const [element, setElement] = useState<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState(FALLBACK_OFFSET_PX);

  useEffect(() => {
    if (!element) return;

    const measure = () => {
      // Its own sticky offset, not `getBoundingClientRect`: the rect says where
      // the bar is now, which is lower until the author has scrolled past it.
      const ownOffset = parseFloat(window.getComputedStyle(element).top);
      setOffset(
        (Number.isNaN(ownOffset) ? 0 : ownOffset) + element.offsetHeight,
      );
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);

  return { ref: setElement, offset };
}
