"use client";

import { useCallback, useEffect, useRef } from "react";

export function useAutoResize(maxHeight = "12rem") {
  const ref = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
    el.style.maxHeight = maxHeight;
    el.style.overflowY =
      el.scrollHeight > el.offsetHeight ? "auto" : "hidden";
  }, [maxHeight]);

  useEffect(() => {
    resize();
  }, [resize]);

  return { ref, resize };
}
