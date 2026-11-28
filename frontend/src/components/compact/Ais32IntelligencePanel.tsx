"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  FileText,
  Lock,
  Plus,
  RefreshCw,
  Scale,
  Shield,
  ShieldCheck,
  X,
} from "lucide-react";
import { ais32Api, Ais32ContractSummary, Ais32OrgContextItem } from "@/lib/api";

interface Ais32IntelligencePanelProps {
  variant: "overview" | "accuracy";
  isAdmin: boolean;
  isViewer?: boolean;
  selectedRuleId?: string | null;
}

export function Ais32IntelligencePanel({
  variant,
  isAdmin,
  isViewer = false,
  selectedRuleId,
}: Ais32IntelligencePanelProps) {
  const [overview, setOverview] = useState<Record<string, any> | null>(null);
  const [contracts, setContracts] = useState<Ais32ContractSummary[]>([]);
  const [orgTypes, setOrgTypes] = useState<string[]>([]);
  const [orgItems, setOrgItems] = useState<Ais32OrgContextItem[]>([]);
  const [ais33Plan, setAis33Plan] = useState<Record<string, any> | null>(null);
  const [evalModeA, setEvalModeA] = useState<Record<string, any> | null>(null);
  const [evalModeB, setEvalModeB] = useState<Record<string, any> | null>(null);
  const [runKeyInput, setRunKeyInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedRuleTable, setExpandedRuleTable] = useState(true);

  // Contract Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerDetail, setDrawerDetail] = useState<Record<string, any> | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [approvingContract, setApprovingContract] = useState(false);

  // Org Context Modal state
  const [orgModalOpen, setOrgModalOpen] = useState(false);
  const [newCustomer, setNewCustomer] = useState("DEFAULT");
  const [newType, setNewType] = useState("AUTHORIZED_SCANNER");
  const [newValue, setNewValue] = useState("");
  const [newPattern, setNewPattern] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [savingOrg, setSavingOrg] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const ov = await ais32Api.getOverview();
      setOverview(ov);
      setAis33Plan(ov?.ais33_readiness || null);

      if (variant === "overview") {
        const [cRes, tRes, oRes] = await Promise.all([
          ais32Api.listContracts(),
          ais32Api.getOrgContextTypes(),
          ais32Api.listOrgContext(),
        ]);
        setContracts(cRes.items || []);
        setOrgTypes(tRes.supported_types || []);
        setOrgItems(oRes.items || []);
      } else {
        const latest = ov?.latest_run_summary;
        if (latest?.run_key) {
          setRunKeyInput(latest.run_key);
          try {
            const ev = await ais32Api.evaluateRun(latest.run_key, latest.mode);
            if (latest.mode === "MODE_A") setEvalModeA(ev);
            else setEvalModeB(ev);
          } catch {
            // Non-fatal if latest run eval restricted to Admin
          }
        }
      }
    } catch (err: any) {
      setErrorMsg(err?.message || "Could not load AIS 3.2 intelligence metadata");
    } finally {
      setLoading(false);
    }
  }, [variant]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleOpenContract = async (ruleId: string) => {
    setDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const d = await ais32Api.getContractDetail(ruleId);
      setDrawerDetail(d);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to load dynamic rule contract");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleApproveContract = async (ruleId: string) => {
    setApprovingContract(true);
    try {
      const updated = await ais32Api.saveContract(ruleId, { overrides: {}, approve: true });
      setDrawerDetail(updated);
      await loadAll();
    } catch (err: any) {
      setErrorMsg(err?.message || "Contract approval failed");
    } finally {
      setApprovingContract(false);
    }
  };

  const handleCreateOrgContext = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newValue.trim()) return;
    setSavingOrg(true);
    try {
      await ais32Api.createOrgContext({
        customer: newCustomer.trim() || "DEFAULT",
        context_type: newType,
        context_value: newValue.trim(),
        match_pattern: newPattern.trim() || newValue.trim(),
        description: newDesc.trim(),
        auto_approve: isAdmin,
      });
      setNewValue("");
      setNewPattern("");
      setNewDesc("");
      const oRes = await ais32Api.listOrgContext();
      setOrgItems(oRes.items || []);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to create organizational context");
    } finally {
      setSavingOrg(false);
    }
  };

  const handleDecideOrg = async (id: string, action: "APPROVE" | "REJECT" | "REVOKE") => {
    try {
      await ais32Api.decideOrgContext(id, { action });
      const oRes = await ais32Api.listOrgContext();
      setOrgItems(oRes.items || []);
    } catch (err: any) {
      setErrorMsg(err?.message || "Decision update failed");
    }
  };

  const handleEvaluateRunKey = async () => {
    if (!runKeyInput.trim()) return;
    setErrorMsg(null);
    try {
      const [resA, resB] = await Promise.allSettled([
        ais32Api.evaluateRun(runKeyInput.trim(), "MODE_A"),
        ais32Api.evaluateRun(runKeyInput.trim(), "MODE_B"),
      ]);
      if (resA.status === "fulfilled") setEvalModeA(resA.value);
      if (resB.status === "fulfilled") setEvalModeB(resB.value);
      if (resA.status === "rejected" && resB.status === "rejected") {
        setErrorMsg(`No evaluation results found for run key '${runKeyInput.trim()}'`);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || "Run evaluation failed");
    }
  };

  if (loading && !overview) {
    return (
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 text-xs text-slate-400 flex items-center gap-2">
        <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
        Loading AIS 3.2 Universal Rule Intelligence...
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid={`ais32-panel-${variant}`}>
      {errorMsg && (
        <div className="p-2.5 rounded-lg border border-rose-800/70 bg-rose-950/30 text-xs text-rose-300 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg(null)} className="text-rose-200 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {variant === "overview" && (
        <>
          {/* Compact AIS 3.2 Overview Strip */}
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/80 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-bold text-slate-100">
                  AIS 3.2 Universal Rule Intelligence Overview
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/70 border border-cyan-800/70 text-cyan-300">
                  Engine {overview?.engine_version || "3.2.0"} • Validator {overview?.validator_version || "3.2.0"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setOrgModalOpen(true)}
                  className="px-2.5 py-1 rounded-md border border-indigo-700/70 bg-indigo-950/60 hover:bg-indigo-900/70 text-indigo-200 text-[11px] font-semibold flex items-center gap-1"
                >
                  <Building2 className="w-3.5 h-3.5" />
                  Org Context ({orgItems.filter((i) => i.approval_status === "APPROVED").length} approved)
                </button>
                <button
                  type="button"
                  onClick={loadAll}
                  className="p-1.5 rounded-md border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300"
                  title="Refresh AIS 3.2 overview"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
              <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Rule Coverage</span>
                <strong className="font-mono text-sm text-cyan-300">
                  {overview?.mapped_rules ?? 0} / {overview?.total_rules ?? 0}
                </strong>
                <span className="text-[10px] text-slate-500 block">Archetypes mapped</span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Canonical Archetypes</span>
                <strong className="font-mono text-sm text-emerald-300">{overview?.archetype_count ?? 11}</strong>
                <span className="text-[10px] text-slate-500 block">Modular validator profiles</span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Rule Contracts</span>
                <strong className="font-mono text-sm text-slate-100">
                  {overview?.approved_contracts ?? 0} Appr / {overview?.provisional_contracts ?? 0} Prov
                </strong>
                <span className="text-[10px] text-slate-500 block">Versioned &amp; hashed</span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Protected Holdouts</span>
                <strong className="font-mono text-xs text-emerald-300 flex items-center gap-1">
                  <Lock className="w-3 h-3" /> ISOLATED &amp; LOCKED
                </strong>
                <span className="text-[10px] text-slate-500 block">
                  AIS 2.6e ({overview?.protected_cohorts?.AIS_2_6E_FROZEN_20?.item_count ?? 0}) &amp; 3.0 ({overview?.protected_cohorts?.AIS_3_0_INDEPENDENT_HOLDOUT_100?.item_count ?? 0})
                </span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Autonomous Action</span>
                <strong className="font-mono text-xs text-amber-300">DISABLED (Advisory)</strong>
                <span className="text-[10px] text-slate-500 block">Human-in-the-loop gate</span>
              </div>
            </div>

            {/* Compact Rule Intelligence Table */}
            <div className="border-t border-slate-800/80 pt-2">
              <button
                type="button"
                onClick={() => setExpandedRuleTable((v) => !v)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-200 hover:text-cyan-300 py-1"
              >
                <span className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  Rule Intelligence &amp; Dynamic Contracts ({contracts.length} synchronized FortiSIEM rules)
                </span>
                {expandedRuleTable ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {expandedRuleTable && (
                <div className="mt-2 overflow-x-auto max-h-72 overflow-y-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-[11px] border-collapse">
                    <thead className="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-2">FortiSIEM Rule</th>
                        <th className="p-2">Archetype</th>
                        <th className="p-2">Contract</th>
                        <th className="p-2">Mandatory Evidence</th>
                        <th className="p-2">Org Context Needed</th>
                        <th className="p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/70 text-slate-300">
                      {contracts.map((c) => {
                        const isSelected = selectedRuleId && (c.fortisiem_rule_id === selectedRuleId || c.rule_db_id === selectedRuleId);
                        return (
                          <tr key={c.rule_db_id} className={isSelected ? "bg-cyan-950/30" : "hover:bg-slate-900/50"}>
                            <td className="p-2 font-medium text-slate-200 max-w-xs truncate" title={c.fortisiem_rule_id}>
                              {c.rule_name}
                              <span className="block text-[10px] font-mono text-slate-500">{c.fortisiem_rule_id}</span>
                            </td>
                            <td className="p-2 font-mono">
                              <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300 text-[10px]">
                                {c.rule_archetype}
                              </span>
                            </td>
                            <td className="p-2 font-mono text-[10px]">
                              <span
                                className={`px-1.5 py-0.5 rounded border ${
                                  c.approval_state === "APPROVED"
                                    ? "bg-emerald-950/70 border-emerald-800 text-emerald-300"
                                    : "bg-amber-950/60 border-amber-800 text-amber-300"
                                }`}
                              >
                                {c.approval_state} v{c.contract_version}
                              </span>
                            </td>
                            <td className="p-2 font-mono text-[10px] text-slate-400 max-w-[180px] truncate">
                              {(c.mandatory_evidence_fields || []).slice(0, 3).join(", ") || "None"}
                            </td>
                            <td className="p-2 font-mono text-[10px] text-slate-400 max-w-[180px] truncate">
                              {(c.approved_organizational_context_types || []).slice(0, 2).join(", ") || "None"}
                            </td>
                            <td className="p-2">
                              <button
                                type="button"
                                onClick={() => handleOpenContract(c.fortisiem_rule_id)}
                                className="px-2 py-0.5 rounded border border-cyan-800 bg-cyan-950/60 hover:bg-cyan-900 text-cyan-200 text-[10px] font-semibold"
                              >
                                Inspect Contract
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {variant === "accuracy" && (
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/80 space-y-3" data-testid="ais32-accuracy-evaluation">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-slate-100">
                AIS 3.2 Paired Evaluation — Mode A (Baseline) vs Mode B (Rule-Aware)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/70 border border-amber-800 text-amber-300">
                Development Evaluation (Not GT-3 Certified)
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={runKeyInput}
                onChange={(e) => setRunKeyInput(e.target.value)}
                placeholder="Run Key (e.g. AIS32-MODE_B-...)"
                className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 w-52"
              />
              <button
                type="button"
                onClick={handleEvaluateRunKey}
                className="px-2.5 py-1 rounded bg-cyan-700 hover:bg-cyan-600 text-white text-xs font-semibold"
              >
                Load Run
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {[
              { label: "Mode A — Neutral Baseline", data: evalModeA },
              { label: "Mode B — Universal Rule-Aware Engine", data: evalModeB },
            ].map((slot) => {
              const rawM = slot.data?.raw_llm_metrics;
              const valM = slot.data?.validated_app_metrics;
              const effM = slot.data?.effective_operational_metrics;
              return (
                <div key={slot.label} className="p-3 rounded-lg border border-slate-800 bg-slate-900/70 space-y-2">
                  <div className="flex items-center justify-between">
                    <strong className="text-slate-200">{slot.label}</strong>
                    <span className="text-[10px] font-mono text-slate-400">
                      {slot.data ? slot.data.run_key : "No run loaded"}
                    </span>
                  </div>
                  {slot.data ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-[11px] font-mono text-left">
                        <thead>
                          <tr className="text-slate-400 border-b border-slate-800">
                            <th className="py-1">Layer</th>
                            <th className="py-1">Cov%</th>
                            <th className="py-1">Conc Acc%</th>
                            <th className="py-1">E2E%</th>
                            <th className="py-1">TP / FP Rec%</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 text-slate-200">
                          {[
                            { name: "Raw LLM", m: rawM },
                            { name: "Validated App", m: valM },
                            { name: "Effective Op", m: effM },
                          ].map((row) => (
                            <tr key={row.name}>
                              <td className="py-1 font-sans">{row.name}</td>
                              <td className="py-1">{row.m?.decision_coverage_pct ?? "N/A"}</td>
                              <td className="py-1">{row.m?.conclusive_accuracy_pct ?? "N/A"}</td>
                              <td className="py-1">{row.m?.end_to_end_correct_binary_rate_pct ?? "N/A"}</td>
                              <td className="py-1">
                                {row.m?.tp_recall_all_tps_pct ?? "N/A"} / {row.m?.fp_recall_all_fps_pct ?? "N/A"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500">
                      Execute or enter an AIS 3.2 development run key to inspect separated Raw, Validated, and Effective metrics.
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          {ais33Plan && (
            <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/50 text-[11px] text-slate-300 flex flex-wrap items-center justify-between gap-2">
              <div>
                <strong className="text-cyan-300">AIS 3.3 Fresh Holdout Target:</strong> Min N={ais33Plan.recommended_minimum_total} untouched incidents (min {ais33Plan.recommended_min_tp_incidents} TPs), dual-reviewer GT-3 certified, strict SHA-256 &amp; ID isolation.
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 border border-slate-700 text-amber-300">
                {ais33Plan.status}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Dynamic Rule Contract Inspector Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex justify-end">
          <div className="w-full max-w-xl bg-slate-950 border-l border-slate-800 h-full overflow-y-auto p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-cyan-400" />
                  Dynamic Rule Contract Inspector
                </h3>
                <p className="text-[11px] font-mono text-slate-400">
                  {drawerDetail?.contract_id || "Loading..."}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {drawerLoading || !drawerDetail ? (
              <div className="text-xs text-slate-400 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" /> Loading contract specification...
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                  <div className="font-semibold text-slate-100">{drawerDetail.rule_name}</div>
                  <div className="font-mono text-[11px] text-cyan-300">
                    {drawerDetail.rule_archetype} {drawerDetail.secondary_archetype ? `(+ ${drawerDetail.secondary_archetype})` : ""} • Vendor: {drawerDetail.source_vendor}
                  </div>
                  <div className="font-mono text-[10px] text-slate-400">
                    Version {drawerDetail.contract_version} • Approval: {drawerDetail.approval_state} • SHA: {String(drawerDetail.contract_hash || "").slice(0, 16)}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800">
                  <div className="font-semibold text-slate-300 mb-1">Detection Objective</div>
                  <p className="text-slate-300 leading-relaxed">{drawerDetail.detection_objective}</p>
                </div>

                <div className="grid grid-cols-1 gap-2">
                  <div className="p-2.5 rounded-lg bg-rose-950/20 border border-rose-900/50">
                    <div className="font-semibold text-rose-300 mb-1">TRUE_POSITIVE Criteria</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                      {(drawerDetail.tp_criteria || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                  <div className="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-900/50">
                    <div className="font-semibold text-emerald-300 mb-1">FALSE_POSITIVE Criteria</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                      {(drawerDetail.fp_criteria || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                  <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/50">
                    <div className="font-semibold text-amber-300 mb-1">Authorization &amp; Limitation Guardrails</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                      {(drawerDetail.authorization_requirements || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                </div>

                {isAdmin && !isViewer && drawerDetail.approval_state !== "APPROVED" && (
                  <button
                    type="button"
                    disabled={approvingContract}
                    onClick={() => handleApproveContract(drawerDetail.fortisiem_rule_id)}
                    className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold flex items-center justify-center gap-1.5"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    {approvingContract ? "Approving Contract..." : "Approve Contract Version (Admin)"}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tenant-Scoped Organizational Context Manager Modal */}
      {orgModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <Database className="w-4 h-4 text-indigo-400" />
                  Verified Organizational Context Registry (Tenant-Isolated)
                </h3>
                <p className="text-[11px] text-slate-400">
                  Only Administrator-approved, non-expired records enter prompts. Internal IP != authorized; absent context = UNKNOWN.
                </p>
              </div>
              <button type="button" onClick={() => setOrgModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {!isViewer && (
              <form onSubmit={handleCreateOrgContext} className="grid grid-cols-1 sm:grid-cols-5 gap-2 p-3 rounded-lg bg-slate-900/70 border border-slate-800 text-xs">
                <input
                  type="text"
                  value={newCustomer}
                  onChange={(e) => setNewCustomer(e.target.value)}
                  placeholder="Tenant / Customer"
                  className="px-2 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
                />
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="px-2 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
                >
                  {(orgTypes.length > 0 ? orgTypes : ["AUTHORIZED_SCANNER"]).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="Context Value (e.g. Qualys)"
                  className="px-2 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
                />
                <input
                  type="text"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  placeholder="IP/CIDR/Domain/Host Pattern"
                  className="px-2 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
                />
                <button
                  type="submit"
                  disabled={savingOrg}
                  className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center justify-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </form>
            )}

            <div className="overflow-x-auto rounded-lg border border-slate-800">
              <table className="w-full text-left text-[11px] border-collapse">
                <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-2">Tenant</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Value / Pattern</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Admin Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70 text-slate-300">
                  {orgItems.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-4 text-center text-slate-500">
                        No organizational context records registered (missing context defaults to UNKNOWN).
                      </td>
                    </tr>
                  ) : (
                    orgItems.map((item) => (
                      <tr key={item.id}>
                        <td className="p-2 font-mono">{item.customer}</td>
                        <td className="p-2 font-mono text-cyan-300">{item.context_type}</td>
                        <td className="p-2">
                          <span className="font-semibold">{item.context_value}</span>
                          <span className="block font-mono text-[10px] text-slate-500">{item.match_pattern}</span>
                        </td>
                        <td className="p-2 font-mono">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                            item.approval_status === "APPROVED" ? "bg-emerald-950 text-emerald-300" : "bg-amber-950 text-amber-300"
                          }`}>
                            {item.approval_status}
                          </span>
                        </td>
                        <td className="p-2 flex items-center gap-1.5">
                          {isAdmin && item.approval_status !== "APPROVED" && (
                            <button
                              type="button"
                              onClick={() => handleDecideOrg(item.id, "APPROVE")}
                              className="px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-[10px]"
                            >
                              Approve
                            </button>
                          )}
                          {isAdmin && item.approval_status === "APPROVED" && (
                            <button
                              type="button"
                              onClick={() => handleDecideOrg(item.id, "REVOKE")}
                              className="px-2 py-0.5 rounded bg-rose-800 hover:bg-rose-700 text-white text-[10px]"
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
