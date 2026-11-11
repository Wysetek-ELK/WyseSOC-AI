"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { formatServer2HealthSummary } from "@/lib/provenance";
import { VerdictumLogo } from "@/components/brand/VerdictumLogo";
import {
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
  BookOpenCheck,
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
      {
        title: "AI Verdict Admin Guide",
        href: "/admin-guide",
        icon: BookOpenCheck,
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [llmStatus, setLlmStatus] = useState<{
    is_healthy: boolean;
    model?: string;
    status?: string;
    endpoint_provenance?: string;
    current_s2_health?: string;
    gpu_telemetry_verified?: boolean;
    test_environment?: string | null;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = () => {
      api.getLlmStatus()
        .then((res) => {
          if (isMounted) setLlmStatus(res);
        })
        .catch(() => {
          if (isMounted) {
            setLlmStatus({
              is_healthy: false,
              endpoint_provenance: "OFFLINE",
              current_s2_health: "OFFLINE",
              gpu_telemetry_verified: false,
            });
          }
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
            endpoint_provenance: customEvent.detail.endpoint_provenance,
            current_s2_health: customEvent.detail.current_s2_health,
            gpu_telemetry_verified: customEvent.detail.gpu_telemetry_verified,
            test_environment: customEvent.detail.test_environment,
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
      className={`relative z-10 flex flex-col theme-sidebar-shell text-slate-200 transition-all duration-200 select-none ${collapsed ? "w-12" : "w-56"
        }`}
    >
      {/* Brand Header */}
      <div className="flex h-10 items-center justify-between px-2 border-b border-slate-800/80">
        <Link
          href="/agent-mission-control"
          className="flex items-center overflow-hidden min-w-0 transition-all duration-200"
          title="Verdictum AI — Agentic Triage Platform"
        >
          <VerdictumLogo size="sm" showWordmark={!collapsed} />
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors shrink-0"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto p-1.5 space-y-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.groupTitle} className="space-y-0.5">
            {!collapsed && (
              <div className="px-2 pt-0.5 pb-0.5 text-[9px] font-mono font-semibold uppercase tracking-wider text-slate-500">
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
                  className={`flex items-center gap-2 px-2 py-1 rounded-md text-[11.5px] font-medium transition-all ${active
                      ? "theme-nav-active"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/60 border border-transparent"
                    }`}
                  title={collapsed ? item.title : undefined}
                >
                  <Icon className={`h-3.5 w-3.5 shrink-0 ${active ? "text-cyan-300" : "text-slate-400"}`} />
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
      <div className="p-2 border-t border-slate-800/80 text-[10px] font-mono">
        {(() => {
          const s2Summary = formatServer2HealthSummary(llmStatus || undefined);
          const modelDisplay = llmStatus?.model
            ? llmStatus.model.split("/").pop()?.replace(/-Instruct.*$/i, "") || llmStatus.model
            : "Qwen 2.5 7B";
          return !collapsed ? (
            <Link
              href="/inference-control"
              className="block rounded-lg theme-glass-sunken hover:border-slate-700 p-2 space-y-1 transition-colors cursor-pointer"
              title="Inspect Inference Control & Historical Health Telemetry"
              data-testid="sidebar-inference-widget"
            >
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-slate-400 text-[9px]">INFERENCE</span>
                <span className={`flex items-center gap-1 rounded px-1.5 py-0.5 border text-[9px] font-bold tracking-wide ${s2Summary.badgeClass}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${s2Summary.dotClass}`}></span>
                  {s2Summary.statusLabel}
                </span>
              </div>
              <div className="text-[9px] text-slate-400 leading-tight" data-testid="sidebar-arch-label">
                Arch: <span className="text-slate-300">{s2Summary.archLabel}</span>
              </div>
              <div className="text-[9px] text-slate-400 leading-tight flex items-center justify-between gap-1">
                <span>LLM:</span>
                {llmStatus?.is_healthy ? (
                  <span
                    className={`${s2Summary.isMockEndpoint ? "text-teal-300" : "text-emerald-400"} font-semibold flex items-center gap-1 truncate max-w-[130px]`}
                    title={llmStatus.model || s2Summary.modelStatusText}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${s2Summary.dotClass} shrink-0`}></span>
                    {s2Summary.isMockEndpoint ? `${modelDisplay} (HTTP Mock)` : `${modelDisplay} (Active)`}
                  </span>
                ) : (
                  <span className="text-rose-300">{s2Summary.modelStatusText}</span>
                )}
              </div>
              {llmStatus?.test_environment && (
                <div className="text-[8px] mt-0.5 px-1 py-0.2 rounded bg-teal-950/70 border border-teal-800/70 text-teal-300 truncate" data-testid="sidebar-test-env">
                  TEST ENV: {llmStatus.test_environment}
                </div>
              )}
            </Link>
          ) : (
            <Link
              href="/inference-control"
              className="flex justify-center py-1"
              title={`${s2Summary.archLabel} (${s2Summary.statusLabel})`}
            >
              <span
                className={`h-2 w-2 rounded-full ${s2Summary.dotClass}`}
                title={`${s2Summary.archLabel} (${s2Summary.statusLabel})`}
              ></span>
            </Link>
          );
        })()}
      </div>
    </aside>
  );
}
