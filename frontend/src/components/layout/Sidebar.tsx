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
  },
  {
    title: "Evaluation Reports",
    href: "/evaluation-reports",
    icon: BarChart3,
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
        collapsed ? "w-14" : "w-56"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-12 items-center justify-between px-3 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-cyan-600/20 text-cyan-400 border border-cyan-500/30">
            <ShieldAlert className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-xs tracking-wider text-slate-100 uppercase">
                AI Verdict
              </span>
              <span className="text-[9px] text-cyan-400 font-mono tracking-tight leading-none">
                SOC PLATFORM · P1
              </span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? "bg-cyan-950/60 text-cyan-300 border border-cyan-700/50 shadow-sm shadow-cyan-900/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
              }`}
              title={collapsed ? item.title : undefined}
            >
              <Icon className={`h-3.5 w-3.5 shrink-0 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
              {!collapsed && (
                <div className="flex flex-1 items-center justify-between overflow-hidden">
                  <span className="truncate">{item.title}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded uppercase font-mono tracking-wider ${item.badgeColor}`}
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
      <div className="p-2 border-t border-slate-800 text-[10px] font-mono">
        {!collapsed ? (
          <div className="rounded-md bg-slate-900/70 p-2 border border-slate-800 space-y-0.5">
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-slate-400 text-[9px]">ENV</span>
              <span className="flex items-center gap-1 text-emerald-400 text-[9px]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE
              </span>
            </div>
            <div className="text-[9px] text-slate-400 leading-tight">
              Arch: <span className="text-slate-300">Server 1</span>
            </div>
            <div className="text-[9px] text-slate-400 leading-tight">
              LLM: <span className="text-amber-400">P1 (Native)</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400" title="System Active"></span>
          </div>
        )}
      </div>
    </aside>
  );
}

