"use client";

import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";

interface UploadProgressItem {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface UploadProgressProps {
  uploads: UploadProgressItem[];
}

export function UploadProgress({ uploads }: UploadProgressProps) {
  if (uploads.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 mt-4">
      {uploads.map((upload) => (
        <div
          key={upload.imageId}
          className="flex items-center gap-3 p-3 bg-muted rounded-xl"
        >
          {upload.status === "complete" && (
            <CheckCircleIcon className="w-5 h-5 text-green-500 flex-shrink-0" />
          )}
          {upload.status === "error" && (
            <XCircleIcon className="w-5 h-5 text-red-500 flex-shrink-0" />
          )}
          {(upload.status === "uploading" ||
            upload.status === "processing" ||
            upload.status === "pending") && (
            <ArrowPathIcon className="w-5 h-5 text-accent animate-spin flex-shrink-0" />
          )}

          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {upload.filename}
            </p>
            {upload.status === "uploading" && (
              <div className="mt-1 h-1.5 bg-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent transition-all duration-300"
                  style={{ width: `${upload.progress}%` }}
                />
              </div>
            )}
            {upload.status === "processing" && (
              <p className="text-xs text-muted-foreground">Processing...</p>
            )}
            {upload.status === "complete" && (
              <p className="text-xs text-green-600">Complete</p>
            )}
            {upload.error && (
              <p className="text-xs text-red-500">{upload.error}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
