"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import { Avatar } from "./Avatar";

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { logout, user } = useAuth();
  const t = useTranslations("common.nav");

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayName = user?.first_name || user?.email?.split("@")[0];

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
        aria-label={t("userMenu")}
      >
        {user ? (
          <Avatar
            src={user.avatar_url}
            firstName={user.first_name}
            lastName={user.last_name}
            size={24}
            className="text-[10px]"
          />
        ) : null}
        {displayName}
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-44 bg-white rounded-lg shadow-lg border border-border py-1 z-10">
          {user && user.pending_onboarding_steps.length === 0 && (
            <>
              <Link
                href="/profile"
                className="block px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                onClick={() => setIsOpen(false)}
              >
                {t("profile")}
              </Link>
              <Link
                href="/notifications"
                className="block px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                onClick={() => setIsOpen(false)}
              >
                {t("notifications")}
              </Link>
              <Link
                href="/profile/following"
                className="block px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                onClick={() => setIsOpen(false)}
              >
                {t("following")}
              </Link>
              <Link
                href="/profile/settings"
                className="block px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                onClick={() => setIsOpen(false)}
              >
                {t("settings")}
              </Link>
              <div className="border-t border-border my-1" />
            </>
          )}
          <button
            onClick={() => {
              logout();
              setIsOpen(false);
            }}
            className="block w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            {t("logOut")}
          </button>
        </div>
      )}
    </div>
  );
}
