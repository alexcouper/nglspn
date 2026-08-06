"use client";

import { useState, useCallback } from "react";
import { type ProjectImage } from "@/lib/api";
import {
  type UploadTarget,
  ImageValidationError,
  uploadImage,
} from "@/lib/uploadImage";

interface UploadProgress {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface UseImageUploadOptions {
  // What the upload belongs to. A single value rather than a projectId plus a
  // pair of source fields, so a caller cannot name one owner and upload to
  // another.
  target: UploadTarget;
  onUploadComplete?: (image: ProjectImage) => void;
  onError?: (error: Error) => void;
}

export function useImageUpload({
  target,
  onUploadComplete,
  onError,
}: UseImageUploadOptions) {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);

  const updateUpload = useCallback(
    (imageId: string, updates: Partial<UploadProgress>) => {
      setUploads((prev) =>
        prev.map((u) => (u.imageId === imageId ? { ...u, ...updates } : u))
      );
    },
    []
  );

  const removeUpload = useCallback((imageId: string) => {
    setUploads((prev) => prev.filter((u) => u.imageId !== imageId));
  }, []);

  const uploadFile = useCallback(
    async (file: File) => {
      let imageId: string | null = null;
      try {
        const completedImage = await uploadImage(target, file, {
          onImageId: (id) => {
            imageId = id;
            setUploads((prev) => [
              ...prev,
              {
                imageId: id,
                filename: file.name,
                progress: 0,
                status: "uploading",
              },
            ]);
          },
          onProgress: (progress) => {
            if (imageId) updateUpload(imageId, { progress });
          },
          onUploadDone: () => {
            if (imageId) updateUpload(imageId, { status: "processing" });
          },
        });

        updateUpload(completedImage.id, {
          status: "complete",
          progress: 100,
        });
        onUploadComplete?.(completedImage);

        setTimeout(() => {
          removeUpload(completedImage.id);
        }, 2000);
      } catch (error) {
        const errorMessage =
          error instanceof ImageValidationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Upload failed";
        onError?.(new Error(errorMessage));

        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? { ...u, status: "error" as const, error: errorMessage }
              : u
          )
        );
      }
    },
    [target, onUploadComplete, onError, updateUpload, removeUpload]
  );

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      await Promise.all(fileArray.map(uploadFile));
    },
    [uploadFile]
  );

  return {
    uploads,
    uploadFile,
    uploadFiles,
    isUploading: uploads.some(
      (u) => u.status === "uploading" || u.status === "processing"
    ),
  };
}
