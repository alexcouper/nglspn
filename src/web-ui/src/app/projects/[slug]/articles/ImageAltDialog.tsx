"use client";

import { useState } from "react";
import { Dialog } from "@/components/Dialog";

interface Props {
  initialAltText: string;
  onSave: (altText: string) => void;
  onCancel: () => void;
}

// Mounted only while an image is being edited, so the field always starts from
// that image's current alt text.
export function ImageAltDialog({ initialAltText, onSave, onCancel }: Props) {
  const [altText, setAltText] = useState(initialAltText);

  return (
    <Dialog isOpen onClose={onCancel}>
      <h2 className="text-lg font-semibold text-foreground">Image alt text</h2>
      <p className="text-sm text-muted-foreground mt-2">
        Describe the image for readers using a screen reader, and for when it
        fails to load.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave(altText);
        }}
      >
        <label
          htmlFor="image-alt"
          className="block text-sm font-medium text-foreground mt-6"
        >
          Alt text
        </label>
        <input
          id="image-alt"
          type="text"
          autoFocus
          value={altText}
          onChange={(e) => setAltText(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-accent"
        />

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button type="submit" className="btn-primary text-sm py-2 px-4">
            Save
          </button>
        </div>
      </form>
    </Dialog>
  );
}
