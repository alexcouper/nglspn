"use client";

import { useCallback, useState } from "react";
import { uploadProjectImage } from "@/lib/uploadProjectImage";

export type ImageUploadStatus =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "error"; message: string };

function messageFor(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Image upload failed";
}

// Inline images reach the editor by three routes — the toolbar button, dropping
// a file on the body, and pasting one — and all three funnel through the
// imageUploadHandler. MDXEditor rethrows a rejected upload into an unhandled
// promise, so this is the only place an author can be told it went wrong.
export function useImageUploadStatus(projectId: string) {
  const [status, setStatus] = useState<ImageUploadStatus>({ kind: "idle" });

  const uploadImage = useCallback(
    async (file: File) => {
      setStatus({ kind: "uploading" });
      try {
        const image = await uploadProjectImage(projectId, file, {
          source: "article",
        });
        setStatus({ kind: "idle" });
        return image.url;
      } catch (err) {
        setStatus({ kind: "error", message: messageFor(err) });
        throw err;
      }
    },
    [projectId],
  );

  const dismissError = useCallback(() => setStatus({ kind: "idle" }), []);

  return { status, uploadImage, dismissError };
}
