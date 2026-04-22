"use client";

const FIELD_LABELS: Record<string, string> = {
  title: "A title",
  description: "A description",
  main_image: "A main image",
};

interface PublishDialogProps {
  isOpen: boolean;
  missing: string[];
  onClose: () => void;
}

export function PublishDialog({ isOpen, missing, onClose }: PublishDialogProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-foreground">
          Not quite ready to publish
        </h2>
        <p className="text-sm text-muted-foreground mt-2">
          Before publishing, please add:
        </p>
        <ul className="mt-3 space-y-1 text-sm text-foreground list-disc list-inside">
          {missing.map((field) => (
            <li key={field}>{FIELD_LABELS[field] ?? field}</li>
          ))}
        </ul>
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="btn-primary text-sm py-2 px-4"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
