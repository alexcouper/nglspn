"use client";

import { useRef } from "react";
import { PhotoIcon } from "@heroicons/react/24/outline";
import { ButtonWithTooltip, insertImage$, usePublisher } from "@mdxeditor/editor";
import { ALLOWED_IMAGE_TYPES } from "@/lib/uploadImage";

// Straight to the OS file picker — no dialog. insertImage$ runs the file through
// the configured imageUploadHandler and inserts the node with empty alt text;
// alt text is set afterwards via the image's settings button.
export function InsertImageButton() {
  const insertImage = usePublisher(insertImage$);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_IMAGE_TYPES.join(",")}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          // Clear it so picking the same file twice still fires a change.
          e.target.value = "";
          if (file) insertImage({ file });
        }}
      />
      <ButtonWithTooltip
        title="Insert image"
        onClick={() => inputRef.current?.click()}
      >
        <PhotoIcon className="w-5 h-5" />
      </ButtonWithTooltip>
    </>
  );
}
