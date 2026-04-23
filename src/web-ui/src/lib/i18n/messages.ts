import "server-only";
import { fetchCatalog } from "./catalog";
import type { Locale } from "@/i18n/config";
import enMessages from "@/messages/en.json";

type Messages = Record<string, unknown>;

function unflatten(flat: Record<string, string>): Messages {
  const out: Messages = {};
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split(".");
    let cursor: Messages = out;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (
        typeof cursor[part] !== "object" ||
        cursor[part] === null ||
        Array.isArray(cursor[part])
      ) {
        cursor[part] = {};
      }
      cursor = cursor[part] as Messages;
    }
    cursor[parts[parts.length - 1]] = value;
  }
  return out;
}

function deepMerge(base: Messages, over: Messages): Messages {
  const result: Messages = { ...base };
  for (const [k, v] of Object.entries(over)) {
    const e = result[k];
    if (
      typeof v === "object" && v !== null && !Array.isArray(v) &&
      typeof e === "object" && e !== null && !Array.isArray(e)
    ) {
      result[k] = deepMerge(e as Messages, v as Messages);
    } else {
      result[k] = v;
    }
  }
  return result;
}

export async function loadMessages(locale: Locale): Promise<{
  merged: Messages;
  localeOnly: Messages;
  english: Messages;
}> {
  const english = enMessages as Messages;
  if (locale === "en") {
    return { merged: english, localeOnly: english, english };
  }
  const flat = await fetchCatalog(locale);
  const localeOnly = unflatten(flat);
  return { merged: deepMerge(english, localeOnly), localeOnly, english };
}
