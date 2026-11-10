"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
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
  Server,
  MessageSquareCode,
} from "lucide-react";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
}

interface NavGroup {
  groupTitle: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupTitle: "SOC OPERATIONS",
    items: [
      {
        title: "Agent Mission Control",
        href: "/agent-mission-control",
        icon: LayoutDashboard,
      },
      {
        title: "AI Triage Workbench",
        href: "/ai-triage-workbench",
        icon: AlertTriangle,
      },
      {
        title: "Telemetry Hub",
        href: "/telemetry-hub",
        icon: UploadCloud,
      },
      {
        title: "Human Review Queue",
        href: "/human-review-queue",
        icon: UserCheck,
      },
      {
        title: "SOC AI Chatbot",
        href: "/soc-chatbot",
        icon: MessageSquareCode,
        badge: "LLM",
        badgeColor: "bg-indigo-950 text-indigo-300 border border-indigo-800",
      },
    ],
  },
  {
    groupTitle: "AGENT INTELLIGENCE",
    items: [
      {
        title: "Agent Intelligence Studio",
        href: "/agent-intelligence-studio",
        icon: Cpu,
      },
      {
        title: "Detection Intelligence",
        href: "/detection-intelligence",
        icon: FileCode2,
      },
      {
        title: "Agent Memory",
        href: "/agent-memory",
        icon: Brain,
      },
    ],
  },
  {
    groupTitle: "VALIDATION & TRUST",
    items: [
      {
        title: "Agent Simulation Lab",
        href: "/agent-simulation-lab",
        icon: FlaskConical,
      },
      {
        title: "Verdict Intelligence",
        href: "/verdict-intelligence",
        icon: BarChart3,
      },
    ],
  },
  {
    groupTitle: "PLATFORM CONTROL",
    items: [
      {
        title: "Inference Control",
        href: "/inference-control",
        icon: Server,
      },
      {
        title: "Agent Configuration",
        href: "/agent-configuration",
        icon: Settings,
      },
      {
        title: "Governance & Access",
        href: "/governance-access",
        icon: ShieldCheck,
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [llmStatus, setLlmStatus] = useState<{ is_healthy: boolean; model?: string } | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = () => {
      api.getLlmStatus()
        .then((res) => {
          if (isMounted) setLlmStatus(res);
        })
        .catch(() => {
          if (isMounted) setLlmStatus({ is_healthy: false });
        });
    };

    // Initial fetch on mount
    fetchStatus();

    // Auto-refresh every 15 seconds to reflect real-time inference engine health
    const interval = setInterval(fetchStatus, 15000);

    // Instant sync listener for changes made in Agent Configuration
    const handleStatusEvent = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail && typeof customEvent.detail.is_healthy === "boolean") {
        if (isMounted) {
          setLlmStatus({
            is_healthy: customEvent.detail.is_healthy,
            model: customEvent.detail.model,
          });
        }
      } else {
        fetchStatus();
      }
    };

    window.addEventListener("llm-status-change", handleStatusEvent);

    return () => {
      isMounted = false;
      clearInterval(interval);
      window.removeEventListener("llm-status-change", handleStatusEvent);
    };
  }, []);

  const isItemActive = (href: string) => {
    if (href === "/agent-mission-control") {
      return pathname === "/" || pathname === "/agent-mission-control";
    }
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <aside
      className={`relative flex flex-col border-r border-slate-800 bg-slate-950 text-slate-200 transition-all duration-200 select-none ${
        collapsed ? "w-14" : "w-60"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-12 items-center justify-between px-3 border-b border-slate-800">
        <Link href="/agent-mission-control" className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-cyan-600/20 text-cyan-400 border border-cyan-500/30">
            <ShieldAlert className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-xs tracking-wider text-slate-100 uppercase">
                AI Verdict
              </span>
              <span className="text-[9px] text-cyan-400 font-mono tracking-tight leading-none">
                Agentic SOC Intelligence Platform
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

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.groupTitle} className="space-y-0.5">
            {!collapsed && (
              <div className="px-2 pt-1 pb-0.5 text-[9px] font-mono font-semibold uppercase tracking-wider text-slate-500">
                {group.groupTitle}
              </div>
            )}
            {group.items.map((item) => {
              const active = isItemActive(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                    active
                      ? "bg-cyan-950/60 text-cyan-300 border border-cyan-700/50 shadow-sm shadow-cyan-900/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                  }`}
                  title={collapsed ? item.title : undefined}
                >
                  <Icon className={`h-3.5 w-3.5 shrink-0 ${active ? "text-cyan-400" : "text-slate-400"}`} />
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
          </div>
        ))}
      </nav>

      {/* Footer System Status */}
      <div className="p-2 border-t border-slate-800 text-[10px] font-mono">
        {!collapsed ? (
          <Link
            href="/inference-control"
            className="block rounded-md bg-slate-900/70 hover:bg-slate-900 p-2 border border-slate-800 hover:border-slate-700 space-y-0.5 transition-colors cursor-pointer"
            title="Inspect Inference Control & Historical Health Telemetry"
          >
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-slate-400 text-[9px]">INFERENCE</span>
              <span className="flex items-center gap-1 text-emerald-400 text-[9px]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE
              </span>
            </div>
            <div className="text-[9px] text-slate-400 leading-tight">
              Arch: <span className="text-slate-300">{llmStatus?.is_healthy ? "S1 + S2 (GPU)" : "Server 1"}</span>
            </div>
            <div className="text-[9px] text-slate-400 leading-tight flex items-center justify-between">
              <span>LLM:</span>
              {llmStatus?.is_healthy ? (
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Qwen 2.5 7B (Active)
                </span>
              ) : (
                <span className="text-amber-400">P1 (Native)</span>
              )}
            </div>
          </Link>
        ) : (
          <Link href="/inference-control" className="flex justify-center py-1" title="Inference Control Active">
            <span className="h-2 w-2 rounded-full bg-emerald-400" title="Inference Control Active"></span>
          </Link>
        )}
      </div>
    </aside>
  );
}
