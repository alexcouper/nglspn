"use client";

import { useState, useCallback } from "react";
import { api, type ProjectImage } from "@/lib/api";

interface UploadProgress {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface UseImageUploadOptions {
  projectId: string;
  onUploadComplete?: (image: ProjectImage) => void;
  onError?: (error: Error) => void;
}

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function useImageUpload({
  projectId,
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
      // Validate file type
      if (!ALLOWED_TYPES.includes(file.type)) {
        onError?.(new Error(`Invalid file type: ${file.type}`));
        return;
      }

      // Validate file size
      if (file.size > MAX_SIZE) {
        onError?.(new Error("File size must be less than 10MB"));
        return;
      }

      // Get image dimensions
      const dimensions = await getImageDimensions(file);

      try {
        // Step 1: Get presigned URL from backend
        const presigned = await api.myProjects.getImageUploadUrl(
          projectId,
          file.name,
          file.type,
          file.size
        );

        // Add to uploads list
        setUploads((prev) => [
          ...prev,
          {
            imageId: presigned.image_id,
            filename: file.name,
            progress: 0,
            status: "uploading",
          },
        ]);

        // Step 2: Upload to S3 using XMLHttpRequest for progress tracking
        await new Promise<void>((resolve, reject) => {
          const xhr = new XMLHttpRequest();

          xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
              const progress = Math.round((e.loaded / e.total) * 100);
              updateUpload(presigned.image_id, { progress });
            }
          });

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve();
            } else {
              reject(new Error(`Upload failed with status ${xhr.status}`));
            }
          };

          xhr.onerror = () => reject(new Error("Upload failed"));

          xhr.open(presigned.method, presigned.upload_url);
          Object.entries(presigned.headers).forEach(([key, value]) => {
            xhr.setRequestHeader(key, value);
          });
          xhr.send(file);
        });

        updateUpload(presigned.image_id, { status: "processing" });

        // Step 3: Notify backend of completion
        const completedImage = await api.myProjects.completeImageUpload(
          projectId,
          presigned.image_id,
          dimensions
        );

        updateUpload(presigned.image_id, { status: "complete", progress: 100 });
        onUploadComplete?.(completedImage);

        // Remove from uploads list after a delay
        setTimeout(() => {
          removeUpload(presigned.image_id);
        }, 2000);
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Upload failed";
        onError?.(new Error(errorMessage));

        // Find the upload by filename and mark as error
        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? { ...u, status: "error" as const, error: errorMessage }
              : u
          )
        );
      }
    },
    [projectId, onUploadComplete, onError, updateUpload, removeUpload]
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

function getImageDimensions(
  file: File
): Promise<{ width: number; height: number } | undefined> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.width, height: img.height });
      URL.revokeObjectURL(img.src);
    };
    img.onerror = () => resolve(undefined);
    img.src = URL.createObjectURL(file);
  });
}
