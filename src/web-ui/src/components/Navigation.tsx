"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth";
import { UserMenu } from "./UserMenu";

export function Navigation() {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const { isAuthenticated, isLoading, logout } = useAuth();

  const isActive = (path: string) => {
    if (path === "/") return pathname === "/";
    return pathname.startsWith(path);
  };

  const linkClass = (path: string) =>
    `text-sm transition-colors duration-150 ${
      isActive(path)
        ? "text-white font-medium"
        : "text-slate-400 hover:text-white"
    }`;

  const mobileLinkClass = (path: string) =>
    `block py-3 text-base transition-colors duration-150 ${
      isActive(path)
        ? "text-foreground font-medium"
        : "text-slate-500 hover:text-foreground"
    }`;

  const closeMenu = () => setMenuOpen(false);

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-nav-bg border-b border-white/[0.08]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Hamburger - mobile */}
          <button
            onClick={() => setMenuOpen(true)}
            className="md:hidden p-1.5 -ml-1.5 text-slate-400 hover:text-white transition-colors"
            aria-label="Open menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Logo + Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/" className="text-white font-semibold text-sm tracking-tight mr-2">
              naglasúpan
            </Link>
            <Link href="/about" className={linkClass("/about")}>About</Link>
            <Link href="/projects" className={linkClass("/projects")}>Projects</Link>
            <Link href="/competitions" className={linkClass("/competitions")}>Competitions</Link>
          </div>

          {/* Mobile logo */}
          <Link href="/" className="md:hidden text-white font-semibold text-sm tracking-tight">
            naglasúpan
          </Link>

          {/* Desktop auth */}
          <div className="hidden md:flex items-center gap-6">
            {isAuthenticated && (
              <Link href="/my-projects" className={linkClass("/my-projects")}>My Projects</Link>
            )}
            {isAuthenticated && (
              <Link href="/my-reviews" className={linkClass("/my-reviews")}>My Reviews</Link>
            )}
            {isLoading ? (
              <span className="text-slate-600 text-sm">...</span>
            ) : isAuthenticated ? (
              <UserMenu />
            ) : (
              <div className="flex items-center gap-3">
                <Link href="/login" className={linkClass("/login")}>Log in</Link>
                <Link
                  href="/register"
                  className="text-sm font-medium bg-accent hover:bg-accent-hover text-white px-3.5 py-1.5 rounded-md transition-colors duration-150"
                >
                  Register
                </Link>
              </div>
            )}
          </div>

          {/* Mobile spacer */}
          <div className="md:hidden w-8" />
        </div>
      </nav>

      {/* Mobile overlay */}
      {menuOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 md:hidden"
          onClick={closeMenu}
        />
      )}

      {/* Mobile slide-in */}
      <div
        className={`fixed top-0 left-0 bottom-0 w-72 bg-white z-50 transform transition-transform duration-200 ease-out md:hidden ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-6">
            <span className="font-semibold text-sm text-foreground tracking-tight">naglasúpan</span>
            <button
              onClick={closeMenu}
              className="p-1.5 text-slate-400 hover:text-foreground transition-colors"
              aria-label="Close menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-0.5 border-b border-slate-100 pb-4 mb-4">
            <Link href="/" className={mobileLinkClass("/")} onClick={closeMenu}>Home</Link>
            <Link href="/about" className={mobileLinkClass("/about")} onClick={closeMenu}>About</Link>
            <Link href="/projects" className={mobileLinkClass("/projects")} onClick={closeMenu}>Projects</Link>
            <Link href="/competitions" className={mobileLinkClass("/competitions")} onClick={closeMenu}>Competitions</Link>
          </div>

          <div className="space-y-0.5">
            {isAuthenticated && (
              <Link href="/my-projects" className={mobileLinkClass("/my-projects")} onClick={closeMenu}>My Projects</Link>
            )}
            {isAuthenticated && (
              <Link href="/my-reviews" className={mobileLinkClass("/my-reviews")} onClick={closeMenu}>My Reviews</Link>
            )}
            {isLoading ? (
              <span className="block py-3 text-base text-slate-400">...</span>
            ) : isAuthenticated ? (
              <>
                <Link href="/profile" className={mobileLinkClass("/profile")} onClick={closeMenu}>Profile</Link>
                <div className="border-t border-slate-100 my-3" />
                <button
                  onClick={() => { logout(); closeMenu(); }}
                  className="block py-3 text-base text-slate-500 hover:text-foreground transition-colors"
                >
                  Log out
                </button>
              </>
            ) : (
              <div className="pt-2 space-y-2">
                <Link
                  href="/login"
                  className="block w-full text-center py-2.5 text-sm font-medium text-foreground border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                  onClick={closeMenu}
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  className="block w-full text-center py-2.5 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
                  onClick={closeMenu}
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
