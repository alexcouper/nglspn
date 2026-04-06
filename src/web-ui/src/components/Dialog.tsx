"use client";

import { useEffect, useRef, type ReactNode } from "react";

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  position?: "center" | "top";
}

export function Dialog({ isOpen, onClose, children, className = "max-w-md", position = "center" }: DialogProps) {
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
      className={`fixed inset-x-0 mx-auto w-[calc(100%-2rem)] max-h-[calc(100%-2rem)] backdrop:bg-black/60 backdrop:backdrop-blur-sm bg-transparent p-0 overflow-visible ${position === "top" ? "top-[10vh] mb-auto" : "inset-y-0 my-auto"} ${isOpen ? "" : "hidden"}`}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className={`bg-white rounded-xl shadow-lg border border-border w-full mx-auto p-6 ${className}`}>
        {children}
      </div>
    </dialog>
  );
}
