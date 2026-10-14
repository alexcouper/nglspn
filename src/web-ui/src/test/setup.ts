import { afterEach, vi } from "vitest";

// Components read their copy through next-intl, whose hooks need a provider.
// Tests mount components bare with createRoot, so instead of wrapping every
// mount, the hooks are replaced with translators over the real English
// messages. Tests keep asserting on the visible English text.
vi.mock("next-intl", async (importOriginal) => {
  const actual = await importOriginal<typeof import("next-intl")>();
  const { messages } = await import("@/i18n/messages");
  const locale = "en";
  return {
    ...actual,
    useLocale: () => locale,
    useFormatter: () => actual.createFormatter({ locale }),
    useTranslations: (namespace?: string) =>
      actual.createTranslator({ locale, messages, namespace } as never),
  };
});

vi.mock("next-intl/server", async (importOriginal) => {
  const actual = await importOriginal<typeof import("next-intl/server")>();
  const { createTranslator, createFormatter } = await import("next-intl");
  const { messages } = await import("@/i18n/messages");
  const locale = "en";
  return {
    ...actual,
    getLocale: async () => locale,
    getFormatter: async () => createFormatter({ locale }),
    getTranslations: async (namespace?: string | { namespace?: string }) =>
      createTranslator({
        locale,
        messages,
        namespace: typeof namespace === "string" ? namespace : namespace?.namespace,
      } as never),
  };
});

// React requires this to be set so act() works without a warning.
(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// jsdom ships HTMLDialogElement but not its modal methods, so anything built on
// components/Dialog.tsx throws on mount. Enough of a stand-in to drive the
// open/close cycle — it does not emulate the top layer or focus trapping.
if (
  typeof HTMLDialogElement !== "undefined" &&
  typeof HTMLDialogElement.prototype.showModal !== "function"
) {
  HTMLDialogElement.prototype.show = function show() {
    this.open = true;
  };
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close(returnValue?: string) {
    this.open = false;
    if (returnValue !== undefined) this.returnValue = returnValue;
    this.dispatchEvent(new Event("close"));
  };
}

afterEach(() => {
  localStorage.clear();
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0].trim();
    if (name) {
      document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
