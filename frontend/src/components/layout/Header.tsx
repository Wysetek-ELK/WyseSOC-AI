"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Eye,
  EyeOff,
  Sun,
  Moon,
  LogOut,
  User as UserIcon,
  Shield,
  Bell,
} from "lucide-react";
import { useApp } from "@/context/AppContext";

export function Header() {
  const router = useRouter();
  const { user, logout, blindReviewMode, setBlindReviewMode, theme, toggleTheme } = useApp();
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    router.push(`/incidents?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "Administrator":
        return "bg-rose-950/70 text-rose-300 border-rose-800/60";
      case "SOC Analyst":
        return "bg-cyan-950/70 text-cyan-300 border-cyan-800/60";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <header className="flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/90 px-6 backdrop-blur-md">
      {/* Global Search Bar */}
      <form onSubmit={handleSearch} className="relative w-96 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Global Search: Incident ID, Rule, IP, Device, File..."
          className="w-full rounded-lg border border-slate-800 bg-slate-900/80 py-1.5 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 transition-colors focus:border-cyan-500/80 focus:bg-slate-900 focus:outline-none focus:ring-1 focus:ring-cyan-500"
        />
      </form>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Blind Review Mode Toggle */}
        <button
          onClick={() => setBlindReviewMode(!blindReviewMode)}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
            blindReviewMode
              ? "border-amber-500/60 bg-amber-950/60 text-amber-300 shadow-sm shadow-amber-900/30"
              : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
          title="Blind Review Mode: Suppresses historical ground truth verdicts so analysts can investigate neutrally"
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

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* User Profile & Role */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
          <div className="flex flex-col text-right">
            <span className="text-xs font-semibold text-slate-200 leading-none">
              {user ? user.username : "Analyst"}
            </span>
            <span
              className={`mt-1 inline-block self-end rounded border px-1.5 py-0.2 text-[9px] font-mono tracking-wider uppercase ${getRoleBadge(
                user?.role || "SOC Analyst"
              )}`}
            >
              {user?.role || "Analyst"}
            </span>
          </div>

          <button
            onClick={logout}
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-rose-400 hover:border-rose-900/60 transition-colors"
            title="Sign out of AI Verdict"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
