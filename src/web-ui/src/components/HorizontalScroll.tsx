"use client";

import { useRef, useState, useEffect, useCallback, type ReactNode } from "react";

export function HorizontalScroll({ children }: { children: ReactNode }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    checkScroll();
    el.addEventListener("scroll", checkScroll, { passive: true });
    const ro = new ResizeObserver(checkScroll);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", checkScroll);
      ro.disconnect();
    };
  }, [checkScroll]);

  return (
    <div className="relative -mx-4 sm:-mx-6">
      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide px-4 sm:px-6"
      >
        {children}
      </div>
      {canScrollLeft && (
        <div className="pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-muted to-transparent" />
      )}
      {canScrollRight && (
        <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-muted to-transparent" />
      )}
    </div>
  );
}
