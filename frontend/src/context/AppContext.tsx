"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, api } from "@/lib/api";

export type AppTheme = "obsidian" | "classic";

interface AppContextType {
  user: User | null;
  isLoading: boolean;
  blindReviewMode: boolean;
  setBlindReviewMode: (enabled: boolean) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  theme: AppTheme;
  toggleTheme: () => void;
  refreshUser: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

function applyThemeToDocument(nextTheme: AppTheme) {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", nextTheme);
  document.documentElement.classList.add("dark");
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [blindReviewMode, setBlindReviewState] = useState<boolean>(false);
  const [theme, setTheme] = useState<AppTheme>("obsidian");

  useEffect(() => {
    // Load stored preferences
    const storedBlind = localStorage.getItem("ai_verdict_blind_review");
    if (storedBlind === "true") setBlindReviewState(true);

    const rawStoredTheme = localStorage.getItem("ai_verdict_theme");
    const resolvedTheme: AppTheme =
      rawStoredTheme === "classic" ? "classic" : "obsidian";
    setTheme(resolvedTheme);
    applyThemeToDocument(resolvedTheme);

    // Check user session
    refreshUser();
  }, []);

  const refreshUser = async () => {
    if (
      typeof window !== "undefined" &&
      window.location.pathname === "/login" &&
      !localStorage.getItem("ai_verdict_token")
    ) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const u = await api.getMe();
      setUser(u);
      localStorage.setItem("ai_verdict_user", JSON.stringify(u));
    } catch {
      setUser(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem("ai_verdict_user");
        localStorage.removeItem("ai_verdict_token");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const setBlindReviewMode = (enabled: boolean) => {
    setBlindReviewState(enabled);
    localStorage.setItem("ai_verdict_blind_review", enabled ? "true" : "false");
  };

  const toggleTheme = () => {
    const next: AppTheme = theme === "obsidian" ? "classic" : "obsidian";
    setTheme(next);
    localStorage.setItem("ai_verdict_theme", next);
    applyThemeToDocument(next);
  };

  const login = async (username: string, password: string) => {
    const res = await api.login(username, password);
    if (res.access_token) {
      localStorage.setItem("ai_verdict_token", res.access_token);
      localStorage.setItem("ai_verdict_user", JSON.stringify(res.user));
      setUser(res.user);
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("ai_verdict_token");
        localStorage.removeItem("ai_verdict_user");
      }
      setUser(null);
      window.location.href = "/login";
    }
  };

  return (
    <AppContext.Provider
      value={{
        user,
        isLoading,
        blindReviewMode,
        setBlindReviewMode,
        login,
        logout,
        theme,
        toggleTheme,
        refreshUser,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}

