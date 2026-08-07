"use client";

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { api, NotificationGroup, NotificationSummary } from "@/lib/api";
import { useAuth } from "@/contexts/auth";
import { groupKey } from "@/lib/notifications";

const POLL_INTERVAL_MS = 30_000;

export interface NotificationDiffEvent {
  newlyActiveKeys: string[];
  groupsByKey: Map<string, NotificationGroup>;
}

type DiffListener = (event: NotificationDiffEvent) => void;

interface NotificationsContextValue {
  summary: NotificationSummary | null;
  groups: NotificationGroup[];
  loadingGroups: boolean;
  refreshSummary: () => Promise<void>;
  refreshGroups: () => Promise<void>;
  markThreadRead: (rootDiscussionId: string) => Promise<void>;
  markThreadByComment: (commentId: string) => Promise<void>;
  markArticleRead: (articleId: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  subscribeDiff: (listener: DiffListener) => () => void;
}

const NotificationsContext = createContext<NotificationsContextValue | undefined>(
  undefined
);

function keyedGroups(groups: NotificationGroup[]): Array<{
  key: string;
  group: NotificationGroup;
}> {
  const out: Array<{ key: string; group: NotificationGroup }> = [];
  for (const g of groups) {
    const key = groupKey(g);
    if (key) out.push({ key, group: g });
  }
  return out;
}

function diffActiveKeys(
  prev: Set<string>,
  next: NotificationGroup[]
): string[] {
  const newly: string[] = [];
  for (const { key } of keyedGroups(next)) {
    if (!prev.has(key)) newly.push(key);
  }
  return newly;
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [summary, setSummary] = useState<NotificationSummary | null>(null);
  const [groups, setGroups] = useState<NotificationGroup[]>([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const lastGroupKeysRef = useRef<Set<string>>(new Set());
  const lastGroupCountRef = useRef<number>(0);
  const listenersRef = useRef<Set<DiffListener>>(new Set());

  const fireDiff = useCallback((nextGroups: NotificationGroup[]) => {
    const newlyActiveKeys = diffActiveKeys(
      lastGroupKeysRef.current,
      nextGroups
    );
    const groupsByKey = new Map<string, NotificationGroup>();
    for (const { key, group } of keyedGroups(nextGroups)) {
      groupsByKey.set(key, group);
    }
    if (newlyActiveKeys.length > 0) {
      for (const listener of listenersRef.current) {
        listener({ newlyActiveKeys, groupsByKey });
      }
    }
    lastGroupKeysRef.current = new Set(
      keyedGroups(nextGroups).map(({ key }) => key)
    );
  }, []);

  const refreshGroups = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoadingGroups(true);
    try {
      const next = await api.notifications.listGroups();
      setGroups(next);
      fireDiff(next);
    } catch {
      // swallow — UI continues to show last known state
    } finally {
      setLoadingGroups(false);
    }
  }, [isAuthenticated, fireDiff]);

  const refreshSummary = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const next = await api.notifications.getSummary();
      setSummary(next);
      if (next.unread_group_count !== lastGroupCountRef.current) {
        lastGroupCountRef.current = next.unread_group_count;
        // group count changed — refetch groups to update popover/toaster
        await refreshGroups();
      }
    } catch {
      // swallow
    }
  }, [isAuthenticated, refreshGroups]);

  const markThreadRead = useCallback(
    async (rootDiscussionId: string) => {
      try {
        await api.notifications.markThreadRead(rootDiscussionId);
      } finally {
        await refreshSummary();
      }
    },
    [refreshSummary]
  );

  const markThreadByComment = useCallback(
    async (commentId: string) => {
      try {
        await api.notifications.markThreadByComment(commentId);
      } finally {
        await refreshSummary();
      }
    },
    [refreshSummary]
  );

  const markArticleRead = useCallback(
    async (articleId: string) => {
      try {
        await api.notifications.markArticleThread(articleId);
      } finally {
        await refreshSummary();
      }
    },
    [refreshSummary]
  );

  const markAllRead = useCallback(async () => {
    try {
      await api.notifications.markAllRead();
    } finally {
      await refreshSummary();
    }
  }, [refreshSummary]);

  const subscribeDiff = useCallback((listener: DiffListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setSummary(null);
      setGroups([]);
      lastGroupKeysRef.current = new Set();
      lastGroupCountRef.current = 0;
      return;
    }

    void refreshSummary();
    const intervalId = window.setInterval(() => {
      void refreshSummary();
    }, POLL_INTERVAL_MS);
    const onFocus = () => {
      void refreshSummary();
    };
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", onFocus);
    };
  }, [isAuthenticated, refreshSummary]);

  return (
    <NotificationsContext.Provider
      value={{
        summary,
        groups,
        loadingGroups,
        refreshSummary,
        refreshGroups,
        markThreadRead,
        markThreadByComment,
        markArticleRead,
        markAllRead,
        subscribeDiff,
      }}
    >
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (ctx === undefined) {
    throw new Error("useNotifications must be used within NotificationsProvider");
  }
  return ctx;
}
