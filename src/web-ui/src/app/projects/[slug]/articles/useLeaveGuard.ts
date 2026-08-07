"use client";

import { useCallback, useEffect } from "react";

const LEAVE_PROMPT =
  "You have unsaved changes to this article. Leave without saving?";

// Guards against leaving with unsaved work, by both routes out of the page.
//
// The `beforeunload` listener covers browser navigation only — a closed tab, a
// reload, a typed URL. In-app navigation never fires it, so the links that leave
// the editor call `confirmLeave` for themselves; the prompt lives here so both
// halves say the same thing.
export function useLeaveGuard(isDirty: () => boolean) {
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!isDirty()) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  // True when it is fine to go: nothing to lose, or the author said so.
  return useCallback(
    () => !isDirty() || window.confirm(LEAVE_PROMPT),
    [isDirty],
  );
}
