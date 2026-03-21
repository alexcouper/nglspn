"use client";

import type { ReactNode } from "react";

export function HorizontalScroll({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide -mx-4 px-4 sm:-mx-6 sm:px-6">
      {children}
    </div>
  );
}
