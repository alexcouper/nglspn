"use client";

import { useState } from "react";

interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  projectTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export function DeleteConfirmationDialog({
  isOpen,
  projectTitle,
  onConfirm,
  onCancel,
  isDeleting = false,
}: DeleteConfirmationDialogProps) {
  const [confirmText, setConfirmText] = useState("");

  if (!isOpen) {
    return null;
  }

  const handleCancel = () => {
    setConfirmText("");
    onCancel();
  };

  const canDelete = confirmText.toLowerCase() === "delete";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleCancel}
        aria-hidden="true"
      />

      <div className="relative bg-white rounded-xl shadow-lg border border-border max-w-md w-full mx-4 p-6">
        <h2 className="text-base font-semibold text-foreground mb-3">
          Delete Project
        </h2>

        <p className="text-sm text-muted-foreground mb-4">
          Are you sure you want to delete{" "}
          <strong className="text-foreground">&quot;{projectTitle}&quot;</strong>? This action cannot be
          undone.
        </p>

        <p className="text-xs text-muted-foreground mb-3">
          Type <strong className="text-red-600">delete</strong> to confirm:
        </p>

        <input
          type="text"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          className="input mb-5"
          placeholder="Type 'delete' to confirm"
          autoFocus
          disabled={isDeleting}
        />

        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isDeleting}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!canDelete || isDeleting}
            className="btn-primary bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? "Deleting..." : "Delete Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
