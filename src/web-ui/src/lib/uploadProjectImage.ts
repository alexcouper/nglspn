import { api, type ProjectImage } from "@/lib/api";

export const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
] as const;

export const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB

// Where the upload came from. Article uploads live on the project so they share
// the storage and variant pipeline, but they describe an article, so the backend
// keeps them out of the project gallery, cover-image picks and image cap.
export type ImageSource = "project" | "article";

export class ImageValidationError extends Error {}

interface UploadOptions {
  isIcon?: boolean;
  source?: ImageSource;
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

  // Read before the PUT so a decode failure fails the upload early rather than
  // leaving a completed row with no dimensions.
  const dimensions = await readImageDimensions(file);

  const presigned = await api.myProjects.getImageUploadUrl(
    projectId,
    file.name,
    file.type,
    file.size,
    options.isIcon ?? false,
    options.source ?? "project",
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

  return api.myProjects.completeImageUpload(
    projectId,
    presigned.image_id,
    dimensions,
  );
}

// Null rather than throwing: an image the browser cannot decode still uploads,
// and the backend's variant job backfills the dimensions later. Callers that
// need the shape up front — the hero crop dialog — treat null as uncroppable.
//
// createImageBitmap reads the Blob directly. An <img> with a blob: URL would be
// blocked by the app's Content-Security-Policy, whose img-src allows data: but
// not blob:, so the fallback path below uses a data URL rather than an object
// URL.
async function readImageDimensions(
  file: File,
): Promise<{ width: number; height: number } | null> {
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      const size = { width: bitmap.width, height: bitmap.height };
      bitmap.close();
      return size;
    } catch {
      // Fall through — some formats/browsers refuse here but decode as an <img>.
    }
  }

  try {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error("read failed"));
      reader.readAsDataURL(file);
    });
    const image = new Image();
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("decode failed"));
      image.src = dataUrl;
    });
    return { width: image.naturalWidth, height: image.naturalHeight };
  } catch {
    return null;
  }
}

