"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { formatServer2HealthSummary } from "@/lib/provenance";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { BrandLogo } from "@/components/common/BrandLogo";
import { NavigationIcon } from "@/components/navigation/NavigationIcon";
import type { NavigationPageId } from "@/config/navigationIcons";
import { BRANDING } from "@/config/branding";

interface NavItem {
  id: NavigationPageId;
  title: string;
  href: string;
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
        id: "agent-mission-control",
        title: "Agent Mission Control",
        href: "/agent-mission-control",
      },
      {
        id: "ai-triage-workbench",
        title: "AI Triage Workbench",
        href: "/ai-triage-workbench",
      },
      {
        id: "telemetry-hub",
        title: "Telemetry Hub",
        href: "/telemetry-hub",
      },
      {
        id: "human-review-queue",
        title: "Human Review Queue",
        href: "/human-review-queue",
      },
      {
        id: "soc-chatbot",
        title: "Verdictum Sentinel",
        href: "/soc-chatbot",
        badge: "COPILOT",
        badgeColor: "bg-indigo-950 text-indigo-300 border border-indigo-800",
      },
    ],
  },
  {
    groupTitle: "AGENT INTELLIGENCE",
    items: [
      {
        id: "agent-intelligence-studio",
        title: "Agent Intelligence Studio",
        href: "/agent-intelligence-studio",
      },
      {
        id: "detection-intelligence",
        title: "Detection Intelligence",
        href: "/detection-intelligence",
      },
      {
        id: "agent-memory",
        title: "Agent Memory",
        href: "/agent-memory",
      },
    ],
  },
  {
    groupTitle: "VALIDATION & TRUST",
    items: [
      {
        id: "agent-simulation-lab",
        title: "Agent Simulation Lab",
        href: "/agent-simulation-lab",
      },
      {
        id: "verdict-intelligence",
        title: "Verdict Intelligence",
        href: "/verdict-intelligence",
      },
    ],
  },
  {
    groupTitle: "PLATFORM CONTROL",
    items: [
      {
        id: "inference-control",
        title: "Inference Control",
        href: "/inference-control",
      },
      {
        id: "agent-configuration",
        title: "Agent Configuration",
        href: "/agent-configuration",
      },
      {
        id: "governance-access",
        title: "Governance & Access",
        href: "/governance-access",
      },
      {
        id: "admin-guide",
        title: "Verdictum AI Admin Guide",
        href: "/admin-guide",
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
      aria-label="Primary sidebar"
      data-sidebar-collapsed={collapsed ? "true" : "false"}
      className={`relative z-10 flex flex-col theme-sidebar-shell text-slate-200 transition-all duration-200 motion-reduce:transition-none select-none ${
        collapsed ? "w-14" : "w-60"
      }`}
    >
      {/* Brand Header */}
      <div
        className={`flex items-center border-b border-slate-800/80 ${
          collapsed
            ? "flex-col justify-center gap-1 py-2 px-1"
            : "min-h-11 py-1.5 justify-between px-2.5"
        }`}
      >
        <Link
          href="/agent-mission-control"
          className={`flex items-center ${
            collapsed ? "justify-center shrink-0" : "gap-2 overflow-hidden min-w-0"
          }`}
          title={`${BRANDING.product.name} ${BRANDING.company.sidebarAttribution} — ${BRANDING.product.agenticSubtitle}`}
        >
          <BrandLogo size={collapsed ? 28 : 26} priority />
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-xs tracking-wider text-sky-300 uppercase leading-tight">
                {BRANDING.product.name}
              </span>
              <span className="text-[8.5px] text-cyan-400 font-mono tracking-tight leading-none">
                {BRANDING.product.agenticSubtitle}
              </span>
              <span
                className="text-[8px] text-amber-300/85 font-mono tracking-wider uppercase leading-tight mt-0.5 font-medium"
                data-testid="sidebar-company-tagline"
              >
                {BRANDING.company.sidebarAttribution}
              </span>
            </div>
          )}
        </Link>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className={`rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors shrink-0 ${
            collapsed ? "w-full flex items-center justify-center py-0.5" : "p-1"
          }`}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Navigation Groups */}
      <nav aria-label="Main navigation" className="flex-1 overflow-y-auto p-1.5 space-y-2">
        {NAV_GROUPS.map((group, groupIdx) => (
          <div key={group.groupTitle} className="space-y-0.5">
            {collapsed ? (
              groupIdx > 0 && (
                <div
                  aria-hidden="true"
                  className="mx-1.5 my-1 border-t border-slate-800/70"
                />
              )
            ) : (
              <div className="px-2 pt-0.5 pb-0.5 text-[9px] font-mono font-semibold uppercase tracking-wider text-slate-500">
                {group.groupTitle}
              </div>
            )}
            {group.items.map((item) => {
              const active = isItemActive(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  aria-label={item.title}
                  data-nav-id={item.id}
                  data-nav-active={active ? "true" : "false"}
                  className={`nav-item-link flex items-center rounded-md text-[11.5px] font-medium ${
                    collapsed
                      ? "justify-center p-1"
                      : "gap-2 px-1.5 py-[3px]"
                  } ${
                    active
                      ? "theme-nav-active font-semibold"
                      : "text-slate-300/90 hover:text-slate-100 hover:bg-slate-900/70 border border-transparent"
                  }`}
                  title={collapsed ? item.title : undefined}
                >
                  <NavigationIcon
                    pageId={item.id}
                    size={collapsed ? "collapsed" : "expanded"}
                    active={active}
                  />
                  {!collapsed && (
                    <div className="flex flex-1 items-center justify-between gap-1.5 min-w-0 overflow-hidden">
                      <span className="truncate">{item.title}</span>
                      {item.badge && (
                        <span
                          className={`shrink-0 text-[9px] px-1.5 py-0.2 rounded uppercase font-mono tracking-wider ${item.badgeColor}`}
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

      {/* Footer System Status & Company Branding */}
      <div className="p-2 border-t border-slate-800/80 text-[10px] font-mono">
        {(() => {
          const s2Summary = formatServer2HealthSummary(llmStatus || undefined);
          const modelDisplay = llmStatus?.model
            ? llmStatus.model.split("/").pop()?.replace(/-Instruct.*$/i, "") || llmStatus.model
            : "Qwen 2.5 7B";
          return !collapsed ? (
            <>
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
              <div className="mt-2 pt-1.5 border-t border-slate-800/70 px-0.5 text-center">
                <p
                  className="text-[9px] text-slate-500 leading-tight font-sans tracking-tight break-words select-none"
                  title={BRANDING.company.copyrightNotice}
                  data-testid="sidebar-company-footer"
                >
                  {BRANDING.company.copyrightNotice}
                </p>
              </div>
            </>
          ) : (
            <>
              <Link
                href="/inference-control"
                className="flex justify-center py-1"
                title={`${s2Summary.archLabel} (${s2Summary.statusLabel})`}
                data-testid="sidebar-inference-widget"
              >
                <span
                  className={`h-2 w-2 rounded-full ${s2Summary.dotClass}`}
                  title={`${s2Summary.archLabel} (${s2Summary.statusLabel})`}
                ></span>
              </Link>
              <div
                className="mt-1 flex justify-center text-center cursor-default"
                title={BRANDING.company.copyrightNotice}
                aria-label={BRANDING.company.copyrightNotice}
                data-testid="sidebar-company-footer"
              >
                <span className="text-[8px] font-mono text-slate-600 font-semibold select-none hover:text-amber-400/80 transition-colors">
                  ©
                </span>
              </div>
            </>
          );
        })()}
      </div>
    </aside>
  );
}
