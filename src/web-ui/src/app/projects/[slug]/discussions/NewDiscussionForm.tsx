"use client";

import { useState } from "react";
import { NewDiscussionModal } from "@/components/NewDiscussionModal";

interface NewDiscussionFormProps {
  onSubmit: (body: string) => Promise<void>;
}

export function NewDiscussionForm({ onSubmit }: NewDiscussionFormProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className="w-full bg-white rounded-xl border border-border p-4 flex items-center gap-3 cursor-pointer hover:border-[#cbd5e1] transition-colors text-left"
      >
        <div className="flex-1 border border-border rounded-full px-4 py-2.5 text-sm text-muted-foreground">
          Start a discussion
        </div>
      </button>

      <NewDiscussionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={onSubmit}
      />
    </>
  );
}
