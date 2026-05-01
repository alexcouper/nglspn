"use client";

import { XMarkIcon } from "@heroicons/react/24/outline";
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
  const [shiftX, setShiftX] = useState(0);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const popoverRef = useRef<HTMLSpanElement>(null);
  // Mobile browsers synthesize a mouseenter+focus+click sequence on first tap,
  // which makes a hover-then-toggle pattern collapse to "open then immediately
  // close" — the user sees nothing on the first tap. Gate hover and focus on
  // the last pointer type so touch input goes through click only.
  const lastPointerTypeRef = useRef<string>("mouse");
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

  useEffect(() => {
    if (!open) return;
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // After the popover renders, measure its viewport position and shift it
  // horizontally so it stays inside the viewport — needed when the trigger
  // is near a screen edge (common on mobile).
  useEffect(() => {
    if (!open) {
      setShiftX(0);
      return;
    }
    function clamp() {
      const popover = popoverRef.current;
      if (!popover) return;
      const margin = 8;
      // Reset to centred before measuring so subsequent recalcs are absolute,
      // not cumulative.
      popover.style.transform = "translateX(-50%)";
      const rect = popover.getBoundingClientRect();
      let next = 0;
      if (rect.left < margin) next = margin - rect.left;
      else if (rect.right > window.innerWidth - margin)
        next = window.innerWidth - margin - rect.right;
      setShiftX(next);
    }
    clamp();
    window.addEventListener("resize", clamp);
    return () => window.removeEventListener("resize", clamp);
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
    // The ref reads below only happen inside event handlers, never during
    // render; the lint rule does not infer that through cloneElement.
    // eslint-disable-next-line react-hooks/refs
    {
      "aria-describedby": open ? id : undefined,
      onPointerDown: (event: React.PointerEvent) => {
        lastPointerTypeRef.current = event.pointerType || "mouse";
      },
      onFocus: () => {
        if (lastPointerTypeRef.current === "mouse") setOpen(true);
      },
      onBlur: () => {
        if (lastPointerTypeRef.current === "mouse") setOpen(false);
      },
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
      // Hover handlers live on the wrapper so the pointer can travel from
      // the trigger into the popover (e.g. to click a link inside) without
      // the popover closing.
      onMouseEnter={() => {
        if (lastPointerTypeRef.current === "mouse") setOpen(true);
      }}
      onMouseLeave={() => {
        if (lastPointerTypeRef.current === "mouse") setOpen(false);
      }}
    >
      {trigger}
      {open && (
        <span
          ref={popoverRef}
          id={id}
          role="tooltip"
          style={{ transform: `translateX(calc(-50% + ${shiftX}px))` }}
          className="absolute z-50 left-1/2 top-full mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl bg-surface border border-border shadow-lg p-4 pr-8 whitespace-normal text-left"
        >
          {content}
          <button
            type="button"
            aria-label="Close"
            className="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setOpen(false);
            }}
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </span>
      )}
    </span>
  );
}
