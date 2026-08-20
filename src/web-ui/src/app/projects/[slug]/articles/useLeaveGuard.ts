"use client";

import { useEffect } from "react";

// Exported so the test can assert on the sentence the guard shows rather than
// on a second copy of it.
export const LEAVE_PROMPT =
  "You have unsaved changes to this article. Leave without saving?";

// Schemes that hand the click to something other than the browsing context.
const NON_NAVIGATING = new Set(["mailto:", "tel:", "sms:", "javascript:"]);

// True when the click is the author leaving the page, rather than opening the
// link somewhere else or moving around inside this one.
function isLeavingClick(event: MouseEvent, anchor: HTMLAnchorElement) {
  // A modified click opens a new tab or window, and a non-primary button is
  // not a navigation at all — the author stays where they are either way.
  if (event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
    return false;

  const target = anchor.getAttribute("target");
  if (target && target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;

  // A link the author wrote into the body. Clicking one inside a contenteditable
  // puts the caret in it rather than following it, so prompting would fire on
  // an ordinary edit. Matched by attribute rather than `isContentEditable`,
  // which jsdom does not compute.
  if (anchor.closest('[contenteditable]:not([contenteditable="false"])'))
    return false;

  const href = anchor.getAttribute("href");
  if (!href) return false;

  let destination: URL;
  try {
    destination = new URL(href, window.location.href);
  } catch {
    return false;
  }
  if (NON_NAVIGATING.has(destination.protocol)) return false;

  // A bare "#" or an in-page anchor only moves the scroll position.
  const here = new URL(window.location.href);
  return (
    destination.pathname !== here.pathname || destination.search !== here.search
  );
}

// Guards against leaving with unsaved work.
//
// The `beforeunload` listener covers browser navigation — a closed tab, a
// reload, a typed URL. In-app navigation never fires it, so the click
// interceptor covers the rest: every link on the page, including the header,
// the logo, the user menu and the footer, which `app/layout.tsx` renders as
// siblings of this page and which therefore know nothing about the draft.
//
// The interceptor is registered on `window`, and that is not incidental. React
// attaches its whole synthetic event system as listeners on the container it
// hydrated into, and `Link`'s own onClick is what preventDefaults and calls
// `router.push` — so the guard has to see the click, and cancel it, before
// React dispatches. `window` is the outermost object in the capture path, above
// both `document` and any container inside it, so a window-capture listener
// runs first however late it was registered and wherever React attached. Any
// listener further in is a bet on React's internals. Do not move it inwards.
export function useLeaveGuard(isDirty: () => boolean) {
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!isDirty()) return;
      event.preventDefault();
      // The spelling older Safari still reads, which only takes effect for a
      // non-empty string; current browsers take the preventDefault above.
      event.returnValue = LEAVE_PROMPT;
    };

    const intercept = (event: MouseEvent) => {
      if (event.defaultPrevented || !isDirty()) return;
      const anchor = (event.target as Element | null)?.closest?.("a[href]") as
        HTMLAnchorElement | null | undefined;
      if (!anchor || !isLeavingClick(event, anchor)) return;
      if (window.confirm(LEAVE_PROMPT)) return;
      // Enough on its own, and deliberately not paired with `stopPropagation`.
      // `Link` runs the anchor's own onClick first and only then bails on
      // `e.defaultPrevented` (next/dist/client/app-dir/link.js), so cancelling
      // the default stops the navigation while the drawer and the user menu
      // still get their `closeMenu` and shut behind the dialog.
      event.preventDefault();
    };

    window.addEventListener("beforeunload", warn);
    window.addEventListener("click", intercept, true);
    return () => {
      window.removeEventListener("beforeunload", warn);
      window.removeEventListener("click", intercept, true);
    };
  }, [isDirty]);
}
