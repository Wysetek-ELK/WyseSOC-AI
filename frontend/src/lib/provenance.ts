export interface ProvenanceBadgeInfo {
  label: string;
  sublabel?: string;
  className: string;
  isMock: boolean;
  isLiveProvider: boolean;
}

export function formatExecutionProvenanceBadge(opts: {
  executionProvenance?: string | null;
  historicalProvenance?: string | null;
  isSimulated?: boolean;
  validationStatus?: string | null;
  modelIdentifier?: string | null;
  sourceType?: string | null;
  eligibilityStatus?: string | null;
  currentS2Health?: string | null;
}): ProvenanceBadgeInfo {
  const provUp = (opts.executionProvenance || "").trim().toUpperCase();
  const modelId = (opts.modelIdentifier || "").trim();

  let resolved = provUp;
  if (!resolved) {
    if (opts.isSimulated) {
      resolved = "SIMULATED";
    } else if (["POLICY_GUARD", "PREFLIGHT_GUARD", "TOKEN_BUDGET_GUARD", "VALIDATION_GUARD"].includes(modelId)) {
      resolved = modelId;
    } else if ((opts.eligibilityStatus || "").toUpperCase() === "FAILED") {
      resolved = "OFFLINE";
    } else if ((opts.validationStatus || "").toUpperCase() === "INVALID_MODEL_OUTPUT") {
      resolved = "DEGRADED";
    } else if ((opts.sourceType || "").toUpperCase() === "HISTORICAL") {
      resolved = "HISTORICAL";
    } else {
      resolved = "LIVE_PROVIDER";
    }
  }

  switch (resolved) {
    case "HTTP_MOCK":
      return {
        label: "HTTP_MOCK",
        sublabel: opts.historicalProvenance || "Test HTTP Mock Endpoint (Non-GPU)",
        className: "bg-teal-950/70 text-teal-300 border-teal-700/70",
        isMock: true,
        isLiveProvider: false,
      };
    case "SIMULATED":
      return {
        label: "SIMULATED",
        sublabel: opts.historicalProvenance || "Deterministic Simulator (Non-Production)",
        className: "bg-amber-950/70 text-amber-300 border-amber-700/70",
        isMock: false,
        isLiveProvider: false,
      };
    case "OFFLINE":
      return {
        label: "OFFLINE",
        sublabel: "Provider Unreachable",
        className: "bg-rose-950/70 text-rose-300 border-rose-700/70",
        isMock: false,
        isLiveProvider: false,
      };
    case "DEGRADED":
      return {
        label: "DEGRADED",
        sublabel: "Degraded / Partial Provider Response",
        className: "bg-orange-950/70 text-orange-300 border-orange-700/70",
        isMock: false,
        isLiveProvider: false,
      };
    case "POLICY_GUARD":
    case "PREFLIGHT_GUARD":
    case "TOKEN_BUDGET_GUARD":
    case "VALIDATION_GUARD":
      return {
        label: resolved,
        sublabel: "Deterministic Safety Guardrail",
        className: "bg-amber-950/70 text-amber-300 border-amber-700/70",
        isMock: false,
        isLiveProvider: false,
      };
    case "HISTORICAL":
      return {
        label: "HISTORICAL",
        sublabel: opts.historicalProvenance || "Historical Record",
        className: "bg-indigo-950/70 text-indigo-300 border-indigo-700/70",
        isMock: false,
        isLiveProvider: false,
      };
    default:
      return {
        label: "LIVE_PROVIDER",
        sublabel:
          opts.currentS2Health === "OFFLINE"
            ? "Historical Live Provider (Cortex Offline Now)"
            : "Remote Verdictum Cortex Inference",
        className: "bg-emerald-950/70 text-emerald-300 border-emerald-700/70",
        isMock: false,
        isLiveProvider: true,
      };
  }
}

export function formatServer2HealthSummary(opts?: {
  is_healthy?: boolean;
  endpoint_provenance?: string | null;
  current_s2_health?: string | null;
  gpu_telemetry_verified?: boolean;
  status?: string | null;
}) {
  if (!opts) {
    return {
      statusLabel: "CHECKING",
      archLabel: "Verdictum Core",
      modelStatusText: "Checking...",
      badgeClass: "bg-slate-900 border-slate-800 text-slate-400",
      dotClass: "bg-slate-500",
      isMockEndpoint: false,
    };
  }

  const prov = (opts.endpoint_provenance || "").toUpperCase();
  const s2h = (opts.current_s2_health || opts.status || "").toUpperCase();

  if (prov === "HTTP_MOCK" || s2h === "HTTP_MOCK") {
    return {
      statusLabel: "HTTP_MOCK",
      archLabel: "Core + HTTP_MOCK (Test)",
      modelStatusText: "Mock HTTP (Non-GPU)",
      badgeClass: "bg-teal-950/60 border-teal-700/70 text-teal-300",
      dotClass: "bg-teal-400",
      isMockEndpoint: true,
    };
  }

  if (opts.is_healthy || s2h === "ONLINE" || s2h === "HEALTHY") {
    return {
      statusLabel: "ACTIVE",
      archLabel: opts.gpu_telemetry_verified ? "Core + Cortex (GPU)" : "Core + Cortex (HTTP API)",
      modelStatusText: opts.gpu_telemetry_verified ? "vLLM GPU Active" : "HTTP API Active",
      badgeClass: "bg-emerald-950/60 border-emerald-700/70 text-emerald-300",
      dotClass: "bg-emerald-400 animate-pulse",
      isMockEndpoint: false,
    };
  }

  if (s2h === "DEGRADED") {
    return {
      statusLabel: "DEGRADED",
      archLabel: "Core (Cortex Degraded)",
      modelStatusText: "Cortex Degraded",
      badgeClass: "bg-orange-950/60 border-orange-700/70 text-orange-300",
      dotClass: "bg-orange-400",
      isMockEndpoint: false,
    };
  }

  return {
    statusLabel: "CORTEX OFFLINE",
    archLabel: "Verdictum Core",
    modelStatusText: "Cortex Offline",
    badgeClass: "bg-rose-950/80 border-rose-700/80 text-rose-300",
    dotClass: "bg-rose-400",
    isMockEndpoint: false,
  };
}

