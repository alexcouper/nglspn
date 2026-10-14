import { getRequestConfig } from "next-intl/server";
import { messages } from "./messages";

// English only for now (issue #103 is groundwork). When Icelandic arrives, this
// is the one place that decides the locale — from a cookie, header or path — and
// loads that language's files. Components call t() either way and do not change.
export const DEFAULT_LOCALE = "en";

export default getRequestConfig(async () => ({
  locale: DEFAULT_LOCALE,
  messages,
}));
