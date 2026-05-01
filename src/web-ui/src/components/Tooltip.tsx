"use client";

import {
  ReactNode,
  useEffect,
  useId,
  useRef,
  useState,
  cloneElement,
  isValidElement,
  KeyboardEvent,
  ReactElement,
} from "react";

interface TooltipProps {
  children: ReactElement;
  content: ReactNode;
  className?: string;
}

export function Tooltip({ children, content, className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (wrapperRef.current && !wrapperRef.current.contains(target)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape" && open) {
      setOpen(false);
    }
  }

  if (!isValidElement(children)) {
    throw new Error("Tooltip expects a single React element as children");
  }

  const trigger = cloneElement(
    children as ReactElement<Record<string, unknown>>,
    {
      "aria-describedby": open ? id : undefined,
      onMouseEnter: () => setOpen(true),
      onMouseLeave: () => setOpen(false),
      onFocus: () => setOpen(true),
      onBlur: () => setOpen(false),
      onClick: (event: React.MouseEvent) => {
        event.preventDefault();
        setOpen((prev) => !prev);
      },
      onKeyDown: handleKeyDown,
    },
  );

  return (
    <span
      ref={wrapperRef}
      className={`relative inline-flex ${className ?? ""}`.trim()}
    >
      {trigger}
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute z-50 left-1/2 top-full mt-2 -translate-x-1/2 max-w-xs rounded-md bg-foreground text-background text-xs leading-snug px-3 py-2 shadow-md whitespace-normal pointer-events-none"
        >
          {content}
        </span>
      )}
    </span>
  );
}
