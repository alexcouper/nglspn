import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { LEAVE_PROMPT, useLeaveGuard } from "./useLeaveGuard";

// --------------------------------------------------------------- factories

function anchor(attributes: Record<string, string>) {
  const element = document.createElement("a");
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  document.body.appendChild(element);
  return element;
}

function link(href: string) {
  return anchor({ href });
}

// ---------------------------------------------------------------- firing

// The guard's verdict on a click, without letting jsdom try to follow the link.
//
// The observer goes on window in the capture phase, registered after the hook's
// own listener, so it always runs second and sees whatever verdict the guard
// reached. `stopPropagation` does not silence it: that only stops the event
// moving on to the next target, not the remaining listeners on this one.
function clickIsAllowed(element: Element, init: MouseEventInit = {}) {
  let prevented = false;
  const observe = (event: Event) => {
    prevented = event.defaultPrevented;
    event.preventDefault();
  };
  window.addEventListener("click", observe, true);
  element.dispatchEvent(
    new MouseEvent("click", { bubbles: true, cancelable: true, ...init }),
  );
  window.removeEventListener("click", observe, true);
  return !prevented;
}

// jsdom's legacy `Event.returnValue` setter coerces to a boolean and
// preventDefaults on anything falsy, which would hide whether the guard set it
// at all. A plain property in its place records the assignment for what it is.
function fireBeforeUnload() {
  const event = new Event("beforeunload", { cancelable: true });
  let returnValue: unknown;
  Object.defineProperty(event, "returnValue", {
    configurable: true,
    get: () => returnValue,
    set: (value) => {
      returnValue = value;
    },
  });
  window.dispatchEvent(event);
  return { prevented: event.defaultPrevented, returnValue };
}

// ---------------------------------------------------------------- mounting

function Harness({ isDirty }: { isDirty: () => boolean }) {
  useLeaveGuard(isDirty);
  return null;
}

// Torn down in afterEach rather than by each test, so that a failed assertion
// cannot leave a guard listening on window and fail the next test instead.
const mounted: Array<() => Promise<void>> = [];

async function mountGuard({ dirty = true }: { dirty?: boolean } = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  await act(async () => {
    root.render(<Harness isDirty={() => dirty} />);
  });

  const unmount = async () => {
    const pending = mounted.indexOf(unmount);
    if (pending === -1) return;
    mounted.splice(pending, 1);
    await act(async () => {
      root.unmount();
    });
    container.remove();
  };
  mounted.push(unmount);
  return { unmount };
}

async function unmountAll() {
  while (mounted.length) await mounted[0]();
}

// ---------------------------------------------------------------- the tests

function stubConfirm(answer: boolean) {
  return vi.spyOn(window, "confirm").mockReturnValue(answer);
}

// The author says yes unless a test says otherwise; the interesting cases are
// the ones where nothing asks at all.
let confirmed: ReturnType<typeof stubConfirm>;

beforeEach(() => {
  confirmed = stubConfirm(true);
});

afterEach(async () => {
  await unmountAll();
  document.body.replaceChildren();
});

describe("clicking a link while the draft is dirty", () => {
  it("cancels the navigation when the author declines", async () => {
    confirmed.mockReturnValue(false);
    await mountGuard();

    expect(clickIsAllowed(link("/my-projects/project-1"))).toBe(false);
    expect(confirmed).toHaveBeenCalledOnce();
  });

  it("lets the navigation through when the author confirms", async () => {
    await mountGuard();

    expect(clickIsAllowed(link("/my-projects/project-1"))).toBe(true);
    expect(confirmed).toHaveBeenCalledOnce();
  });

  // `Link` bails on `e.defaultPrevented`, but only after running the anchor's
  // own onClick — which is how the mobile drawer and the user menu close
  // themselves. Cancelling the default must not cost them that.
  it("lets a declined click still reach the link's own handlers", async () => {
    confirmed.mockReturnValue(false);
    await mountGuard();
    const closeMenu = vi.fn();
    const target = link("/latest");
    target.addEventListener("click", closeMenu);

    expect(clickIsAllowed(target)).toBe(false);
    expect(closeMenu).toHaveBeenCalledOnce();
  });

  it("prompts for a click on anything nested inside the link", async () => {
    confirmed.mockReturnValue(false);
    await mountGuard();
    const nested = document.createElement("span");
    link("/latest").appendChild(nested);

    expect(clickIsAllowed(nested)).toBe(false);
  });

  it("says nothing about a click that missed every link", async () => {
    await mountGuard();
    const button = document.body.appendChild(document.createElement("button"));

    expect(clickIsAllowed(button)).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("leaves an already-cancelled click alone", async () => {
    await mountGuard();
    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    event.preventDefault();

    link("/latest").dispatchEvent(event);

    expect(confirmed).not.toHaveBeenCalled();
  });
});

describe("clicking a link while the draft is clean", () => {
  it("never asks", async () => {
    await mountGuard({ dirty: false });

    expect(clickIsAllowed(link("/my-projects/project-1"))).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });
});

describe("clicks that are not the author leaving the page", () => {
  const openedElsewhere: Array<[string, MouseEventInit]> = [
    ["a command-click", { metaKey: true }],
    ["a control-click", { ctrlKey: true }],
    ["a shift-click", { shiftKey: true }],
    ["an alt-click", { altKey: true }],
    ["a middle-click", { button: 1 }],
  ];

  for (const [name, init] of openedElsewhere) {
    it(`ignores ${name}, which does not take the author off the page`, async () => {
      await mountGuard();

      expect(clickIsAllowed(link("/latest"), init)).toBe(true);
      expect(confirmed).not.toHaveBeenCalled();
    });
  }

  it("ignores a link that opens in another tab", async () => {
    await mountGuard();

    expect(clickIsAllowed(anchor({ href: "/latest", target: "_blank" }))).toBe(
      true,
    );
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("ignores a download link", async () => {
    await mountGuard();

    expect(
      clickIsAllowed(anchor({ href: "/export.csv", download: "export.csv" })),
    ).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("ignores a link the author wrote into the body", async () => {
    await mountGuard();
    const body = document.body.appendChild(document.createElement("div"));
    body.setAttribute("contenteditable", "true");
    const written = document.createElement("a");
    written.setAttribute("href", "/somewhere-else");
    body.appendChild(written);

    expect(clickIsAllowed(written)).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("ignores a mailto: link", async () => {
    await mountGuard();

    expect(clickIsAllowed(link("mailto:hello@example.com"))).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("ignores a bare hash", async () => {
    await mountGuard();

    expect(clickIsAllowed(link("#"))).toBe(true);
    expect(confirmed).not.toHaveBeenCalled();
  });

  it("ignores a link to a section of this same page", async () => {
    await mountGuard();

    expect(clickIsAllowed(link(`${window.location.pathname}#images`))).toBe(
      true,
    );
    expect(confirmed).not.toHaveBeenCalled();
  });
});

describe("closing the tab", () => {
  it("asks the browser to warn while the draft is dirty", async () => {
    await mountGuard();

    // `returnValue` is the old Safari spelling of the same intent, and only
    // counts for a non-empty string; current browsers read the preventDefault.
    expect(fireBeforeUnload()).toEqual({
      prevented: true,
      returnValue: LEAVE_PROMPT,
    });
  });

  it("stays out of the way while the draft is clean", async () => {
    await mountGuard({ dirty: false });

    expect(fireBeforeUnload()).toEqual({
      prevented: false,
      returnValue: undefined,
    });
  });
});

describe("after the editor is gone", () => {
  it("guards neither clicks nor unloads", async () => {
    const guard = await mountGuard();
    await guard.unmount();

    expect(clickIsAllowed(link("/latest"))).toBe(true);
    expect(fireBeforeUnload().prevented).toBe(false);
    expect(confirmed).not.toHaveBeenCalled();
  });
});
