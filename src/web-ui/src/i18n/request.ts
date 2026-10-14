import { getRequestConfig } from "next-intl/server";
import { messages } from "./messages";

// English only for now (issue #103 is groundwork). When Icelandic arrives, this
// is the one place that decides the locale — from a cookie, header or path — and
// loads that language's files. Components call t() either way and do not change.
export const DEFAULT_LOCALE = "en";

// A missing key renders as its path and is logged. In production that is the
// right trade-off; in development and tests it hides typos in components that
// nothing renders, so there it throws instead. The test shim in
// src/test/setup.ts applies the same policy.
export const onMessageError = (error: Error) => {
  if (process.env.NODE_ENV === "production") {
    console.error(error);
    return;
  }
  throw error;
};

export default getRequestConfig(async () => ({
  locale: DEFAULT_LOCALE,
  messages,
  onError: onMessageError,
}));
