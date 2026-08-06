"use client";

import { useState, useCallback } from "react";
import { type ProjectImage } from "@/lib/api";
import {
  type ImageSource,
  ImageValidationError,
  uploadProjectImage,
} from "@/lib/uploadProjectImage";

interface UploadProgress {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface UseImageUploadOptions {
  projectId: string;
  isIcon?: boolean;
  source?: ImageSource;
  // The article an "article" upload belongs to.
  sourceId?: string | null;
  onUploadComplete?: (image: ProjectImage) => void;
  onError?: (error: Error) => void;
}

export function useImageUpload({
  projectId,
  isIcon = false,
  source = "project",
  sourceId = null,
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
        const completedImage = await uploadProjectImage(projectId, file, {
          isIcon,
          source,
          sourceId,
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
    [
      projectId,
      isIcon,
      source,
      sourceId,
      onUploadComplete,
      onError,
      updateUpload,
      removeUpload,
    ]
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
