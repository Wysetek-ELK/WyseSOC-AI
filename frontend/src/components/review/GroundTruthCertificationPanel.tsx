"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCopy,
  Database,
  EyeOff,
  FileCode2,
  HelpCircle,
  Lock,
  Paperclip,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Unlock,
  UserCheck,
  X,
} from "lucide-react";
import {
  CohortSummary,
  GroundTruthDetailResponse,
  GroundTruthQueueItem,
  groundTruthApi,
} from "@/lib/api";
import { useApp } from "@/context/AppContext";

function certBadgeStyle(status: string): string {
  switch (status) {
    case "GT3_CERTIFIED":
      return "bg-emerald-950/80 text-emerald-300 border-emerald-700/70";
    case "CERTIFIED_INCONCLUSIVE":
      return "bg-slate-800 text-slate-300 border-slate-600";
    case "CONFLICT_PENDING_ADJUDICATION":
      return "bg-rose-950/80 text-rose-300 border-rose-700/70";
    case "GT2_SINGLE_REVIEW":
    case "PENDING_SECOND_REVIEW":
      return "bg-sky-950/80 text-sky-300 border-sky-700/70";
    case "IN_PROGRESS":
      return "bg-indigo-950/80 text-indigo-300 border-indigo-700/70";
    case "GT1_HISTORICAL_ONLY":
      return "bg-amber-950/70 text-amber-300 border-amber-700/70";
    default:
      return "bg-zinc-900 text-zinc-300 border-zinc-700";
  }
}

export function GroundTruthCertificationPanel() {
  const { user } = useApp();
  const roleStr = String(user?.role || "");
  const canMutate = roleStr === "Administrator" || roleStr === "SOC Analyst" || roleStr === "SuperAdmin";
  const isAdmin = roleStr === "Administrator" || roleStr === "SuperAdmin";

  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [selectedCohortKey, setSelectedCohortKey] = useState("AIS_2_6E_FROZEN_20");
  const [activeCohort, setActiveCohort] = useState<CohortSummary | null>(null);
  const [items, setItems] = useState<GroundTruthQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [tierFilter, setTierFilter] = useState<"ALL" | "PRIORITY" | "REMAINING">("ALL");
  const [statusFilter, setStatusFilter] = useState("");
  const [vendorFilter, setVendorFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const [exposureOnly, setExposureOnly] = useState(false);
  const [myPendingOnly, setMyPendingOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [showHelpGuide, setShowHelpGuide] = useState(false);

  // Detail Drawer state
  const [detail, setDetail] = useState<GroundTruthDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [logSearch, setLogSearch] = useState("");
  const [showRuleJson, setShowRuleJson] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Additional evidence form
  const [evType, setEvType] = useState("HOST_TELEMETRY");
  const [evRef, setEvRef] = useState("");
  const [evContent, setEvContent] = useState("");
  const [evRationale, setEvRationale] = useState("");
  const [attachingEv, setAttachingEv] = useState(false);

  // Certification review form state
  const [humanVerdict, setHumanVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "INCONCLUSIVE">("TRUE_POSITIVE");
  const [detectionCorrectness, setDetectionCorrectness] = useState<"MATCHED" | "NOT_MATCHED" | "UNKNOWN">("MATCHED");
  const [authContext, setAuthContext] = useState<"AUTHORIZED" | "UNAUTHORIZED" | "UNKNOWN" | "NOT_APPLICABLE">("UNKNOWN");
  const [confidenceLevel, setConfidenceLevel] = useState<"LOW" | "MEDIUM" | "HIGH">("HIGH");
  const [evidenceSufficiency, setEvidenceSufficiency] = useState<"SUFFICIENT" | "PARTIAL" | "INSUFFICIENT">("SUFFICIENT");
  const [rationale, setRationale] = useState("");
  const [evidenceRefsText, setEvidenceRefsText] = useState("");
  const [attReviewed, setAttReviewed] = useState(false);
  const [attNoAi, setAttNoAi] = useState(false);
  const [attIndependent, setAttIndependent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [unlockPromptOpen, setUnlockPromptOpen] = useState(false);
  const [unlockReason, setUnlockReason] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [drawerNotice, setDrawerNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Conflict Adjudication modal state
  const [adjVerdict, setAdjVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "INCONCLUSIVE">("TRUE_POSITIVE");
  const [adjRationale, setAdjRationale] = useState("");
  const [adjudicating, setAdjudicating] = useState(false);

  // Post-certification comparison reveal (only available once GT3_CERTIFIED)
  const [postCertComp, setPostCertComp] = useState<Record<string, any> | null>(null);

  const loadQueue = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const cohortList = await groundTruthApi.listCohorts();
      setCohorts(cohortList);
      const qRes = await groundTruthApi.getCohortQueue(selectedCohortKey, {
        priority_only: tierFilter === "PRIORITY" ? true : tierFilter === "REMAINING" ? false : undefined,
        certification_status: statusFilter || undefined,
        vendor: vendorFilter || undefined,
        customer: customerFilter || undefined,
        exposure_risk_only: exposureOnly ? true : undefined,
        my_pending_only: myPendingOnly ? true : undefined,
        search: search || undefined,
      });
      setActiveCohort(qRes.cohort);
      setItems(qRes.items);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load Ground Truth certification cohort.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [selectedCohortKey, tierFilter, statusFilter, vendorFilter, customerFilter, exposureOnly, myPendingOnly]);

  const openCertificationDrawer = async (fortisiemId: string) => {
    setLoadingDetail(true);
    setDrawerNotice(null);
    setPostCertComp(null);
    setUnlockPromptOpen(false);
    setUnlockReason("");
    setLogSearch("");
    try {
      const d = await groundTruthApi.getIncidentDetail(selectedCohortKey, fortisiemId);
      setDetail(d);
      if (d.my_review) {
        setHumanVerdict((d.my_review.analyst_verdict as any) || "TRUE_POSITIVE");
        setDetectionCorrectness((d.my_review.detection_correctness as any) || "MATCHED");
        setAuthContext((d.my_review.authorization_context as any) || "UNKNOWN");
        setConfidenceLevel((d.my_review.confidence_level as any) || "HIGH");
        setEvidenceSufficiency((d.my_review.evidence_sufficiency_status as any) || "SUFFICIENT");
        setRationale(d.my_review.analyst_notes || "");
        setEvidenceRefsText((d.my_review.evidence_references || []).join("\n"));
        setAttReviewed(Boolean(d.my_review.attestation_flags?.evidence_reviewed));
        setAttNoAi(Boolean(d.my_review.attestation_flags?.no_ai_or_historical_influence));
        setAttIndependent(Boolean(d.my_review.attestation_flags?.independent_judgment));
      } else {
        setHumanVerdict("TRUE_POSITIVE");
        setDetectionCorrectness("MATCHED");
        setAuthContext("UNKNOWN");
        setConfidenceLevel("HIGH");
        setEvidenceSufficiency("SUFFICIENT");
        setRationale("");
        setEvidenceRefsText("");
        setAttReviewed(false);
        setAttNoAi(false);
        setAttIndependent(false);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Unable to open certification investigation.");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleAttachEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || !evContent.trim()) return;
    setAttachingEv(true);
    setDrawerNotice(null);
    try {
      await groundTruthApi.attachEvidence(selectedCohortKey, detail.cohort_item.fortisiem_incident_id, {
        evidence_type: evType,
        reference_key: evRef,
        evidence_content: evContent,
        analyst_rationale: evRationale,
      });
      setEvRef("");
      setEvContent("");
      setEvRationale("");
      const refreshed = await groundTruthApi.getIncidentDetail(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id
      );
      setDetail(refreshed);
      setDrawerNotice({ type: "success", text: "Additional factual evidence recorded on benchmark incident." });
    } catch (err: any) {
      setDrawerNotice({ type: "error", text: err.message });
    } finally {
      setAttachingEv(false);
    }
  };

  const handleReviewSubmit = async (mode: "DRAFT" | "LOCK") => {
    if (!detail) return;
    setSubmitting(true);
    setDrawerNotice(null);
    try {
      const refs = evidenceRefsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const res = await groundTruthApi.submitReview(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id,
        {
          mode,
          human_verdict: humanVerdict,
          detection_correctness: detectionCorrectness,
          authorization_context: authContext,
          confidence_level: confidenceLevel,
          evidence_sufficiency_status: evidenceSufficiency,
          rationale,
          evidence_references: refs,
          attestation_flags: {
            evidence_reviewed: attReviewed,
            no_ai_or_historical_influence: attNoAi,
            independent_judgment: attIndependent,
          },
        }
      );
      const refreshed = await groundTruthApi.getIncidentDetail(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id
      );
      setDetail(refreshed);
      await loadQueue();
      setDrawerNotice({
        type: "success",
        text:
          mode === "LOCK"
            ? `Review locked cleanly (${res.certification_status}). Excluded from AI training & RAG.`
            : "Draft saved cleanly (unlocks no AI verdict, does not advance certification).",
      });
    } catch (err: any) {
      setDrawerNotice({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnlockReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    const trimmed = unlockReason.trim();
    if (trimmed.length < 5) {
      setDrawerNotice({ type: "error", text: "Please enter a brief unlock reason (at least 5 characters)." });
      return;
    }
    setUnlocking(true);
    setDrawerNotice(null);
    try {
      await groundTruthApi.unlockReview(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id,
        { reason: trimmed }
      );
      setUnlockPromptOpen(false);
      setUnlockReason("");
      setPostCertComp(null);
      const refreshed = await groundTruthApi.getIncidentDetail(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id
      );
      setDetail(refreshed);
      await loadQueue();
      setDrawerNotice({
        type: "success",
        text: "Review unlocked and reverted to draft. You can now update your verdict and re-lock.",
      });
    } catch (err: any) {
      setDrawerNotice({ type: "error", text: err.message });
    } finally {
      setUnlocking(false);
    }
  };

  const handleAdjudicate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setAdjudicating(true);
    setDrawerNotice(null);
    try {
      const res = await groundTruthApi.adjudicateConflict(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id,
        {
          final_verdict: adjVerdict,
          rationale: adjRationale,
        }
      );
      setAdjRationale("");
      const refreshed = await groundTruthApi.getIncidentDetail(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id
      );
      setDetail(refreshed);
      await loadQueue();
      setDrawerNotice({
        type: "success",
        text: `Conflict adjudicated cleanly -> ${res.certification_status} (${res.certified_verdict}).`,
      });
    } catch (err: any) {
      setDrawerNotice({ type: "error", text: err.message });
    } finally {
      setAdjudicating(false);
    }
  };

  const handleRevealPostCertComparison = async () => {
    if (!detail) return;
    try {
      const comp = await groundTruthApi.getPostCertificationComparison(
        selectedCohortKey,
        detail.cohort_item.fortisiem_incident_id
      );
      setPostCertComp(comp);
    } catch (err: any) {
      setDrawerNotice({ type: "error", text: err.message });
    }
  };

  const filteredRawLogs = useMemo(() => {
    if (!detail) return [];
    const q = logSearch.trim().toLowerCase();
    if (!q) return detail.raw_logs;
    return detail.raw_logs.filter((entry) =>
      `${entry.raw_log} ${entry.process_name || ""} ${entry.file_name || ""} ${entry.command_line || ""} ${entry.host || ""} ${entry.source_ip || ""}`
        .toLowerCase()
        .includes(q)
    );
  }, [detail, logSearch]);

  const progress = activeCohort?.progress;
  const priorityPct = progress && progress.priority_total > 0
    ? Math.round((progress.priority_certified / progress.priority_total) * 100)
    : 0;
  const fullPct = progress && progress.total > 0
    ? Math.round(((progress.gt3_certified + progress.certified_inconclusive) / progress.total) * 100)
    : 0;

  return (
    <div className="space-y-3" data-testid="ground-truth-certification-tab">
      {/* Strict Blind Isolation & Readiness Banner */}
      <div className="rounded-lg border border-cyan-900/60 bg-slate-950/90 p-2.5 flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        <div className="flex items-start gap-2.5">
          <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/70 text-cyan-300 shrink-0 mt-0.5">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-100">
                {activeCohort?.name || "AIS 2.6e Frozen Benchmark Cohort Certification"}
              </span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-amber-950/70 text-amber-300 border border-amber-800/60 flex items-center gap-1">
                <EyeOff className="w-3 h-3" /> Blind Enforced
              </span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-950/70 text-emerald-300 border border-emerald-800/60">
                Excluded from RAG &amp; Learning
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Certify the 5 Priority Pilot and 15 Remaining frozen incidents using only raw SIEM logs, triggered rule definition, and factual host/network evidence before AIS 2.7 live GPU inference.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {cohorts.length > 0 && (
            <select
              value={selectedCohortKey}
              onChange={(e) => setSelectedCohortKey(e.target.value)}
              className="px-2 py-1 text-xs font-mono rounded border border-slate-700 bg-slate-900 text-slate-200 focus:outline-none"
            >
              {cohorts.map((c) => (
                <option key={c.cohort_key} value={c.cohort_key}>
                  {c.cohort_key} ({c.progress.total})
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={() => setShowHelpGuide(!showHelpGuide)}
            className="flex items-center gap-1 px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300"
          >
            <HelpCircle className="w-3.5 h-3.5 text-cyan-400" /> Guide
          </button>
          <button
            type="button"
            onClick={loadQueue}
            className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
          >
            <RefreshCw className="w-3 h-3" /> Sync
          </button>
        </div>
      </div>

      {/* Collapsible Certification Rules Guide */}
      {showHelpGuide && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-300 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <div className="font-bold text-cyan-300 mb-1">Certification Tiers</div>
            <ul className="space-y-0.5 text-[11px] text-slate-400">
              <li><strong className="text-slate-200">GT-0 / GT-1:</strong> Unreviewed / historical FortiSIEM only (excluded from benchmark accuracy).</li>
              <li><strong className="text-sky-300">GT-2:</strong> 1 locked independent human review (exploratory only).</li>
              <li><strong className="text-emerald-300">GT-3 Certified:</strong> 2 distinct reviewers agreed or Senior Adjudicator resolved conflict.</li>
            </ul>
          </div>
          <div>
            <div className="font-bold text-amber-300 mb-1">Strict Blindness Guarantees</div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              AI verdicts, confidence scores, historical FortiSIEM labels, and sibling reviewer conclusions are withheld on the server until dual-reviewer certification locks cleanly.
            </p>
          </div>
          <div>
            <div className="font-bold text-rose-300 mb-1">Zero Contamination Rule</div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              All 20 cohort items carry <code className="text-slate-200">excluded_from_learning=true</code> so certified benchmark verdicts never enter Agent Memory, RAG precedents, or rule prompts.
            </p>
          </div>
        </div>
      )}

      {/* Dual Progress Bars & Neutral Certification Counters */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2.5">
        <div className="lg:col-span-5 p-2.5 rounded-lg border border-slate-800 bg-slate-950 space-y-2">
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="font-semibold text-amber-300 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Priority Pilot Batch
              </span>
              <span className="font-mono text-slate-200">
                {progress?.priority_certified ?? 0}/{progress?.priority_total ?? 5} GT-3 ({progress?.priority_single_reviewed ?? 0} GT-2+)
              </span>
            </div>
            <div className="h-2 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
              <div
                className="h-full bg-amber-500 transition-all"
                style={{ width: `${priorityPct}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="font-semibold text-cyan-300 flex items-center gap-1">
                <Award className="w-3 h-3" /> Full Frozen Benchmark Cohort
              </span>
              <span className="font-mono text-slate-200">
                {(progress?.gt3_certified ?? 0) + (progress?.certified_inconclusive ?? 0)}/{progress?.total ?? 20} Certified ({fullPct}%)
              </span>
            </div>
            <div className="h-2 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all"
                style={{ width: `${fullPct}%` }}
              />
            </div>
          </div>
        </div>

        <div className="lg:col-span-7 grid grid-cols-3 sm:grid-cols-6 gap-2">
          <div className="p-2 rounded-lg border border-slate-800 bg-slate-950">
            <div className="text-[10px] text-slate-400">GT-0 / GT-1</div>
            <div className="text-lg font-bold font-mono text-slate-100">
              {(progress?.gt0_unreviewed ?? 0) + (progress?.gt1_historical_only ?? 0)}
            </div>
          </div>
          <div className="p-2 rounded-lg border border-sky-900/40 bg-sky-950/20">
            <div className="text-[10px] text-sky-400">GT-2 Single</div>
            <div className="text-lg font-bold font-mono text-sky-300">
              {progress?.gt2_single_review ?? 0}
            </div>
          </div>
          <div className="p-2 rounded-lg border border-emerald-900/40 bg-emerald-950/20">
            <div className="text-[10px] text-emerald-400">GT-3 Certified</div>
            <div className="text-lg font-bold font-mono text-emerald-300">
              {progress?.gt3_certified ?? 0}
            </div>
          </div>
          <div className="p-2 rounded-lg border border-rose-900/40 bg-rose-950/20">
            <div className="text-[10px] text-rose-400">Conflicts</div>
            <div className="text-lg font-bold font-mono text-rose-300">
              {progress?.conflict_pending_adjudication ?? 0}
            </div>
          </div>
          <div className="p-2 rounded-lg border border-amber-900/40 bg-amber-950/20">
            <div className="text-[10px] text-amber-400">Exposure Risk</div>
            <div className="text-lg font-bold font-mono text-amber-300">
              {progress?.exposure_risk_count ?? 0}
            </div>
          </div>
          <div className="p-2 rounded-lg border border-indigo-900/40 bg-indigo-950/20">
            <div className="text-[10px] text-indigo-300">My Locked</div>
            <div className="text-lg font-bold font-mono text-indigo-200">
              {progress?.my_locked_reviews ?? 0}/{progress?.total ?? 20}
            </div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-2 rounded-lg border border-slate-800 bg-slate-950 flex flex-col md:flex-row gap-2 items-stretch md:items-center justify-between">
        <div className="flex flex-wrap items-center gap-1.5">
          {(["ALL", "PRIORITY", "REMAINING"] as const).map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => setTierFilter(tier)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                tierFilter === tier
                  ? "bg-cyan-950 text-cyan-200 border-cyan-700"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
              }`}
            >
              {tier === "ALL" ? "All 20 Cohort" : tier === "PRIORITY" ? "Priority 5 Pilot" : "Remaining 15"}
            </button>
          ))}
          <select
            value={vendorFilter}
            onChange={(e) => setVendorFilter(e.target.value)}
            className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-900 text-slate-300"
          >
            <option value="">All Vendors</option>
            <option value="CrowdStrike">CrowdStrike (10)</option>
            <option value="Prisma SASE">Prisma SASE (10)</option>
          </select>
          <select
            value={customerFilter}
            onChange={(e) => setCustomerFilter(e.target.value)}
            className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-900 text-slate-300"
          >
            <option value="">All Customers</option>
            <option value="Tosoh">Tosoh</option>
            <option value="WSTPL">WSTPL</option>
            <option value="Forbes_Marshall">Forbes_Marshall</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-900 text-slate-300"
          >
            <option value="">All Cert States</option>
            <option value="GT0_UNREVIEWED">GT-0 Unreviewed</option>
            <option value="GT1_HISTORICAL_ONLY">GT-1 Historical Only</option>
            <option value="IN_PROGRESS">Draft / In Progress</option>
            <option value="GT2_SINGLE_REVIEW">GT-2 Single Review</option>
            <option value="CONFLICT_PENDING_ADJUDICATION">Conflict Pending</option>
            <option value="GT3_CERTIFIED">GT-3 Certified</option>
            <option value="CERTIFIED_INCONCLUSIVE">Certified Inconclusive</option>
          </select>
          <label className="flex items-center gap-1 px-2 py-1 text-[11px] text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={myPendingOnly}
              onChange={(e) => setMyPendingOnly(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900"
            />
            My Pending
          </label>
          <label className="flex items-center gap-1 px-2 py-1 text-[11px] text-amber-300 cursor-pointer">
            <input
              type="checkbox"
              checked={exposureOnly}
              onChange={(e) => setExposureOnly(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900"
            />
            Exposure Risk
          </label>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            loadQueue();
          }}
          className="flex gap-1.5"
        >
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2 top-2 text-slate-500" />
            <input
              type="text"
              placeholder="ID, host, entity..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-7 pr-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-900 text-slate-200 w-44 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-2.5 py-1 rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200"
          >
            Go
          </button>
        </form>
      </div>

      {errorMsg && (
        <div className="p-2.5 rounded border border-rose-800 bg-rose-950/50 text-xs text-rose-200">
          {errorMsg}
        </div>
      )}

      {/* Frozen Cohort Certification Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden shadow-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-semibold text-[11px]">
                <th className="py-2 px-2.5">#</th>
                <th className="py-2 px-2.5">FortiSIEM ID / Internal ID</th>
                <th className="py-2 px-2.5">Customer &amp; Rule</th>
                <th className="py-2 px-2.5">Entity / Target</th>
                <th className="py-2 px-2.5">Blind &amp; Exposure</th>
                <th className="py-2 px-2.5">Certification Status</th>
                <th className="py-2 px-2.5">My Review</th>
                <th className="py-2 px-2.5 text-right sticky right-0 bg-slate-900/95">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Loading frozen Ground Truth Certification cohort...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No cohort incidents match the current filters.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.cohort_item_id}
                    className="hover:bg-slate-900/50 transition-colors group"
                    data-testid={`gt-row-${item.fortisiem_incident_id}`}
                  >
                    <td className="py-1.5 px-2.5 font-mono text-[11px] text-slate-400">
                      {item.is_priority ? (
                        <span className="px-1.5 py-0.2 rounded bg-amber-950/70 text-amber-300 border border-amber-800/60 font-bold text-[10px]">
                          P{item.priority_rank}
                        </span>
                      ) : (
                        <span>#{item.priority_rank}</span>
                      )}
                    </td>
                    <td className="py-1.5 px-2.5">
                      <div className="font-mono font-bold text-cyan-400">{item.fortisiem_incident_id}</div>
                      <div className="text-[10px] font-mono text-slate-500 truncate max-w-[140px]">
                        {item.incident_db_id || "pending-uuid"}
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5">
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                          {item.vendor}
                        </span>
                        <span className="text-slate-200 font-medium">{item.customer}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 truncate max-w-[220px]">{item.rule_name}</div>
                    </td>
                    <td className="py-1.5 px-2.5 font-mono text-[11px]">
                      <div className="text-slate-200 truncate max-w-[180px]">{item.observed_entity || "—"}</div>
                      <div className="text-[10px] text-slate-500">{item.target_host || "—"}</div>
                    </td>
                    <td className="py-1.5 px-2.5">
                      <div className="flex flex-col gap-0.5">
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-300">
                          <EyeOff className="w-3 h-3" /> {item.blind_status}
                        </span>
                        {item.exposure_risk_flag && (
                          <span
                            title={item.exposure_risk_reason}
                            className="inline-flex items-center gap-1 text-[10px] text-amber-400/90"
                          >
                            <AlertTriangle className="w-3 h-3 shrink-0" /> Historical Masked
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5">
                      <div className="flex flex-col gap-0.5">
                        <span
                          className={`inline-flex items-center w-fit px-1.5 py-0.2 rounded text-[10px] font-mono border ${certBadgeStyle(
                            item.certification_status
                          )}`}
                        >
                          {item.certification_status}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Reviewers locked: {item.locked_reviewers_count}/2
                          {item.certified_verdict ? ` • Final: ${item.certified_verdict}` : ""}
                        </span>
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5 font-mono text-[11px]">
                      {item.my_review_status === "LOCKED" ? (
                        <span className="text-emerald-300 flex items-center gap-1">
                          <Lock className="w-3 h-3" /> LOCKED ({item.my_review_verdict})
                        </span>
                      ) : item.my_review_status === "DRAFT" ? (
                        <span className="text-amber-300">DRAFT ({item.my_review_verdict})</span>
                      ) : (
                        <span className="text-slate-500">Not Reviewed</span>
                      )}
                    </td>
                    <td className="py-1.5 px-2.5 text-right sticky right-0 bg-slate-950/95 group-hover:bg-slate-900/95">
                      <button
                        type="button"
                        onClick={() => openCertificationDrawer(item.fortisiem_incident_id)}
                        className="px-2.5 py-1 rounded bg-cyan-950/70 hover:bg-cyan-900/80 text-cyan-200 border border-cyan-700/70 text-xs font-medium"
                      >
                        {item.my_review_status === "LOCKED" ? "Inspect" : "Certify"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ground Truth Investigation & Independent Certification Drawer */}
      {(detail || loadingDetail) && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-end"
          data-testid="gt-certification-drawer"
        >
          <div className="w-full max-w-4xl bg-slate-950 border-l border-slate-800 h-full overflow-y-auto p-5 space-y-4">
            {loadingDetail && !detail ? (
              <div className="py-20 text-center text-sm text-slate-400">
                Loading isolated telemetry and rule specification...
              </div>
            ) : detail && (
              <>
                {/* Drawer Header */}
                <div className="flex items-start justify-between border-b border-slate-800 pb-3 sticky top-0 bg-slate-950/95 z-10 pt-1">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-bold text-cyan-400">
                        FortiSIEM #{detail.cohort_item.fortisiem_incident_id}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${certBadgeStyle(detail.cohort_item.certification_status)}`}>
                        {detail.cohort_item.certification_status}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950/70 text-amber-300 border border-amber-800/60 flex items-center gap-1">
                        <EyeOff className="w-3 h-3" /> Blind Enforced
                      </span>
                    </div>
                    <h2 className="text-sm font-bold text-slate-100 mt-1">
                      {detail.incident_overview.title || detail.rule_definition.rule_name}
                    </h2>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Customer: {detail.incident_overview.customer} • Vendor: {detail.cohort_item.vendor} • Target: {detail.incident_overview.target_host || "N/A"} • Internal UUID: {detail.incident_overview.incident_db_id}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDetail(null)}
                    className="p-1.5 rounded border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Strict Blind Guarantees Notice */}
                <div className="p-2.5 rounded-lg border border-amber-900/60 bg-amber-950/20 text-[11px] text-amber-200 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>
                      <strong>Independent Evidence Environment:</strong> Only raw SIEM logs, triggered FortiSIEM rule definition, and normalized telemetry are loaded. AI verdicts &amp; historical FortiSIEM resolutions are strictly sealed on the backend.
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400 shrink-0">
                    Reviewers: {detail.locked_reviewers_count}/2
                  </span>
                </div>

                {drawerNotice && (
                  <div
                    className={`p-2.5 rounded border text-xs flex items-center gap-2 ${
                      drawerNotice.type === "success"
                        ? "border-emerald-800 bg-emerald-950/40 text-emerald-200"
                        : "border-rose-800 bg-rose-950/40 text-rose-200"
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{drawerNotice.text}</span>
                  </div>
                )}

                {/* 1. Triggered FortiSIEM Rule Definition */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                      <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
                      Triggered FortiSIEM Rule Definition
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowRuleJson(!showRuleJson)}
                      className="text-[11px] text-cyan-400 hover:underline flex items-center gap-0.5"
                    >
                      {showRuleJson ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      Raw Rule Spec
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Rule Event Type</span>
                      <span className="font-mono text-slate-200 break-all">{detail.rule_definition.rule_id}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Severity / Vendor</span>
                      <span className="font-mono text-slate-200">
                        {detail.rule_definition.severity} / {detail.rule_definition.category}
                      </span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Rule SHA-256 Digest</span>
                      <span className="font-mono text-slate-300 truncate block">
                        {detail.rule_definition.rule_definition_sha256 || "N/A"}
                      </span>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-300 p-2 rounded bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block text-[10px] mb-0.5">Detection Logic / Description</span>
                    {detail.rule_definition.condition_summary || detail.rule_definition.description}
                  </div>
                  {showRuleJson && (
                    <pre className="p-2.5 rounded bg-black/70 border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto max-h-48">
                      {JSON.stringify(detail.rule_definition.raw_rule_spec, null, 2)}
                    </pre>
                  )}
                </div>

                {/* 2. Original Raw Logs (Searchable & Copyable) */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <h3 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5 text-emerald-400" />
                      Original Raw Security Logs ({filteredRawLogs.length}/{detail.raw_logs.length})
                    </h3>
                    <input
                      type="text"
                      placeholder="Filter raw logs (command, file, host, IP)..."
                      value={logSearch}
                      onChange={(e) => setLogSearch(e.target.value)}
                      className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-950 text-slate-200 sm:w-64 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {filteredRawLogs.length === 0 ? (
                      <div className="text-xs text-slate-500 py-4 text-center">No matching raw log records.</div>
                    ) : (
                      filteredRawLogs.map((log) => (
                        <div key={log.index} className="p-2.5 rounded border border-slate-800 bg-slate-950 space-y-1.5">
                          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
                            <span>
                              Event #{log.index} {log.event_id ? `• ${log.event_id}` : ""} {log.timestamp ? `• ${log.timestamp}` : ""}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard?.writeText(log.raw_log);
                                setCopiedId(`log-${log.index}`);
                                setTimeout(() => setCopiedId(null), 1500);
                              }}
                              className="flex items-center gap-1 text-cyan-400 hover:underline"
                            >
                              <ClipboardCopy className="w-3 h-3" />
                              {copiedId === `log-${log.index}` ? "Copied" : "Copy"}
                            </button>
                          </div>
                          <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                            {log.host && <span className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-300">Host: {log.host}</span>}
                            {log.source_ip && <span className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-300">SrcIP: {log.source_ip}</span>}
                            {log.process_name && <span className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-cyan-300">Proc: {log.process_name}</span>}
                            {log.file_name && <span className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-amber-300">File: {log.file_name}</span>}
                          </div>
                          {log.command_line && (
                            <div className="text-[11px] font-mono text-cyan-200 bg-slate-900/70 p-1.5 rounded border border-slate-800 break-all">
                              CMD: {log.command_line}
                            </div>
                          )}
                          <pre className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap break-all bg-black/50 p-2 rounded border border-slate-900">
                            {log.raw_log}
                          </pre>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* 3. Normalized Factual Evidence & Hash Anchors */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-100">
                      Normalized Canonical Evidence ({detail.normalized_evidence.length} facts)
                    </h3>
                    <span className="text-[10px] font-mono text-slate-500">
                      Canonical SHA: {detail.canonical_evidence_sha256 ? `${detail.canonical_evidence_sha256.slice(0, 12)}...` : "N/A"}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-48 overflow-y-auto">
                    {detail.normalized_evidence.map((ev, i) => (
                      <div key={i} className="p-2 rounded border border-slate-800 bg-slate-950 text-[11px] font-mono">
                        <div className="text-cyan-400 text-[10px]">{ev.field_name || ev.evidence_type || "FACT"}</div>
                        <div className="text-slate-200 break-all">{String(ev.value ?? ev.summary ?? JSON.stringify(ev))}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 4. Additional Manual Investigation Evidence */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                  <h3 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                    <Paperclip className="w-3.5 h-3.5 text-amber-400" />
                    Additional Investigation Context ({detail.additional_evidence.length})
                  </h3>
                  {detail.additional_evidence.length > 0 && (
                    <div className="space-y-1.5">
                      {detail.additional_evidence.map((ev) => (
                        <div key={ev.id} className="p-2 rounded border border-slate-800 bg-slate-950 text-xs">
                          <div className="flex justify-between text-[10px] font-mono text-slate-400">
                            <span className="text-amber-300">{ev.evidence_type} • {ev.reference_key || "Ref"}</span>
                            <span>{ev.created_at}</span>
                          </div>
                          <div className="text-slate-200 mt-0.5">{ev.evidence_content}</div>
                          {ev.analyst_rationale && <div className="text-[11px] text-slate-400 italic mt-0.5">{ev.analyst_rationale}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                  {canMutate && (
                    <form onSubmit={handleAttachEvidence} className="grid grid-cols-1 sm:grid-cols-4 gap-1.5 pt-1">
                      <select
                        value={evType}
                        onChange={(e) => setEvType(e.target.value)}
                        className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      >
                        <option value="HOST_TELEMETRY">Host Context</option>
                        <option value="TICKET_CHANGE_REQ">Change / IT Ticket</option>
                        <option value="THREAT_INTEL">Threat Intel Hash/URL</option>
                        <option value="EDR_PROCESS_TREE">EDR Process Tree</option>
                      </select>
                      <input
                        type="text"
                        placeholder="Ref key (e.g. CHG-1234)"
                        value={evRef}
                        onChange={(e) => setEvRef(e.target.value)}
                        className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      />
                      <input
                        type="text"
                        placeholder="Observed verification fact..."
                        value={evContent}
                        onChange={(e) => setEvContent(e.target.value)}
                        className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 sm:col-span-2"
                      />
                      <input
                        type="text"
                        placeholder="Verification rationale (optional)..."
                        value={evRationale}
                        onChange={(e) => setEvRationale(e.target.value)}
                        className="px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 sm:col-span-3"
                      />
                      <button
                        type="submit"
                        disabled={attachingEv || !evContent.trim()}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs font-medium border border-slate-700"
                      >
                        {attachingEv ? "Saving..." : "+ Attach Context"}
                      </button>
                    </form>
                  )}
                </div>

                {/* 5. Independent Human Verdict & Certification Console */}
                <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/10 p-3.5 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-900/40 pb-2">
                    <h3 className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                      <UserCheck className="w-4 h-4 text-cyan-400" />
                      Independent Human Ground Truth Assessment
                    </h3>
                    {detail.my_review?.is_locked && (
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 text-[10px] font-mono flex items-center gap-1">
                          <Lock className="w-3 h-3" /> YOUR REVIEW LOCKED
                        </span>
                        {canMutate && detail.can_unlock_my_review && (
                          <button
                            type="button"
                            onClick={() => setUnlockPromptOpen((v) => !v)}
                            data-testid="unlock-my-review-btn"
                            className="px-2 py-0.5 rounded bg-amber-950/70 hover:bg-amber-900/80 text-amber-200 border border-amber-700/70 text-[10px] font-mono flex items-center gap-1 transition-colors"
                          >
                            <Unlock className="w-3 h-3" />
                            {unlockPromptOpen ? "Cancel Unlock" : "Unlock Review"}
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {detail.my_review?.is_locked && unlockPromptOpen && canMutate && detail.can_unlock_my_review && (
                    <form
                      onSubmit={handleUnlockReview}
                      className="p-2.5 rounded border border-amber-800/70 bg-amber-950/20 space-y-2"
                      data-testid="unlock-review-form"
                    >
                      <div className="text-[11px] text-amber-200">
                        Unlocking reverts your review back to <strong>DRAFT</strong> so you can update your verdict and re-lock. This action is recorded in the audit trail.
                      </div>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          required
                          minLength={5}
                          value={unlockReason}
                          onChange={(e) => setUnlockReason(e.target.value)}
                          placeholder="Reason for unlocking (e.g. Marked wrong verdict by mistake)..."
                          className="flex-1 px-2.5 py-1.5 text-xs rounded border border-amber-800/60 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                        />
                        <button
                          type="submit"
                          disabled={unlocking || unlockReason.trim().length < 5}
                          className="px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-40 text-xs font-bold text-white flex items-center justify-center gap-1.5 shrink-0"
                        >
                          <Unlock className="w-3.5 h-3.5" />
                          {unlocking ? "Unlocking..." : "Confirm Unlock"}
                        </button>
                      </div>
                    </form>
                  )}

                  {detail.my_review?.is_locked && !detail.can_unlock_my_review && detail.unlock_blocked_reason && (
                    <div className="p-2 rounded bg-slate-900 border border-slate-700 text-[11px] text-slate-300">
                      {detail.unlock_blocked_reason}
                    </div>
                  )}

                  {detail.lock_blocked_reason && (
                    <div className="p-2 rounded bg-slate-900 border border-slate-700 text-[11px] text-amber-300">
                      {detail.lock_blocked_reason}
                    </div>
                  )}

                  {/* Verdict Classification Buttons */}
                  <div>
                    <label className="text-[11px] font-semibold text-slate-300 block mb-1.5">
                      1. Independent Human Verdict
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        disabled={!detail.can_submit_lock || !canMutate}
                        onClick={() => setHumanVerdict("TRUE_POSITIVE")}
                        className={`py-2 px-2 rounded border text-xs font-bold flex items-center justify-center gap-1.5 ${
                          humanVerdict === "TRUE_POSITIVE"
                            ? "bg-rose-950 text-rose-200 border-rose-600"
                            : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800"
                        } disabled:opacity-50`}
                      >
                        <ShieldAlert className="w-3.5 h-3.5" /> TRUE_POSITIVE
                      </button>
                      <button
                        type="button"
                        disabled={!detail.can_submit_lock || !canMutate}
                        onClick={() => setHumanVerdict("FALSE_POSITIVE")}
                        className={`py-2 px-2 rounded border text-xs font-bold flex items-center justify-center gap-1.5 ${
                          humanVerdict === "FALSE_POSITIVE"
                            ? "bg-emerald-950 text-emerald-200 border-emerald-600"
                            : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800"
                        } disabled:opacity-50`}
                      >
                        <ShieldCheck className="w-3.5 h-3.5" /> FALSE_POSITIVE
                      </button>
                      <button
                        type="button"
                        disabled={!detail.can_submit_lock || !canMutate}
                        onClick={() => setHumanVerdict("INCONCLUSIVE")}
                        className={`py-2 px-2 rounded border text-xs font-bold flex items-center justify-center gap-1.5 ${
                          humanVerdict === "INCONCLUSIVE"
                            ? "bg-amber-950 text-amber-200 border-amber-600"
                            : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800"
                        } disabled:opacity-50`}
                      >
                        <AlertTriangle className="w-3.5 h-3.5" /> INCONCLUSIVE
                      </button>
                    </div>
                  </div>

                  {/* Structured Context Classifications */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">Detection Matched Rule?</label>
                      <select
                        disabled={!detail.can_submit_lock || !canMutate}
                        value={detectionCorrectness}
                        onChange={(e) => setDetectionCorrectness(e.target.value as any)}
                        className="w-full px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      >
                        <option value="MATCHED">MATCHED</option>
                        <option value="NOT_MATCHED">NOT_MATCHED</option>
                        <option value="UNKNOWN">UNKNOWN</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">Authorization Context</label>
                      <select
                        disabled={!detail.can_submit_lock || !canMutate}
                        value={authContext}
                        onChange={(e) => setAuthContext(e.target.value as any)}
                        className="w-full px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      >
                        <option value="AUTHORIZED">AUTHORIZED (Approved)</option>
                        <option value="UNAUTHORIZED">UNAUTHORIZED</option>
                        <option value="UNKNOWN">UNKNOWN</option>
                        <option value="NOT_APPLICABLE">NOT_APPLICABLE</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">Reviewer Confidence</label>
                      <select
                        disabled={!detail.can_submit_lock || !canMutate}
                        value={confidenceLevel}
                        onChange={(e) => setConfidenceLevel(e.target.value as any)}
                        className="w-full px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      >
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">Evidence Sufficiency</label>
                      <select
                        disabled={!detail.can_submit_lock || !canMutate}
                        value={evidenceSufficiency}
                        onChange={(e) => setEvidenceSufficiency(e.target.value as any)}
                        className="w-full px-2 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                      >
                        <option value="SUFFICIENT">SUFFICIENT</option>
                        <option value="PARTIAL">PARTIAL</option>
                        <option value="INSUFFICIENT">INSUFFICIENT</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                      Evidence-Grounded Rationale (min 15 chars required to lock)
                    </label>
                    <textarea
                      rows={3}
                      disabled={!detail.can_submit_lock || !canMutate}
                      value={rationale}
                      onChange={(e) => setRationale(e.target.value)}
                      placeholder="Cite exact event IDs, command lines, hosts, filenames, and authorization evidence justifying your classification..."
                      className="w-full p-2 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                      Supporting Evidence References (one reference per line)
                    </label>
                    <textarea
                      rows={2}
                      disabled={!detail.can_submit_lock || !canMutate}
                      value={evidenceRefsText}
                      onChange={(e) => setEvidenceRefsText(e.target.value)}
                      placeholder="event_id: 123456&#10;process: UltraViewer_Service.exe"
                      className="w-full p-2 text-xs font-mono rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500"
                    />
                  </div>

                  {/* Three Mandatory Blind Attestations */}
                  <div className="p-2.5 rounded border border-slate-800 bg-slate-950/90 space-y-1.5 text-xs">
                    <div className="font-semibold text-slate-200 text-[11px]">Mandatory Independence Attestations</div>
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        disabled={!detail.can_submit_lock || !canMutate}
                        checked={attReviewed}
                        onChange={(e) => setAttReviewed(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900"
                      />
                      <span>I reviewed the raw security logs, triggered rule definition, and normalized evidence for this incident.</span>
                    </label>
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        disabled={!detail.can_submit_lock || !canMutate}
                        checked={attNoAi}
                        onChange={(e) => setAttNoAi(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900"
                      />
                      <span>I formed this classification without viewing AI verdicts, AI confidence, or historical SIEM resolution labels.</span>
                    </label>
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        disabled={!detail.can_submit_lock || !canMutate}
                        checked={attIndependent}
                        onChange={(e) => setAttIndependent(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900"
                      />
                      <span>This verdict represents my independent SOC judgment and is locked permanently for GT-3 certification.</span>
                    </label>
                  </div>

                  {detail.can_submit_lock && canMutate && (
                    <div className="flex flex-col sm:flex-row gap-2 pt-1">
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => handleReviewSubmit("DRAFT")}
                        className="flex-1 py-2 px-3 rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center justify-center gap-1.5"
                      >
                        <Save className="w-3.5 h-3.5" /> Save Draft
                      </button>
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => handleReviewSubmit("LOCK")}
                        className="flex-1 py-2 px-3 rounded bg-cyan-700 hover:bg-cyan-600 text-xs font-bold text-white flex items-center justify-center gap-1.5"
                      >
                        <Lock className="w-3.5 h-3.5" /> {submitting ? "Submitting..." : "Submit & Lock Independent Review"}
                      </button>
                    </div>
                  )}
                </div>

                {/* 6. Conflict Adjudication Panel (Senior / Admin ONLY on CONFLICT_PENDING_ADJUDICATION) */}
                {detail.cohort_item.certification_status === "CONFLICT_PENDING_ADJUDICATION" && isAdmin && (
                  <form
                    onSubmit={handleAdjudicate}
                    className="rounded-lg border border-rose-800/70 bg-rose-950/20 p-3.5 space-y-2.5"
                  >
                    <h3 className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Dual-Reviewer Conflict Adjudication (Senior/Admin)
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {detail.conflict_reviews.map((rev) => (
                        <div key={rev.review_id} className="p-2 rounded border border-slate-800 bg-slate-950 text-xs">
                          <div className="font-mono text-[10px] text-slate-400">
                            Reviewer: <strong className="text-slate-200">{rev.reviewer_id}</strong> • Confidence: {rev.confidence_level}
                          </div>
                          <div className="font-bold text-cyan-300 mt-0.5">{rev.analyst_verdict}</div>
                          <div className="text-[11px] text-slate-300 mt-1">{rev.analyst_notes}</div>
                        </div>
                      ))}
                    </div>
                    {detail.can_adjudicate ? (
                      <>
                        <div className="flex gap-2">
                          {(["TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"] as const).map((v) => (
                            <button
                              key={v}
                              type="button"
                              onClick={() => setAdjVerdict(v)}
                              className={`flex-1 py-1.5 rounded border text-xs font-bold ${
                                adjVerdict === v
                                  ? "bg-rose-950 text-rose-200 border-rose-500"
                                  : "bg-slate-900 text-slate-400 border-slate-800"
                              }`}
                            >
                              {v}
                            </button>
                          ))}
                        </div>
                        <textarea
                          rows={2}
                          required
                          value={adjRationale}
                          onChange={(e) => setAdjRationale(e.target.value)}
                          placeholder="Senior binding adjudication rationale (min 15 chars)..."
                          className="w-full p-2 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200"
                        />
                        <button
                          type="submit"
                          disabled={adjudicating}
                          className="w-full py-1.5 rounded bg-rose-700 hover:bg-rose-600 text-xs font-bold text-white"
                        >
                          {adjudicating ? "Finalizing..." : "Issue Binding GT-3 Adjudication"}
                        </button>
                      </>
                    ) : (
                      <div className="text-[11px] text-amber-300">
                        You participated as one of the conflicting reviewers; a third independent Senior Analyst or Administrator must adjudicate.
                      </div>
                    )}
                  </form>
                )}

                {/* 7. Post-Certification Final Result & Optional Comparison (UNLOCKED ONLY AFTER GT-3) */}
                {detail.certified_result && (
                  <div className="rounded-lg border border-emerald-800/70 bg-emerald-950/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                        <Award className="w-4 h-4" />
                        Certified Human Ground Truth: {detail.certified_result.certified_verdict}
                      </h3>
                      {isAdmin && !postCertComp && (
                        <button
                          type="button"
                          onClick={handleRevealPostCertComparison}
                          className="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] text-slate-200"
                        >
                          View Post-Certification Comparison (Admin)
                        </button>
                      )}
                    </div>
                    {postCertComp && (
                      <pre className="p-2 rounded bg-black/70 border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto">
                        {JSON.stringify(postCertComp, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
