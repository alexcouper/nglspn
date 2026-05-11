"use client";

import { useToasts, type Toast, type ToastKind } from "@/contexts/toasts";

const KIND_STYLES: Record<ToastKind, string> = {
  info: "bg-white border-slate-200 text-slate-900",
  warning: "bg-amber-50 border-amber-200 text-amber-900",
  error: "bg-red-50 border-red-200 text-red-900",
};

function defaultBody(toast: Toast) {
  return (
    <div className="flex-1 min-w-0">
      <div className="text-sm leading-snug">{toast.title}</div>
      {toast.description && (
        <div className="text-xs opacity-80 truncate mt-0.5">
          {toast.description}
        </div>
      )}
    </div>
  );
}

export function ToastContainer() {
  const { toasts, dismissToast } = useToasts();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50 max-w-sm">
      {toasts.map((toast) => {
        const kind = toast.kind ?? "info";
        const handleClick = toast.onClick
          ? () => {
              dismissToast(toast.id);
              toast.onClick?.();
            }
          : undefined;
        return (
          <div
            key={toast.id}
            role="status"
            className={`shadow-lg rounded-lg border p-3 flex gap-3 items-start ${
              KIND_STYLES[kind]
            } ${handleClick ? "cursor-pointer hover:bg-slate-50 transition-colors" : ""}`}
            onClick={handleClick}
          >
            {toast.body ?? defaultBody(toast)}
            <button
              type="button"
              aria-label="Dismiss"
              onClick={(event) => {
                event.stopPropagation();
                dismissToast(toast.id);
              }}
              className="text-slate-400 hover:text-slate-600 ml-1"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        );
      })}
    </div>
  );
}
