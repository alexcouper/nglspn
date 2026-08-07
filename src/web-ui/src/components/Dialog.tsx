"use client";

import { useEffect, useRef, type ReactNode } from "react";

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  position?: "center" | "top";
  // Id of the heading inside `children` that names the dialog.
  labelledBy?: string;
  // Edge to edge under `sm`. Has to be applied to the <dialog> itself — the
  // width and height caps below live there, so classes passed through
  // `className` (which lands on the inner panel) cannot override them.
  fullScreenOnMobile?: boolean;
}

export function Dialog({
  isOpen,
  onClose,
  children,
  className = "max-w-md",
  position = "center",
  labelledBy,
  fullScreenOnMobile = false,
}: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    // Prevent native ESC from closing the dialog directly —
    // route it through onClose so consumers can guard against it
    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [onClose]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={labelledBy}
      className={`fixed inset-x-0 mx-auto w-[calc(100%-2rem)] max-h-[calc(100%-2rem)] backdrop:bg-black/60 backdrop:backdrop-blur-sm bg-transparent p-0 overflow-visible ${position === "top" ? "top-[10vh] mb-auto" : "inset-y-0 my-auto"} ${fullScreenOnMobile ? "max-sm:w-full max-sm:h-full max-sm:max-h-full" : ""} ${isOpen ? "" : "hidden"}`}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div
        className={`bg-white rounded-xl shadow-lg border border-border w-full mx-auto p-6 ${fullScreenOnMobile ? "max-sm:h-full max-sm:rounded-none max-sm:border-0" : ""} ${className}`}
      >
        {children}
      </div>
    </dialog>
  );
}
