"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { useApp } from "@/context/AppContext";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return (
      <div className="relative min-h-screen theme-body overflow-hidden">
        <div aria-hidden="true" className="theme-ambient-backdrop pointer-events-none fixed inset-0 z-0" />
        <main className="relative z-10 min-h-screen">{children}</main>
      </div>
    );
  }

  return (
    <div className="relative flex h-screen w-full overflow-hidden theme-body font-sans text-xs">
      <div aria-hidden="true" className="theme-ambient-backdrop pointer-events-none fixed inset-0 z-0" />
      <Sidebar />
      <div className="relative z-10 flex flex-1 flex-col overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto theme-main-canvas p-2 sm:p-2.5">
          {children}
        </main>
      </div>
    </div>
  );
}

