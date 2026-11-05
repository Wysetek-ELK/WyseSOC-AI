"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert,
  LayoutDashboard,
  AlertTriangle,
  UserCheck,
  FileCode2,
  Cpu,
  Brain,
  FlaskConical,
  BarChart3,
  Settings,
  ShieldCheck,
  UploadCloud,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
} from "lucide-react";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
  phase?: number;
}

const NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Incidents",
    href: "/incidents",
    icon: AlertTriangle,
  },
  {
    title: "Data Ingestion",
    href: "/imports",
    icon: UploadCloud,
  },
  {
    title: "SIEM Rules",
    href: "/rules",
    icon: FileCode2,
  },
  {
    title: "Analyst Attention",
    href: "/analyst-attention",
    icon: UserCheck,
  },
  {
    title: "Rule Prompt Studio",
    href: "/prompt-studio",
    icon: Cpu,
  },
  {
    title: "Learning History",
    href: "/learning-history",
    icon: Brain,
  },
  {
    title: "Dry-Run Testing",
    href: "/dry-run",
    icon: FlaskConical,
    badge: "Phase 3",
    badgeColor: "bg-purple-950 text-purple-400 border border-purple-800/60",
    phase: 3,
  },
  {
    title: "Evaluation Reports",
    href: "/evaluation-reports",
    icon: BarChart3,
    badge: "Phase 3",
    badgeColor: "bg-purple-950 text-purple-400 border border-purple-800/60",
    phase: 3,
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
  {
    title: "Administration",
    href: "/admin",
    icon: ShieldCheck,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`relative flex flex-col border-r border-slate-800 bg-slate-950 text-slate-200 transition-all duration-200 select-none ${
        collapsed ? "w-20" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-3 overflow-hidden">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-cyan-600/20 text-cyan-400 border border-cyan-500/30">
            <ShieldAlert className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-wider text-slate-100 uppercase">
                AI Verdict
              </span>
              <span className="text-[10px] text-cyan-400 font-mono tracking-tight">
                SOC PLATFORM · P1
              </span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-cyan-950/60 text-cyan-300 border border-cyan-700/50 shadow-sm shadow-cyan-900/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
              }`}
              title={collapsed ? item.title : undefined}
            >
              <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
              {!collapsed && (
                <div className="flex flex-1 items-center justify-between overflow-hidden">
                  <span className="truncate">{item.title}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-mono tracking-wider ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div className="p-3 border-t border-slate-800 text-[11px] font-mono">
        {!collapsed ? (
          <div className="rounded-lg bg-slate-900/70 p-2.5 border border-slate-800">
            <div className="flex items-center justify-between mb-1">
              <span className="text-slate-400 text-[10px]">ENVIRONMENT</span>
              <span className="flex items-center gap-1.5 text-emerald-400 text-[10px]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE
              </span>
            </div>
            <div className="text-[10px] text-slate-400">
              Architecture: <span className="text-slate-300">Server 1 (Native)</span>
            </div>
            <div className="text-[10px] text-slate-400">
              Local LLM: <span className="text-amber-400">Not Integrated (Phase 1)</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="h-2 w-2 rounded-full bg-emerald-400" title="System Active"></span>
          </div>
        )}
      </div>
    </aside>
  );
}

