// API Client for AI Verdict Frontend

const API_BASE = "/api";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: "Administrator" | "SOC Analyst" | "Read-Only Viewer";
  is_active: boolean;
  created_at: string;
}

export interface IncidentAiVerdictResponse {
  incident_id: string;
  verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION";
  proposed_verdict?: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION";
  confidence: number;
  raw_model_confidence?: number;
  reason: string;
  supporting_evidence: string[];
  supporting_claims?: Array<{
    claim_type: string;
    field: string;
    asserted_value: any;
    is_grounded: boolean;
    grounding_status: string;
    reason?: string;
  }>;
  missing_evidence: string[];
  analyst_questions: string[];
  latency_ms: number;
  model_identifier: string;
  is_simulated: boolean;
  rule_name?: string;
  severity?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  evaluated_at?: string;
  evaluated_by_user?: string;
  validation_status?: string;
  validation_reason_codes?: string[];
  is_decisive_accepted?: boolean;
  evidence_completeness?: number;
  grounding_ratio?: number;
  total_claims_count?: number;
  grounded_claims_count?: number;
  unsupported_claims_count?: number;
  unsupported_claims?: Array<Record<string, any>>;
  detected_contradictions?: string[];
  analyst_action_directive?: string;
  canonical_evidence_count?: number;
  contract_id?: string;
  contract_version?: number;
  validator_version?: string;
  replay_signature?: string;
  compiler_version?: string;
  compilation_digest?: string;
  policy_sections_count?: number;
  policy_version_number?: number;
  policy_status?: string;
  calibration_status?: string;
  is_calibrated?: boolean;
  rag_retrieval_status?: string;
  retrieved_precedents_count?: number;
  retrieved_precedents?: Array<{
    precedent_id: string;
    incident_id: string;
    incident_title: string;
    rule_id: string;
    verified_verdict: string;
    analyst_explanation: string;
    similarity_score: number;
    feedback_timestamp: string;
  }>;
  token_budget_breakdown?: Record<string, any>;
}

export interface IncidentListItem {
  id: string;
  incident_id: string;
  rule_id?: string;
  rule_name?: string;
  event_type: string;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFORMATIONAL";
  status_code: number;
  status_name: string;
  category: string;
  source_ip: string;
  reporting_device: string;
  created_at_epoch?: number;
  first_seen_epoch?: number;
  last_seen_epoch?: number;
  historical_resolution?: string;
  ai_verdict?: IncidentAiVerdictResponse | null;
  event_count: number;
  created_at: string;
}

export interface IncidentDetail {
  id: string;
  incident_id: string;
  rule_id?: string;
  rule_name?: string;
  rule_description?: string;
  import_job_id?: string;
  event_type: string;
  title: string;
  description: string;
  detail: string;
  severity: string;
  event_severity: string;
  status_code: number;
  status_name: string;
  category: string;
  subcategory: string;
  source_ip: string;
  reporting_device: string;
  reporting_ip: string;
  customer: string;
  ticket_id: string;
  first_seen_epoch?: number;
  last_seen_epoch?: number;
  created_at_epoch?: number;
  updated_at_epoch?: number;
  raw_payload: Record<string, any>;
  events: Array<{
    id: string;
    event_id: string;
    event_receive_time?: number;
    event_type: string;
    raw_log: string;
    attributes: Record<string, any>;
  }>;
  ground_truth?: {
    id: string;
    resolution: string;
    cleared_reason: string;
    comments: string;
    cleared_user: string;
    cleared_time_epoch?: number;
    resolved_at_epoch?: number;
    is_ml_generated: boolean;
    created_at: string;
  } | null;
  ai_verdict?: IncidentAiVerdictResponse | null;
  created_at: string;
  updated_at: string;
}

export interface InvestigationQuestion {
  id: string;
  investigation_id: string;
  question: string;
  answer: string;
  asked_by_user_id?: string;
  answered_by_user_id?: string;
  created_at: string;
  answered_at?: string;
}

export interface InvestigationEvidence {
  id: string;
  investigation_id: string;
  evidence_type: string;
  reference_key: string;
  evidence_content: string;
  analyst_rationale: string;
  created_at: string;
}

export interface FortiSIEMPullResponse {
  success: boolean;
  incident_id: string;
  db_id?: string;
  title: string;
  event_type: string;
  severity: string;
  status_name: string;
  event_count: number;
  source: string;
  message: string;
  error?: string;
}

export interface FortiSIEMBatchPullRequest {
  time_from?: number;
  time_to?: number;
  max_count?: number;
  auto_triage_llm?: boolean;
  force_refresh?: boolean;
}

export interface FortiSIEMBatchPullResponse {
  success: boolean;
  total_discovered: number;
  newly_ingested: number;
  already_cached: number;
  ai_verdicts_generated: number;
  checkpoint_epoch?: number;
  source: string;
  message: string;
  sample_incidents: Array<{
    incident_id: string;
    title: string;
    severity: string;
    event_type: string;
    status: string;
    has_ai_verdict: boolean;
  }>;
}

export interface FortiSIEMSchedulerStatusResponse {
  is_running: boolean;
  interval_seconds: number;
  auto_ai_verdict: boolean;
  initial_pull_completed: boolean;
  checkpoint_epoch?: number;
  last_sync_time?: string;
  next_sync_time?: string;
  last_status: string;
  last_error?: string;
  total_pulled_count: number;
  total_ai_verdicts_count: number;
  is_llm_online?: boolean;
  pending_ai_verdicts_count?: number;
  recent_sync_logs: Array<{
    timestamp: string;
    status: string;
    mode?: string;
    newly_ingested?: number;
    already_cached?: number;
    ai_verdicts_generated?: number;
    message?: string;
    error?: string;
  }>;
}

export interface FortiSIEMSchedulerControlRequest {
  interval_seconds?: number;
  auto_ai_verdict?: boolean;
}

export interface FortiSIEMBatchVerdictRequest {
  incident_ids?: string[];
  max_batch?: number;
}

export interface FortiSIEMBatchVerdictResponse {
  success: boolean;
  total_requested: number;
  processed: number;
  successful: number;
  failed: number;
  results: Array<Record<string, any>>;
  message: string;
}

export interface FortiSIEMStatusResponse {
  is_configured: boolean;
  host: string;
  username: string;
  verify_ssl: boolean;
  mode: string;
  sample_incident_ids: string[];
  live_incident_ids?: string[];
}

export interface FortiSIEMConfigResponse {
  is_configured: boolean;
  host: string;
  username: string;
  is_password_set: boolean;
  verify_ssl: boolean;
  timeout: number;
  mock_fallback: boolean;
}

export interface FortiSIEMConfigUpdate {
  host: string;
  username: string;
  password?: string;
  verify_ssl: boolean;
  timeout: number;
  mock_fallback: boolean;
}

export interface FortiSIEMTestConnectionRequest {
  host: string;
  username: string;
  password?: string;
  verify_ssl: boolean;
  timeout: number;
}

export interface FortiSIEMTestConnectionResponse {
  success: boolean;
  status_code?: number;
  latency_ms?: number;
  message: string;
  details?: Record<string, any>;
}

export interface LLMConfigResponse {
  host: string;
  port: number;
  protocol: string;
  base_url: string;
  model_name: string;
  timeout: number;
  allow_mock_fallback: boolean;
  is_online: boolean;
  server1_outbound_ip?: string;
}

export interface LLMConfigUpdate {
  host: string;
  port?: number;
  protocol?: string;
  model_name?: string;
  timeout?: number;
  allow_mock_fallback?: boolean;
}

export interface LLMTestConnectionRequest {
  host: string;
  port?: number;
  protocol?: string;
  timeout?: number;
}

export interface LLMTestConnectionResponse {
  success: boolean;
  status_code?: number;
  latency_ms?: number;
  message: string;
  models: string[];
  tested_url: string;
}

export interface FortiSIEMRuleSyncResponse {
  success: boolean;
  synced_rules_count: number;
  new_rules_count: number;
  updated_rules_count: number;
  total_local_rules: number;
  synced_rules: Array<{
    rule_id: string;
    name: string;
    severity: string;
    event_type: string;
    is_new?: boolean;
  }>;
  message: string;
}

export interface FortiSIEMRulePullResponse {
  success: boolean;
  rule_id: string;
  name: string;
  event_type: string;
  severity: string;
  source: string;
  pattern_logic: string;
  message: string;
}

export interface InvestigationListItem {
  id: string;
  incident_id: string;
  incident_vendor_id?: string;
  title?: string;
  rule_id?: string;
  rule_name?: string;
  severity?: string;
  event_type?: string;
  status: string;
  assigned_to_user_id?: string;
  assigned_to_username?: string;
  analyst_verdict?: string;
  is_disputed: boolean;
  is_independently_verified: boolean;
  question_count: number;
  evidence_count: number;
  created_at: string;
  updated_at: string;
}

export interface InvestigationDetail {
  id: string;
  incident_id: string;
  assigned_to_user_id?: string;
  assigned_to_username?: string;
  status: string;
  analyst_verdict?: string;
  verdict_reason: string;
  analyst_notes: string;
  is_disputed: boolean;
  is_independently_verified: boolean;
  insufficient_evidence_reason?: string;
  created_at: string;
  updated_at: string;
  incident_vendor_id?: string;
  title?: string;
  rule_id?: string;
  rule_name?: string;
  severity?: string;
  event_type?: string;
  source_ip?: string;
  reporting_device?: string;
  questions: InvestigationQuestion[];
  evidence_items: InvestigationEvidence[];
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version_number: number;
  status: "DRAFT" | "APPROVED" | "ARCHIVED";
  is_template_draft: boolean;
  quality_status?: string;
  quality_score?: number | null;
  quality_assessment_id?: string | null;
  common_prompt: string;
  rule_specific_prompt: string;
  detection_conditions: string;
  required_evidence: string;
  tp_indicators: string;
  fp_indicators: string;
  missing_info_criteria: string;
  escalation_conditions: string;
  analyst_questions: string[];
  change_summary: string;
  created_by_user_id?: string;
  approved_by_user_id?: string;
  approved_at?: string;
  created_at: string;
}

export interface RulePrompt {
  id: string;
  rule_id: string;
  rule_name?: string;
  rule_event_type?: string;
  title: string;
  active_version_id?: string;
  active_version?: PromptVersion | null;
  versions: PromptVersion[];
  created_at: string;
  updated_at: string;
}

export interface RulePromptSummaryItem {
  rule_id: string;
  rule_name: string;
  event_type: string;
  severity: string;
  status: string;
  data_source?: string;
  prompt_id?: string;
  active_version_number?: number;
  active_version_status?: string;
  total_versions: number;
  has_approved_prompt: boolean;
  last_updated?: string;
  detection_archetype?: string;
  definition_completeness?: string;
  quality_score?: number | null;
  quality_validation_status?: string;
  blocking_issue_count?: number;
  simulation_status?: string;
  last_validated_date?: string | null;
  revalidation_required?: boolean;
}

export interface QualityGateResult {
  gate_id: string;
  gate_name: string;
  status: "PASSED" | "WARNING" | "FAILED";
  score: number;
  max_score: number;
  details: string;
  blocking_findings: string[];
  warnings: string[];
}

export interface PolicyQualityAssessmentResponse {
  assessment_id: string;
  rule_identifier: string;
  policy_version_number: number;
  prompt_version_id?: string;
  archetype: string;
  validator_version: string;
  quality_score: number;
  structural_quality_score?: number;
  empirical_validation_score?: number;
  empirical_validation_status?: string;
  score_breakdown: Record<string, number>;
  gate_results: Record<string, QualityGateResult>;
  gates?: QualityGateResult[];
  blocking_issues: string[];
  blocking_findings?: string[];
  warnings: string[];
  missing_evidence_mappings: string[];
  recommendations: string[];
  simulation_status: string;
  approval_eligible: boolean;
  hard_gate_failure?: boolean;
  validation_status?: string;
  policy_digest: string;
  contract_digest: string;
  rule_digest: string;
  archetype_version: string;
  evaluated_at: string;
}

export interface RuleIntelligenceData {
  rule_id: string;
  rule_identifier: string;
  semantics: {
    rule_identifier: string;
    rule_name: string;
    siem_vendor: string;
    data_source: string;
    event_category: string;
    sub_category?: string;
    detection_objective: string;
    definition_status: "VERIFIED" | "INCOMPLETE" | "UNKNOWN" | "CONFLICTING";
    source_provenance: string;
    threshold?: number | null;
    threshold_unit?: string | null;
    aggregation_window?: string | null;
    grouping_keys: string[];
    suppression_conditions: string[];
    relevant_fields: string[];
    observed_fields: string[];
    attck_tactics: string[];
    attck_techniques: string[];
    primary_behavior: string;
    review_required: boolean;
    missing_requirements: string[];
    provenance_details: Record<string, string>;
  };
  classification: {
    rule_identifier: string;
    primary_archetype: string;
    secondary_archetype?: string;
    confidence_score: number;
    classification_reason: string;
    matched_features: string[];
    traceability_log: string[];
    registry_version: string;
  };
  archetype_definition: {
    archetype_id: string;
    name: string;
    version: string;
    detection_purpose: string;
    mandatory_core_fields: string[];
    conditional_fields: string[];
    optional_enrichment_fields: string[];
    unsupported_fields: string[];
    tp_indicator_candidates: string[];
    fp_indicator_candidates: string[];
    abstention_requirements: string[];
    escalation_considerations: string[];
    analyst_question_templates: string[];
    unsupported_assumptions: string[];
  };
  candidate_evidence_contract?: any;
}

export interface QualitySummaryItem {
  total_rules: number;
  rules_with_approved_policies: number;
  policies_passing_static_checks: number;
  policies_requiring_review: number;
  policies_with_critical_issues: number;
  policies_with_incomplete_definitions: number;
  policies_with_missing_evidence_mappings: number;
  policies_lacking_simulation_evidence: number;
  quality_score_average: number;
  rules_requiring_revalidation: number;
}

export interface PolicyDriftEventItem {
  id: string;
  trigger_type: string;
  summary: string;
  changed_fields: Record<string, any>;
  revalidation_required: boolean;
  acknowledged: boolean;
  created_at: string;
}

export interface LearningRecord {
  id: string;
  rule_id: string;
  rule_name?: string;
  incident_id: string;
  incident_vendor_id?: string;
  incident_title?: string;
  verified_verdict: string;
  analyst_explanation: string;
  tp_indicators: string[];
  fp_indicators: string[];
  missing_evidence: string[];
  evidence_references: string[];
  answered_questions: Array<{ question: string; answer: string }>;
  verification_status: string;
  feedback_timestamp: string;
  created_at: string;
}

export interface SimilarCaseMatch {
  learning_record_id: string;
  incident_id: string;
  incident_vendor_id?: string;
  title?: string;
  verified_verdict: string;
  analyst_explanation: string;
  match_score: number;
  matched_features: string[];
  feedback_timestamp: string;
}

export interface RuleItem {
  id: string;
  rule_id: string;
  name: string;
  event_type: string;
  description: string;
  severity: string;
  status: string;
  data_source: string;
  detection_tech: string;
  evaluation_mode: string;
  pattern_logic: string;
  remediation: string;
  raw_rule_text: string;
  parsed_metadata?: Record<string, any>;
  incident_count: number;
  created_at: string;
  updated_at: string;
}

export interface RuleStatsResponse {
  total_rules: number;
  active_rules: number;
  inactive_rules: number;
  critical_rules: number;
  high_rules: number;
  medium_rules: number;
  low_rules: number;
  rules_with_incidents: number;
  total_linked_incidents: number;
  rules_with_prompt_templates: number;
}

export interface DashboardMetrics {
  total_incidents: number;
  total_rules: number;
  historical_true_positives: number;
  historical_false_positives: number;
  unresolved_incidents: number;
  ai_evaluated_count?: number;
  ai_true_positives?: number;
  ai_false_positives?: number;
  ai_requires_attention?: number;
  ai_pending_evaluation?: number;
  severity_breakdown: Array<{ severity: string; count: number; percentage: number }>;
  source_breakdown: Array<{ source: string; count: number; percentage: number }>;
  ground_truth_breakdown: Array<{ verdict: string; count: number; percentage: number }>;
  recent_activity: Array<{
    incident_id: string;
    title: string;
    severity: string;
    event_type: string;
    created_at_epoch?: number;
    historical_verdict?: string;
    ai_verdict?: IncidentAiVerdictResponse | null;
    created_at: string;
  }>;
  recent_imports: Array<{
    id: string;
    filename: string;
    file_type: string;
    imported_count: number;
    duplicate_count: number;
    error_count: number;
    status: string;
    created_at: string;
  }>;
  is_empty: boolean;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("ai_verdict_token") : null;
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  options.credentials = "include"; // For HttpOnly cookie support
  options.headers = headers;

  const res = await fetch(url, options);
  if (res.status === 401 && typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    localStorage.removeItem("ai_verdict_token");
    localStorage.removeItem("ai_verdict_user");
    window.location.href = "/login";
  }
  return res;
}

export const api = {
  // Auth
  async login(username: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Invalid credentials");
    }
    return res.json();
  },

  async logout() {
    await fetchWithAuth(`${API_BASE}/auth/logout`, { method: "POST" });
    if (typeof window !== "undefined") {
      localStorage.removeItem("ai_verdict_token");
      localStorage.removeItem("ai_verdict_user");
    }
  },

  async getMe(): Promise<User> {
    const res = await fetchWithAuth(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error("Unauthorized");
    return res.json();
  },

  // Dashboard
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const res = await fetchWithAuth(`${API_BASE}/dashboard/metrics`);
    if (!res.ok) throw new Error("Failed to load dashboard metrics");
    return res.json();
  },

  async getLlmStatus(): Promise<{
    status: string;
    is_healthy: boolean;
    model: string;
    latency_ms: number;
    message?: string;
  }> {
    const res = await fetchWithAuth(`${API_BASE}/dashboard/llm-status`);
    if (!res.ok) throw new Error("Failed to load LLM status");
    return res.json();
  },

  // Incidents
  async getIncidents(params: {
    page?: number;
    page_size?: number;
    search?: string;
    severity?: string;
    status?: string;
    rule_id?: string;
    resolution?: string;
    blind_review?: boolean;
  } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.search) q.set("search", params.search);
    if (params.severity) q.set("severity", params.severity);
    if (params.status) q.set("status", params.status);
    if (params.rule_id) q.set("rule_id", params.rule_id);
    if (params.resolution) q.set("resolution", params.resolution);
    if (params.blind_review !== undefined) q.set("blind_review", params.blind_review.toString());

    const res = await fetchWithAuth(`${API_BASE}/incidents?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch incidents");
    return res.json();
  },

  async getIncidentDetail(id: string, blindReview: boolean = false): Promise<IncidentDetail> {
    const res = await fetchWithAuth(`${API_BASE}/incidents/${id}?blind_review=${blindReview}`);
    if (!res.ok) throw new Error("Incident not found");
    return res.json();
  },

  async getIncidentModelPayload(id: string) {
    const res = await fetchWithAuth(`${API_BASE}/incidents/${id}/model-payload`);
    if (!res.ok) throw new Error("Failed to fetch model payload");
    return res.json();
  },

  async getIncidentAiVerdict(id: string): Promise<IncidentAiVerdictResponse> {
    const res = await fetchWithAuth(`${API_BASE}/incidents/${id}/ai-verdict`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "AI verdict failed" }));
      throw new Error(err.detail || "Failed to generate AI verdict");
    }
    return res.json();
  },

  async getIncidentTimeline(id: string): Promise<IncidentTimelineResponse> {
    const res = await fetchWithAuth(`${API_BASE}/incidents/${encodeURIComponent(id)}/timeline`);
    if (!res.ok) throw new Error("Failed to load incident telemetry timeline");
    return res.json();
  },

  async getTokenAnalytics(windowDays: number = 30, processType?: string): Promise<TokenAnalyticsResponse> {
    const params = new URLSearchParams();
    if (windowDays) params.append("window_days", windowDays.toString());
    if (processType) params.append("process_type", processType);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetchWithAuth(`${API_BASE}/tokens/analytics${qs}`);
    if (!res.ok) throw new Error("Failed to load token bifurcation analytics");
    return res.json();
  },

  async getGlobalTelemetryTimeline(limit: number = 50, stage?: string): Promise<GlobalTelemetryTimelineResponse> {
    const params = new URLSearchParams();
    if (limit) params.append("limit", limit.toString());
    if (stage) params.append("stage", stage);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetchWithAuth(`${API_BASE}/telemetry/timeline${qs}`);
    if (!res.ok) throw new Error("Failed to load global telemetry timeline");
    return res.json();
  },

  // Rules
  async getRules(params: { page?: number; page_size?: number; search?: string; severity?: string; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.search) q.set("search", params.search);
    if (params.severity) q.set("severity", params.severity);
    if (params.status) q.set("status", params.status);

    const res = await fetchWithAuth(`${API_BASE}/rules?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch rules");
    return res.json();
  },

  async getRuleStats(): Promise<RuleStatsResponse> {
    const res = await fetchWithAuth(`${API_BASE}/rules/stats`);
    if (!res.ok) throw new Error("Failed to fetch rule statistics");
    return res.json();
  },

  async getRuleDetail(id: string): Promise<RuleItem> {
    const res = await fetchWithAuth(`${API_BASE}/rules/${id}`);
    if (!res.ok) throw new Error("Rule not found");
    return res.json();
  },

  // Imports
  async uploadImport(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetchWithAuth(`${API_BASE}/imports/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload error");
    }
    return res.json();
  },

  async getImportJobs() {
    const res = await fetchWithAuth(`${API_BASE}/imports/jobs`);
    if (!res.ok) throw new Error("Failed to fetch import jobs");
    return res.json();
  },

  // FortiSIEM Live Pull & Configuration
  async getFortiSiemStatus(): Promise<FortiSIEMStatusResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/status`);
    if (!res.ok) throw new Error("Failed to fetch FortiSIEM status");
    return res.json();
  },

  async getFortiSiemConfig(): Promise<FortiSIEMConfigResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/config`);
    if (!res.ok) throw new Error("Failed to fetch FortiSIEM configuration");
    return res.json();
  },

  async updateFortiSiemConfig(data: FortiSIEMConfigUpdate): Promise<FortiSIEMConfigResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update FortiSIEM configuration" }));
      throw new Error(err.detail || "Update error");
    }
    return res.json();
  },

  async testFortiSiemConnection(data: FortiSIEMTestConnectionRequest): Promise<FortiSIEMTestConnectionResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/test-connection`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Connection test request failed" }));
      throw new Error(err.detail || "Connection test error");
    }
    return res.json();
  },

  async getLLMConfig(): Promise<LLMConfigResponse> {
    const res = await fetchWithAuth(`${API_BASE}/llm/config`);
    if (!res.ok) throw new Error("Failed to fetch LLM configuration");
    return res.json();
  },

  async updateLLMConfig(data: LLMConfigUpdate): Promise<LLMConfigResponse> {
    const res = await fetchWithAuth(`${API_BASE}/llm/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update LLM configuration" }));
      throw new Error(err.detail || "Update error");
    }
    return res.json();
  },

  async testLLMConnection(data: LLMTestConnectionRequest): Promise<LLMTestConnectionResponse> {
    const res = await fetchWithAuth(`${API_BASE}/llm/test-connection`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "LLM connection test request failed" }));
      throw new Error(err.detail || "LLM connection test error");
    }
    return res.json();
  },

  async pullFortiSiemIncident(incidentId: string, forceRefresh = false): Promise<FortiSIEMPullResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/fetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: incidentId, force_refresh: forceRefresh }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to pull incident from FortiSIEM" }));
      throw new Error(err.detail || "FortiSIEM pull error");
    }
    return res.json();
  },

  async syncFortiSiemRules(): Promise<FortiSIEMRuleSyncResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/sync-rules`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to sync rules from FortiSIEM" }));
      throw new Error(err.detail || "FortiSIEM rule synchronization error");
    }
    return res.json();
  },

  async pullFortiSiemRule(ruleId: string, forceRefresh: boolean = false): Promise<FortiSIEMRulePullResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/pull-rule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_id: ruleId, force_refresh: forceRefresh }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Failed to pull rule '${ruleId}' from FortiSIEM` }));
      throw new Error(err.detail || "FortiSIEM rule pull error");
    }
    return res.json();
  },

  async pullAllFortiSiemIncidents(req?: FortiSIEMBatchPullRequest): Promise<FortiSIEMBatchPullResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/pull-all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to batch pull incidents" }));
      throw new Error(err.detail || "Batch pull error");
    }
    return res.json();
  },

  async getFortiSiemSchedulerStatus(): Promise<FortiSIEMSchedulerStatusResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/scheduler/status`);
    if (!res.ok) throw new Error("Failed to fetch scheduler status");
    return res.json();
  },

  async startFortiSiemScheduler(req?: FortiSIEMSchedulerControlRequest): Promise<FortiSIEMSchedulerStatusResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/scheduler/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to start continuous scheduler" }));
      throw new Error(err.detail || "Scheduler start error");
    }
    return res.json();
  },

  async stopFortiSiemScheduler(): Promise<FortiSIEMSchedulerStatusResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/scheduler/stop`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to stop continuous scheduler");
    return res.json();
  },

  async triggerFortiSiemScheduler(): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/scheduler/trigger`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to trigger immediate sync");
    return res.json();
  },

  async processPendingFortiSiemVerdicts(max_count: number = 100): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/process-pending-verdicts?max_count=${max_count}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to process pending AI verdicts");
    return res.json();
  },

  async batchEvaluateAIVerdicts(req?: FortiSIEMBatchVerdictRequest): Promise<FortiSIEMBatchVerdictResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/batch-ai-verdict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Batch AI verdict failed" }));
      throw new Error(err.detail || "Batch verdict error");
    }
    return res.json();
  },

  // Users & Audit
  async getUsers(): Promise<User[]> {
    const res = await fetchWithAuth(`${API_BASE}/users`);
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  async createUser(data: any): Promise<User> {
    const res = await fetchWithAuth(`${API_BASE}/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to create user" }));
      throw new Error(err.detail || "Failed to create user");
    }
    return res.json();
  },

  async getAuditLogs(params: { page?: number; page_size?: number; action?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.action) q.set("action", params.action);

    const res = await fetchWithAuth(`${API_BASE}/audit?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch audit logs");
    return res.json();
  },

  // =================== PHASE 2: INVESTIGATIONS ===================
  async getInvestigationsQueue(params: {
    page?: number;
    page_size?: number;
    status?: string;
    assigned_to?: string;
    verdict?: string;
    is_disputed?: boolean;
    rule_id?: string;
    search?: string;
  } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.status) q.set("status", params.status);
    if (params.assigned_to) q.set("assigned_to", params.assigned_to);
    if (params.verdict) q.set("verdict", params.verdict);
    if (params.is_disputed !== undefined) q.set("is_disputed", String(params.is_disputed));
    if (params.rule_id) q.set("rule_id", params.rule_id);
    if (params.search) q.set("search", params.search);

    const res = await fetchWithAuth(`${API_BASE}/investigations/queue?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch investigations queue");
    return res.json();
  },

  async getInvestigation(id: string): Promise<InvestigationDetail> {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}`);
    if (!res.ok) throw new Error("Failed to fetch investigation details");
    return res.json();
  },

  async getInvestigationByIncident(incidentId: string): Promise<InvestigationDetail> {
    const res = await fetchWithAuth(`${API_BASE}/investigations/by-incident/${incidentId}`);
    if (!res.ok) throw new Error("Failed to fetch investigation for incident");
    return res.json();
  },

  async assignInvestigation(id: string, userId: string | null) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) throw new Error("Failed to assign analyst");
    return res.json();
  },

  async updateInvestigationStatus(id: string, status: string) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
  },

  async addInvestigationQuestion(id: string, question: string) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) throw new Error("Failed to add question");
    return res.json();
  },

  async answerInvestigationQuestion(questionId: string, answer: string) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/questions/${questionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    });
    if (!res.ok) throw new Error("Failed to answer question");
    return res.json();
  },

  async attachInvestigationEvidence(id: string, data: {
    evidence_type: string;
    reference_key: string;
    evidence_content: string;
    analyst_rationale: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to attach evidence");
    return res.json();
  },

  async submitInvestigationVerdict(id: string, data: {
    analyst_verdict: string;
    verdict_reason: string;
    analyst_notes: string;
    insufficient_evidence_reason?: string | null;
    is_disputed: boolean;
    is_independently_verified: boolean;
    status?: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/investigations/${id}/verdict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to submit verdict");
    return res.json();
  },

  // =================== PHASE 2: PROMPT STUDIO ===================
  async getRulePromptsSummary(): Promise<RulePromptSummaryItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/summary`);
    if (!res.ok) throw new Error("Failed to fetch rule prompts summary");
    return res.json();
  },

  async getRulePrompt(ruleId: string): Promise<RulePrompt> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}`);
    if (!res.ok) throw new Error("Failed to fetch rule prompt");
    return res.json();
  },

  async generateTemplateDraft(ruleId: string): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/generate-draft`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to generate template draft");
    return res.json();
  },

  async createManualDraft(ruleId: string, data: {
    common_prompt: string;
    rule_specific_prompt: string;
    detection_conditions: string;
    required_evidence: string;
    tp_indicators: string;
    fp_indicators: string;
    missing_info_criteria: string;
    escalation_conditions: string;
    analyst_questions: string[];
    change_summary: string;
  }): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create draft version");
    return res.json();
  },

  async approvePromptVersion(ruleId: string, versionId: string, changeSummary?: string): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/approve/${versionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ change_summary: changeSummary || "Approved by SOC Lead" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to approve prompt version" }));
      throw new Error(err.detail || "Failed to approve prompt version");
    }
    return res.json();
  },

  async rollbackPromptVersion(ruleId: string, versionId: string): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/rollback/${versionId}`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to rollback prompt version" }));
      throw new Error(err.detail || "Failed to rollback prompt version");
    }
    return res.json();
  },

  async exportRulePrompts(format: "json" | "markdown" = "json"): Promise<{ blob: Blob; filename: string }> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/export?format=${format}`);
    if (!res.ok) throw new Error("Failed to export rule prompts");
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition");
    let filename = `agent_intelligence_studio_rules_prompts.${format === "json" ? "json" : "md"}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename };
  },


  async exportSingleRulePrompt(ruleId: string, format: "json" | "markdown" = "json"): Promise<{ blob: Blob; filename: string }> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/export?format=${format}`);
    if (!res.ok) throw new Error("Failed to export rule prompt configuration");
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition");
    let filename = `rule_prompt_${ruleId}.${format === "json" ? "json" : "md"}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename };
  },


  // =================== AGENT INTELLIGENCE STUDIO 2.0 ===================
  async getRuleIntelligence(ruleId: string): Promise<RuleIntelligenceData> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/intelligence`);
    if (!res.ok) throw new Error("Failed to fetch rule intelligence and detection semantics");
    return res.json();
  },

  async analyzeRuleIntelligence(ruleId: string, authoritativeDefinition?: any): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ authoritative_siem_definition: authoritativeDefinition }),
    });
    if (!res.ok) throw new Error("Failed to analyze rule intelligence");
    return res.json();
  },

  async generateIntelligentDraft(ruleId: string, authoritativeDefinition?: any): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/generate-intelligent-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ authoritative_siem_definition: authoritativeDefinition }),
    });
    if (!res.ok) throw new Error("Failed to generate intelligent draft");
    return res.json();
  },

  async validatePolicyQuality(ruleId: string, versionId?: string): Promise<PolicyQualityAssessmentResponse> {
    const url = versionId ? `${API_BASE}/prompts/rule/${ruleId}/validate-quality?version_id=${versionId}` : `${API_BASE}/prompts/rule/${ruleId}/validate-quality`;
    const res = await fetchWithAuth(url, { method: "POST" });
    if (!res.ok) throw new Error("Failed to validate policy quality");
    return res.json();
  },

  async evaluatePolicySimulation(ruleId: string, versionId?: string): Promise<any> {
    const url = versionId ? `${API_BASE}/prompts/rule/${ruleId}/evaluate-simulation?version_id=${versionId}` : `${API_BASE}/prompts/rule/${ruleId}/evaluate-simulation`;
    const res = await fetchWithAuth(url, { method: "POST" });
    if (!res.ok) throw new Error("Failed to evaluate policy simulation");
    return res.json();
  },

  async getPolicyQualitySummary(): Promise<QualitySummaryItem> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/quality/summary`);
    if (!res.ok) throw new Error("Failed to fetch policy quality summary");
    return res.json();
  },

  async startBulkQualityAudit(): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/quality/bulk-assess`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to start bulk quality audit");
    return res.json();
  },

  async getBulkQualityAuditStatus(jobId: string): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/quality/bulk-assess/${jobId}`);
    if (!res.ok) throw new Error("Failed to get bulk quality audit status");
    return res.json();
  },

  async getRuleDriftEvents(ruleId: string): Promise<PolicyDriftEventItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/drift`);
    if (!res.ok) throw new Error("Failed to fetch rule drift events");
    return res.json();
  },

  async acknowledgeDriftEvents(ruleId: string): Promise<{ acknowledged_count: number }> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/acknowledge-drift`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to acknowledge drift events");
    return res.json();
  },

  // =================== PHASE 2: LEARNING HISTORY ===================
  async getLearningRecords(params: {
    page?: number;
    page_size?: number;
    rule_id?: string;
    verification_status?: string;
    verdict?: string;
    search?: string;
  } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.rule_id) q.set("rule_id", params.rule_id);
    if (params.verification_status) q.set("verification_status", params.verification_status);
    if (params.verdict) q.set("verdict", params.verdict);
    if (params.search) q.set("search", params.search);

    const res = await fetchWithAuth(`${API_BASE}/learning/records?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch learning records");
    return res.json();
  },

  async getLearningRecord(id: string): Promise<LearningRecord> {
    const res = await fetchWithAuth(`${API_BASE}/learning/records/${id}`);
    if (!res.ok) throw new Error("Failed to fetch learning record");
    return res.json();
  },

  async findSimilarCases(data: {
    incident_id?: string;
    rule_id?: string;
    event_type?: string;
    source_ip?: string;
    command_substring?: string;
    top_k?: number;
  }): Promise<SimilarCaseMatch[]> {
    const res = await fetchWithAuth(`${API_BASE}/learning/similar-cases`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to search similar cases");
    return res.json();
  },

  async seedHistoricalLearning() {
    const res = await fetchWithAuth(`${API_BASE}/learning/seed-historical`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to seed historical learning cases");
    return res.json();
  },

  // =================== PHASE 3: DRY-RUN ENGINE ===================
  async createDryRunConfig(data: {
    name: string;
    description?: string;
    rule_id?: string;
    prompt_version_id?: string;
    provider_type?: string;
    split_strategy?: string;
    dataset_filters?: Record<string, any>;
  }): Promise<DryRunConfig> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/configs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create dry run config");
    }
    return res.json();
  },

  async getDryRunConfigs(): Promise<DryRunConfig[]> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/configs`);
    if (!res.ok) throw new Error("Failed to fetch dry run configs");
    return res.json();
  },

  async getDryRunConfig(id: string): Promise<DryRunConfig> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/configs/${id}`);
    if (!res.ok) throw new Error("Failed to fetch dry run config");
    return res.json();
  },

  async triggerDryRunJob(configId: string, customSampleLimit?: number): Promise<DryRunJob> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_id: configId, custom_sample_limit: customSampleLimit }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to trigger dry run job");
    }
    return res.json();
  },

  async getDryRunJobs(limit: number = 50): Promise<DryRunJob[]> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/jobs?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch dry run jobs");
    return res.json();
  },

  async getDryRunJob(id: string): Promise<DryRunJob> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/jobs/${id}`);
    if (!res.ok) throw new Error("Failed to fetch dry run job");
    return res.json();
  },

  async getDryRunJobResults(jobId: string, limit: number = 100, offset: number = 0): Promise<DryRunResult[]> {
    const res = await fetchWithAuth(`${API_BASE}/dry-run/jobs/${jobId}/results?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error("Failed to fetch dry run results");
    return res.json();
  },

  // =================== PHASE 3: EVALUATION FRAMEWORK ===================
  async getJobMetrics(jobId: string): Promise<EvaluationMetrics> {
    const res = await fetchWithAuth(`${API_BASE}/evaluations/job/${jobId}/metrics`);
    if (!res.ok) throw new Error("Failed to fetch job evaluation metrics");
    return res.json();
  },

  async getPromptComparisons(ruleId: string): Promise<PromptComparisonItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/evaluations/prompt-comparison/${ruleId}`);
    if (!res.ok) throw new Error("Failed to fetch prompt comparisons");
    return res.json();
  },

  async getRuleMaturityStatus(): Promise<RuleMaturity[]> {
    const res = await fetchWithAuth(`${API_BASE}/evaluations/rule-maturity`);
    if (!res.ok) throw new Error("Failed to fetch rule maturity evaluations");
    return res.json();
  },

  async approveRuleForAutomation(ruleId: string, approvalNotes: string): Promise<RuleMaturity> {
    const res = await fetchWithAuth(`${API_BASE}/evaluations/rule-maturity/${ruleId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approval_notes: approvalNotes }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to approve rule for automation");
    }
    return res.json();
  },

  // =================== DUAL-SERVER INFRASTRUCTURE MONITORING ===================
  async getServersLive(): Promise<ServersLiveResponse> {
    const res = await fetchWithAuth(`${API_BASE}/system/servers/live`);
    if (!res.ok) throw new Error("Failed to fetch live server metrics");
    return res.json();
  },

  async getServersHistory(window: string = "24h"): Promise<ServersHistoryResponse> {
    const res = await fetchWithAuth(`${API_BASE}/system/servers/history?window=${window}`);
    if (!res.ok) throw new Error("Failed to fetch server historical telemetry");
    return res.json();
  },

  // =================== VERDICT INTELLIGENCE VALIDATION (AIS 2.1) ===================
  async evaluateIncidentTrust(req: {
    incident_id: string;
    rule_id?: string;
    policy_version_number?: number;
    allow_simulation?: boolean;
    custom_model_output?: any;
  }): Promise<VerdictTrustAssessmentResult> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/evaluate-incident-trust`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to evaluate incident trust" }));
      throw new Error(err.detail || "Failed to evaluate incident trust");
    }
    return res.json();
  },

  async getIncidentTrust(incidentId: string): Promise<VerdictTrustAssessmentResult | null> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/incident/${encodeURIComponent(incidentId)}/trust`);
    if (!res.ok) return null;
    return res.json();
  },

  async startHistoricalEvaluation(req: {
    run_name?: string;
    rule_id?: string;
    archetype?: string;
    dataset_filter?: string;
    sample_limit?: number;
    policy_version_id?: string;
    baseline_run_id?: string;
    provider_type?: string;
  }): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/dry-run/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to start historical evaluation" }));
      throw new Error(err.detail || "Failed to start historical evaluation");
    }
    return res.json();
  },

  async listEvaluationRuns(limit: number = 20): Promise<any[]> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/dry-run/runs?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to list evaluation runs");
    return res.json();
  },

  async getEvaluationRunDetails(runId: string): Promise<{ run: any; results: any[] }> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/dry-run/runs/${encodeURIComponent(runId)}`);
    if (!res.ok) throw new Error("Failed to fetch evaluation run details");
    return res.json();
  },

  async compareEvaluationRuns(baselineRunId: string, candidateRunId: string): Promise<RegressionComparisonReport> {
    const res = await fetchWithAuth(
      `${API_BASE}/verdict-intelligence/dry-run/compare?baseline_run_id=${encodeURIComponent(baselineRunId)}&candidate_run_id=${encodeURIComponent(candidateRunId)}`
    );
    if (!res.ok) throw new Error("Failed to compare evaluation runs");
    return res.json();
  },

  async getVerdictTrustOverview(): Promise<VerdictTrustOverviewResponse> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/metrics/summary`);
    if (!res.ok) throw new Error("Failed to fetch verdict trust overview");
    return res.json();
  },

  async getRuleWiseTrustworthiness(): Promise<RuleWiseTrustworthinessItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/verdict-intelligence/metrics/rule-wise`);
    if (!res.ok) throw new Error("Failed to fetch rule-wise trustworthiness metrics");
    return res.json();
  },

  async exportEvaluationReport(runId?: string, format: "json" | "csv" = "json"): Promise<{ blob: Blob; filename: string }> {
    const url = runId
      ? `${API_BASE}/verdict-intelligence/export?run_id=${encodeURIComponent(runId)}&format=${format}`
      : `${API_BASE}/verdict-intelligence/export?format=${format}`;
    const res = await fetchWithAuth(url);
    if (!res.ok) throw new Error("Failed to export evaluation report");
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition");
    let filename = `verdict_validation_${runId || "all"}.${format}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename };
  },
};

export interface DryRunConfig {
  id: string;
  name: string;
  description: string;
  rule_id?: string;
  rule_name?: string;
  prompt_version_id?: string;
  provider_type: string;
  split_strategy: string;
  dataset_filters: Record<string, any>;
  created_by_user_id?: string;
  created_at: string;
}

export interface DryRunJob {
  id: string;
  config_id: string;
  config_name?: string;
  status: string;
  total_items: number;
  processed_items: number;
  error_count: number;
  is_simulated: boolean;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

export interface DryRunResult {
  id: string;
  job_id: string;
  incident_id: string;
  incident_vendor_id?: string;
  incident_title?: string;
  rule_id?: string;
  rule_name?: string;
  predicted_verdict: string;
  confidence: number;
  reasoning: string;
  supporting_evidence: string[];
  missing_evidence: string[];
  analyst_questions: string[];
  latency_ms: number;
  model_identifier: string;
  prompt_version_number: number;
  validation_status: string;
  is_simulated: boolean;
  ground_truth_verdict?: string;
  is_agreement?: boolean;
  created_at: string;
}

export interface ConfusionMatrixData {
  true_positive_as_tp: number;
  true_positive_as_fp: number;
  true_positive_as_abstain: number;
  false_positive_as_fp: number;
  false_positive_as_tp: number;
  false_positive_as_abstain: number;
}

export interface EvaluationMetrics {
  job_id: string;
  job_status: string;
  is_simulated: boolean;
  total_evaluated: number;
  resolved_predictions: number;
  abstention_count: number;
  error_count: number;
  verdict_accuracy: number;
  tp_precision: number;
  tp_recall: number;
  fp_precision: number;
  fp_recall: number;
  f1_score: number;
  abstention_coverage: number;
  confusion_matrix: ConfusionMatrixData;
  rule_breakdown: Array<{
    rule_id: string;
    rule_name: string;
    total: number;
    tp_agree: number;
    fp_agree: number;
    tp_as_fp: number;
    fp_as_tp: number;
    abstains: number;
    accuracy: number;
    precision: number;
    coverage: number;
  }>;
  average_latency_ms: number;
  generated_at: string;
}

export interface PromptComparisonItem {
  prompt_version_number: number;
  prompt_version_id: string;
  is_template_draft: boolean;
  status: string;
  evaluated_cases: number;
  verdict_accuracy: number;
  tp_precision: number;
  fp_precision: number;
  coverage: number;
  average_latency_ms: number;
}

export interface RuleMaturity {
  id: string;
  rule_id: string;
  rule_name?: string;
  event_type?: string;
  maturity_status: "NOT_TESTED" | "LEARNING" | "UNDER_EVALUATION" | "CANDIDATE_FOR_AUTOMATION" | "APPROVED_FOR_AUTOMATION";
  precision_score: number;
  recall_score: number;
  f1_score: number;
  coverage_score: number;
  sample_size: number;
  unresolved_evidence_gaps: string[];
  recommendation_explanation: string;
  is_admin_approved: boolean;
  approved_by_username?: string;
  approved_at?: string;
  approval_notes: string;
  latest_test_date?: string;
}

export interface ServerMetricItem {
  server_id: string;
  server_name: string;
  timestamp: string;
  status: "ONLINE" | "OFFLINE" | "DEGRADED";
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent?: number | null;
  disk_used_gb?: number | null;
  disk_total_gb?: number | null;
  gpu_percent?: number | null;
  gpu_memory_percent?: number | null;
  gpu_memory_used_gb?: number | null;
  gpu_memory_total_gb?: number | null;
  gpu_temp_c?: number | null;
  latency_ms?: number | null;
  active_requests?: number;
  details?: Record<string, any>;
}

export interface ServersLiveResponse {
  timestamp: string;
  server_1: ServerMetricItem;
  server_2: ServerMetricItem;
  system_health: "OPTIMAL" | "ATTENTION_REQUIRED";
}

export interface ServerHistoryDataPoint {
  timestamp: string;
  time_label: string;
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent?: number | null;
  status: string;
  gpu_percent?: number | null;
  gpu_memory_percent?: number | null;
  gpu_memory_used_gb?: number | null;
  gpu_temp_c?: number | null;
  latency_ms?: number | null;
  active_requests: number;
}

export interface ServersHistoryResponse {
  window: "1h" | "6h" | "24h" | "7d";
  cutoff: string;
  server_1_series: ServerHistoryDataPoint[];
  server_2_series: ServerHistoryDataPoint[];
  stats: {
    server_1: {
      cpu: { avg: number; max: number; min: number };
      memory: { avg: number; max: number; min: number };
      samples_count: number;
    };
    server_2: {
      gpu: { avg: number; max: number; min: number };
      gpu_vram: { avg: number; max: number; min: number };
      latency: { avg: number; max: number; min: number };
      samples_count: number;
    };
  };
}

export interface TimelineMilestone {
  stage: string;
  type: string;
  title: string;
  timestamp: string;
  epoch_ms?: number;
  source: string;
  description: string;
  icon?: string;
  severity?: string;
  token_bifurcation?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    latency_ms: number;
    model: string;
  };
  metadata?: Record<string, any>;
}

export interface IncidentTimelineResponse {
  success: boolean;
  incident_id: string;
  title: string;
  storage_node: string;
  token_summary: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    records_count: number;
  };
  milestone_count: number;
  milestones: TimelineMilestone[];
}

export interface TokenProcessBifurcation {
  process_type: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  percentage_of_total: number;
  avg_latency_ms: number;
}

export interface TokenModelBifurcation {
  model_identifier: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  percentage_of_total: number;
}

export interface TokenLedgerItem {
  id: string;
  process_type: string;
  process_id?: string;
  incident_id?: string;
  rule_id?: string;
  model_identifier: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  is_simulated: boolean;
  executed_by_user: string;
  timestamp: string;
  details?: Record<string, any>;
}

export interface TokenAnalyticsResponse {
  window_days: number;
  cutoff_timestamp: string;
  storage_location: string;
  totals: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    prompt_percentage: number;
    completion_percentage: number;
    total_calls: number;
    avg_latency_ms: number;
  };
  by_process: TokenProcessBifurcation[];
  by_model: TokenModelBifurcation[];
  recent_ledger: TokenLedgerItem[];
}

export interface GlobalTelemetryTimelineResponse {
  success: boolean;
  storage_node: string;
  total_records: number;
  timeline: Array<{
    id: string;
    incident_id?: string;
    event_type: string;
    stage: string;
    summary: string;
    source: string;
    severity: string;
    source_ip?: string;
    reporting_device?: string;
    epoch_ms?: number;
    token_count: number;
    timestamp: string;
    details?: Record<string, any>;
  }>;
}

export interface TrustScoreDimensionBreakdown {
  direct_claim_support: number;
  source_reliability: number;
  contradiction_handling: number;
  independent_corroboration: number;
  historical_validation_support: number;
  total_raw_score: number;
}

export interface VerdictTrustAssessmentResult {
  incident_id: string;
  rule_id: string;
  archetype: string;
  suggested_verdict: string;
  effective_verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ANALYST_ATTENTION";
  trust_score?: number | null;
  raw_trust_score: number;
  evidence_sufficiency_score: number;
  evidence_status: "SUFFICIENT" | "INSUFFICIENT" | "CONFLICTING" | "UNCALIBRATED";
  score_dimensions: TrustScoreDimensionBreakdown;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  missing_evidence: string[];
  confidence_limitations: string[];
  historical_validation_status: string;
  is_calibrated: boolean;
  calibrated_probability?: number | null;
  applicable_policy_version?: number | null;
  applicable_contract_version?: string | null;
  escalation_reason?: string | null;
  human_readable_explanation: string;
  model_identifier: string;
  is_simulated: boolean;
  evaluated_at: string;
}

export interface VerdictTrustOverviewResponse {
  total_evaluated_incidents: number;
  true_positive_recommendations: number;
  false_positive_recommendations: number;
  analyst_attention_decisions: number;
  average_trust_score: number;
  average_sufficiency_score: number;
  trust_score_distribution: Record<string, number>;
  low_trust_verdicts_count: number;
  missing_evidence_count: number;
  conflicting_evidence_count: number;
}

export interface RuleWiseTrustworthinessItem {
  rule_id: string;
  rule_name: string;
  archetype: string;
  incident_count: number;
  average_trust_score?: number | null;
  evidence_sufficiency?: number | null;
  measured_accuracy?: number | null;
  tp_recall?: number | null;
  fp_specificity?: number | null;
  abstention_rate?: number | null;
  validation_status: string;
}

export interface CaseRegressionDetail {
  incident_id: string;
  rule_id: string;
  ground_truth: string;
  baseline_verdict: string;
  candidate_verdict: string;
  baseline_trust?: number | null;
  candidate_trust?: number | null;
  regression_type: string;
  reason: string;
}

export interface RegressionComparisonReport {
  rule_id?: string | null;
  baseline_run_id: string;
  candidate_run_id: string;
  validation_state: "VALIDATED" | "REGRESSION_DETECTED" | "INCONCLUSIVE" | "INSUFFICIENT_DATA" | "EVALUATION_FAILED";
  sample_count: number;
  baseline_accuracy?: number | null;
  candidate_accuracy?: number | null;
  accuracy_delta?: number | null;
  baseline_coverage: number;
  candidate_coverage: number;
  coverage_delta: number;
  baseline_recall?: number | null;
  candidate_recall?: number | null;
  recall_delta?: number | null;
  baseline_specificity?: number | null;
  candidate_specificity?: number | null;
  specificity_delta?: number | null;
  critical_regressions_count: number;
  statistically_significant: boolean;
  p_value_estimate?: number | null;
  regressed_cases: CaseRegressionDetail[];
  improved_cases: CaseRegressionDetail[];
  summary_message: string;
}




