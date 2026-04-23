"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { NextIntlClientProvider } from "next-intl";
import type { Locale } from "@/i18n/config";

type Messages = Record<string, unknown>;

type EditableMessagesContextValue = {
  editMode: boolean;
  locale: Locale;
  /** True when this dotted key resolves to text from the en fallback (no row in `locale`). */
  isFallback: (dottedKey: string) => boolean;
  /** Splice text into messages at the dotted-key path; triggers re-render of all consumers. */
  applyOverride: (dottedKey: string, text: string) => void;
  /** Read the English source string at a dotted path. */
  readEnglish: (dottedKey: string) => string | undefined;
};

const EditableMessagesContext = createContext<EditableMessagesContextValue | null>(
  null,
);

export function useEditableMessages(): EditableMessagesContextValue {
  const ctx = useContext(EditableMessagesContext);
  if (ctx === null) {
    throw new Error(
      "useEditableMessages must be used inside <EditableMessagesProvider>",
    );
  }
  return ctx;
}

export function EditableMessagesProvider({
  locale,
  initialMessages,
  enMessages,
  localeOnlyMessages,
  editMode,
  children,
}: {
  locale: Locale;
  /** Already-merged messages (en deep-merged with locale catalog). What NextIntl renders. */
  initialMessages: Messages;
  /** Plain English source catalog (en.json). */
  enMessages: Messages;
  /** Locale-only catalog without the en fallback merged in. Used for fallback detection. */
  localeOnlyMessages: Messages;
  editMode: boolean;
  children: ReactNode;
}) {
  const [messages, setMessages] = useState<Messages>(initialMessages);

  const applyOverride = useCallback((dottedKey: string, text: string) => {
    setMessages((prev) => setIn(prev, dottedKey.split("."), text));
  }, []);

  const isFallback = useCallback(
    (dottedKey: string) => {
      if (locale === "en") return false;
      const parts = dottedKey.split(".");
      const localeOnly = getIn(localeOnlyMessages, parts);
      const en = getIn(enMessages, parts);
      return localeOnly === undefined && en !== undefined;
    },
    [locale, localeOnlyMessages, enMessages],
  );

  const readEnglish = useCallback(
    (dottedKey: string) => {
      const v = getIn(enMessages, dottedKey.split("."));
      return typeof v === "string" ? v : undefined;
    },
    [enMessages],
  );

  const value = useMemo<EditableMessagesContextValue>(
    () => ({ editMode, locale, isFallback, applyOverride, readEnglish }),
    [editMode, locale, isFallback, applyOverride, readEnglish],
  );

  return (
    <EditableMessagesContext.Provider value={value}>
      <NextIntlClientProvider locale={locale} messages={messages}>
        {children}
      </NextIntlClientProvider>
    </EditableMessagesContext.Provider>
  );
}

function setIn(obj: Messages, path: string[], value: string): Messages {
  if (path.length === 0) return obj;
  const [head, ...rest] = path;
  const child = obj[head];
  if (rest.length === 0) {
    return { ...obj, [head]: value };
  }
  const childObj =
    child && typeof child === "object" && !Array.isArray(child)
      ? (child as Messages)
      : {};
  return { ...obj, [head]: setIn(childObj, rest, value) };
}

function getIn(obj: Messages, path: string[]): unknown {
  let cursor: unknown = obj;
  for (const part of path) {
    if (cursor && typeof cursor === "object" && !Array.isArray(cursor)) {
      cursor = (cursor as Messages)[part];
    } else {
      return undefined;
    }
  }
  return cursor;
}
