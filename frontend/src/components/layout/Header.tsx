"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Eye,
  EyeOff,
  Sparkles,
  Layers,
  LogOut,
} from "lucide-react";
import { useApp } from "@/context/AppContext";

export function Header() {
  const router = useRouter();
  const { user, isLoading, logout, blindReviewMode, setBlindReviewMode, theme, toggleTheme } = useApp();
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    router.push(`/ai-triage-workbench?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "Administrator":
        return "bg-rose-950/70 text-rose-300 border-rose-800/60";
      case "SOC Analyst":
        return "bg-cyan-950/70 text-cyan-300 border-cyan-800/60";
      case "Read-Only Viewer":
        return "bg-amber-950/70 text-amber-300 border-amber-800/60";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const displayName = user ? user.username : isLoading ? "Verifying..." : "Guest";
  const displayRole = user?.role ? user.role : isLoading ? "SYNCING" : "UNAUTHENTICATED";

  return (
    <header className="flex h-12 items-center justify-between theme-glass-header px-3.5">
      {/* Global Search Bar */}
      <form onSubmit={handleSearch} className="relative w-72 sm:w-80 md:w-96 max-w-md">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Global Triage Search: Incident ID, Rule, Source IP, Device, File..."
          className="w-full rounded-md border border-slate-800 bg-slate-950/80 py-1 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 transition-colors focus:border-cyan-500/80 focus:bg-slate-950 focus:outline-none focus:ring-1 focus:ring-cyan-500"
        />
      </form>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-2.5">
        {/* Blind Review Mode Toggle */}
        <button
          onClick={() => setBlindReviewMode(!blindReviewMode)}
          className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-all ${
            blindReviewMode
              ? "border-amber-500/60 bg-amber-950/60 text-amber-300 shadow-sm shadow-amber-900/30"
              : "theme-secondary-btn"
          }`}
          title="Blind Review Safeguard: Suppresses historical ground truth verdicts so analysts can investigate neutrally"
        >
          {blindReviewMode ? (
            <>
              <EyeOff className="h-3.5 w-3.5 text-amber-400" />
              <span>Blind Review: <strong className="text-amber-400">ON</strong></span>
            </>
          ) : (
            <>
              <Eye className="h-3.5 w-3.5 text-slate-400" />
              <span>Blind Review: OFF</span>
            </>
          )}
        </button>

        {/* Theme Switcher: Obsidian Glass (Default) vs Classic Slate */}
        <button
          type="button"
          onClick={toggleTheme}
          data-testid="theme-toggle-btn"
          className="flex items-center gap-1.5 px-2 py-1 rounded-md theme-secondary-btn text-[11px] font-medium transition-colors"
          title={
            theme === "obsidian"
              ? "Switch to Classic Slate & Cyan theme"
              : "Switch to Obsidian Glass (Default) theme"
          }
        >
          {theme === "obsidian" ? (
            <>
              <Sparkles className="h-3.5 w-3.5 text-sky-400" />
              <span className="hidden md:inline">Obsidian</span>
            </>
          ) : (
            <>
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              <span className="hidden md:inline">Classic</span>
            </>
          )}
        </button>

        {/* User Profile & Role */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="flex flex-col text-right">
            <span className="text-xs font-semibold text-slate-200 leading-none" data-testid="header-user-name">
              {displayName}
            </span>
            <span
              data-testid="header-user-role"
              className={`mt-0.5 inline-block self-end rounded border px-1 py-0.2 text-[9px] font-mono tracking-wider uppercase leading-none ${getRoleBadge(
                displayRole
              )}`}
            >
              {displayRole}
            </span>
          </div>

          <button
            onClick={logout}
            className="p-1 rounded-md theme-secondary-btn text-slate-400 hover:text-rose-400 hover:border-rose-900/60 transition-colors"
            title="Sign out of AI Verdict"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
