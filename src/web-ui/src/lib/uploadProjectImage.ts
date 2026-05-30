import { api, type ProjectImage } from "@/lib/api";

export const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
] as const;

export const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB

export class ImageValidationError extends Error {}

interface UploadOptions {
  isIcon?: boolean;
  // Fired once the backend allocates the image row but before the S3 PUT —
  // useful for callers that want to track per-upload progress by id.
  onImageId?: (imageId: string) => void;
  // Fired with 0..100 during the S3 PUT.
  onProgress?: (percent: number) => void;
  // Fired after the S3 PUT succeeds, before the backend completion call.
  onUploadDone?: () => void;
}

// Shared 3-step image upload: presigned URL → S3 PUT → backend completion.
// The `useImageUpload` hook wraps this with React state for a multi-file
// progress list; one-shot callers (the article inline image handler) can use
// it directly and ignore the callbacks.
export async function uploadProjectImage(
  projectId: string,
  file: File,
  options: UploadOptions = {},
): Promise<ProjectImage> {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type as (typeof ALLOWED_IMAGE_TYPES)[number])) {
    throw new ImageValidationError(`Invalid file type: ${file.type}`);
  }
  if (file.size > MAX_IMAGE_SIZE) {
    throw new ImageValidationError("File size must be less than 10MB");
  }

  const presigned = await api.myProjects.getImageUploadUrl(
    projectId,
    file.name,
    file.type,
    file.size,
    options.isIcon ?? false,
  );

  options.onImageId?.(presigned.image_id);

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    if (options.onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          options.onProgress!(Math.round((e.loaded / e.total) * 100));
        }
      });
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed with status ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Upload failed"));

    xhr.open(presigned.method, presigned.upload_url);
    Object.entries(presigned.headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });
    xhr.send(file);
  });

  options.onUploadDone?.();

  return api.myProjects.completeImageUpload(projectId, presigned.image_id);
}
