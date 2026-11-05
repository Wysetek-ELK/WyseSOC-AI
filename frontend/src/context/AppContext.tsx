"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, api } from "@/lib/api";

interface AppContextType {
  user: User | null;
  isLoading: boolean;
  blindReviewMode: boolean;
  setBlindReviewMode: (enabled: boolean) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  theme: "dark" | "light";
  toggleTheme: () => void;
  refreshUser: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [blindReviewMode, setBlindReviewState] = useState<boolean>(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    // Load stored preferences
    const storedBlind = localStorage.getItem("ai_verdict_blind_review");
    if (storedBlind === "true") setBlindReviewState(true);

    const storedTheme = (localStorage.getItem("ai_verdict_theme") as "dark" | "light") || "dark";
    setTheme(storedTheme);
    if (storedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }

    // Check user session
    refreshUser();
  }, []);

  const refreshUser = async () => {
    setIsLoading(true);
    try {
      const u = await api.getMe();
      setUser(u);
      localStorage.setItem("ai_verdict_user", JSON.stringify(u));
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const setBlindReviewMode = (enabled: boolean) => {
    setBlindReviewState(enabled);
    localStorage.setItem("ai_verdict_blind_review", enabled ? "true" : "false");
  };

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("ai_verdict_theme", next);
    if (next === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const login = async (username: string, password: string) => {
    const res = await api.login(username, password);
    if (res.access_token) {
      localStorage.setItem("ai_verdict_token", res.access_token);
      localStorage.setItem("ai_verdict_user", JSON.stringify(res.user));
      setUser(res.user);
    }
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    window.location.href = "/login";
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
