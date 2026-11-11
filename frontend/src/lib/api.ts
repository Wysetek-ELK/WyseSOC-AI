// API Client for Verdictum AI Frontend

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
  execution_provenance?: string;
  configured_provider?: string;
  test_environment?: string | null;
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
  proposal_validation_outcome?: string;
  final_disposition?: string;
  abstention_reason?: string | null;
  trust_score?: number | null;
  historical_trust_score?: number | null;
  trust_cap_applied?: boolean;
  trust_cap_reason?: string | null;
  trust_status?: string;
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
  rule_uuid?: string;
  logical_rule_id?: string;
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
  cleared_reason?: string;
  cleared_user?: string;
  cleared_time_epoch?: number;
  ai_verdict?: IncidentAiVerdictResponse | null;
  event_count: number;
  created_at: string;
}

export interface IncidentMatchedRuleSummary {
  rule_uuid?: string | null;
  logical_rule_id: string;
  rule_name?: string | null;
  event_type?: string | null;
  incident_count: number;
}

export interface IncidentListResponse {
  items: IncidentListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  exact_rule_id?: string | null;
  exact_logical_rule_id?: string | null;
  exact_rule_name?: string | null;
  distinct_rule_count?: number;
  combines_multiple_rules?: boolean;
  matched_rules?: IncidentMatchedRuleSummary[];
}

export interface IncidentDetail {
  id: string;
  incident_id: string;
  rule_id?: string;
  rule_uuid?: string;
  logical_rule_id?: string;
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
  resolution?: string;
  cleared_reason?: string;
  cleared_user?: string;
  cleared_time_epoch?: number;
  resolution_updated?: boolean;
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
  resolutions_updated?: number;
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

export interface FortiSIEMSyncResolutionsResponse {
  success: boolean;
  total_incidents_checked: number;
  resolutions_updated: number;
  total_with_resolution: number;
  message: string;
}

export interface FortiSIEMSingleSyncResponse {
  success: boolean;
  incident_id: string;
  db_id: string;
  status_name: string;
  status_code: number;
  resolution: string;
  cleared_reason: string;
  cleared_user: string;
  cleared_time_epoch?: number;
  comments: string;
  is_ml_generated: boolean;
  updated: boolean;
  source: string;
  message: string;
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

export interface AIAssuranceSummary {
  incident_summary: string;
  rule_id?: string | null;
  rule_name?: string | null;
  policy_version_number?: number | null;
  policy_digest?: string | null;
  proposed_verdict?: string | null;
  validated_verdict?: string | null;
  validation_status?: string | null;
  abstention_reason?: string | null;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  missing_evidence: string[];
  trust_score?: number | null;
  historical_trust_score?: number | null;
  trust_cap_applied?: boolean;
  is_calibrated: boolean;
  calibration_status: string;
  historical_sample_count: number;
  historical_validation_status: string;
  model_identifier?: string | null;
  is_simulated: boolean;
  configured_provider?: string | null;
  execution_provenance?: string | null;
  historical_execution_provenance?: string | null;
  current_s2_health?: string | null;
  test_environment?: string | null;
  pilot_evaluation_id?: string | null;
  pilot_mode?: string | null;
  evaluated_at?: string | null;
  analyst_feedback_action?: string | null;
  supervisor_verified: boolean;
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
  ai_validated_verdict?: string | null;
  ai_trust_score?: number | null;
  pilot_mode?: string | null;
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
  ai_assurance?: AIAssuranceSummary | null;
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
  scoring_model_version?: string;
  scoring_denominator?: number;
  structural_denominator?: number;
  structural_raw_score?: number | null;
  empirical_denominator?: number;
  quality_score: number;
  structural_quality_score?: number;
  empirical_validation_score?: number;
  empirical_validation_status?: string;
  validation_status: string;
  gate_scores_total?: number;
  gate_max_total?: number;
  score_breakdown: Record<string, number>;
  gate_results: Record<string, QualityGateResult>;
  gates?: QualityGateResult[];
  blocking_issues: string[];
  blocking_findings?: string[];
  warnings: string[];
  missing_evidence_mappings: string[];
  recommendations: string[];
  simulation_status: string;
  simulation_run_id?: string | null;
  simulation_provider_type?: string | null;
  simulation_model_identifier?: string | null;
  simulation_execution_provenance?: string | null;
  simulation_is_simulated?: boolean | null;
  simulation_sample_count?: number | null;
  simulation_verified_cases?: number | null;
  simulation_policy_digest?: string | null;
  approval_eligible: boolean;
  structural_approval_eligible?: boolean;
  empirical_validation_eligible?: boolean;
  autonomous_operation_eligible?: boolean;
  hard_gate_failure?: boolean;
  historical_assessment_preserved?: boolean;
  persisted_validator_version?: string | null;
  persisted_quality_score?: number | null;
  policy_digest: string;
  contract_digest: string;
  rule_digest: string;
  archetype_version: string;
  evaluated_at: string;
}

export interface PolicySimulationResult {
  status: string;
  simulation_status: string;
  sample_count: number;
  evaluated_cases?: number;
  total_scanned?: number;
  rule_matched?: number;
  analyst_labeled?: number;
  eligible_ground_truth_count?: number;
  verified_ground_truth_cases?: number;
  excluded_count?: number;
  exclusion_reasons?: Record<string, number>;
  exclusions_detail?: Array<{ incident_id: string; reason: string; detail: string; rule_id?: string }>;
  stage_details?: {
    scanned?: Array<{ incident_id: string; rule_id?: string; status: string; reason?: string | null; detail?: string }>;
    rule_matched?: Array<{ incident_id: string; rule_id?: string; has_analyst_label?: boolean; resolution?: string | null }>;
    analyst_labeled?: Array<{ incident_id: string; rule_id?: string; resolution: string; comments?: string; is_ml_generated?: boolean }>;
    eligible?: Array<{ incident_id: string; rule_id?: string; ground_truth: string; resolution?: string; comments?: string }>;
    excluded?: Array<{ incident_id: string; rule_id?: string; reason: string; detail: string }>;
    evaluated?: Array<any>;
  };
  funnel?: {
    available?: number;
    retrieved?: number;
    total_scanned: number;
    rule_matched: number;
    labeled?: number;
    analyst_labeled: number;
    verified?: number;
    eligible: number;
    excluded: number;
    inferred?: number;
    evaluated: number;
    scored?: number;
    exploratory_replay_count?: number;
    exclusion_reasons: Record<string, number>;
  };
  available_count?: number;
  retrieved_count?: number;
  verified_count?: number;
  inferred_count?: number;
  scored_count?: number;
  exploratory_replay_count?: number;
  provider_type?: string;
  is_simulated?: boolean;
  execution_provenance?: string;
  model_identifier?: string | null;
  certifying_empirical_eligible?: boolean;
  token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  min_samples_required: number;
  message: string;
  critical_regressions: number;
  regression_detected: boolean;
  regression_status: "PASS" | "REGRESSION_DETECTED" | "INSUFFICIENT_DATA" | "NOT_ASSESSED";
  empirical_validation_status:
    | "EVALUATED_PASSED"
    | "EVALUATED_FAILED"
    | "INSUFFICIENT_DATA"
    | "INCONCLUSIVE"
    | "SIMULATED_ONLY_NOT_CERTIFYING";
  abstention_rate?: number | null;
  balanced_accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  specificity?: number | null;
  false_positive_rate?: number | null;
  false_negative_rate?: number | null;
  decision_coverage?: number | null;
  overall_accuracy?: number | null;
  confusion_matrix?: {
    tp: number;
    fp: number;
    tn: number;
    fn: number;
    abstained: number;
  };
  ground_truth_distribution?: {
    tp: number;
    fp: number;
    unverified: number;
  };
  run_id?: string;
  is_calibrated: boolean;
  calibration_status: string;
  brier_score?: number | null;
  ece?: number | null;
  candidate_metrics?: any;
  baseline_metrics?: any;
  regressed_cases?: any[];
  improved_cases?: any[];
  per_incident_results?: Array<{
    incident_id: string;
    rule_id: string;
    ground_truth?: string | null;
    suggested_verdict: string;
    effective_verdict: string;
    trust_score?: number | null;
    raw_trust_score: number;
    evidence_status: string;
    is_correct?: boolean | null;
    is_abstained: boolean;
    is_critical_error?: boolean;
    escalation_reason?: string | null;
  }>;
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

async function parseChatHttpError(res: Response): Promise<string> {
  const text = await res.text().catch(() => "");
  let detail = `Chatbot request failed (HTTP ${res.status})`;
  try {
    const parsed = JSON.parse(text);
    if (parsed?.detail) return parsed.detail;
  } catch {
    if (res.status === 504) {
      return "Gateway Timeout (504): Reverse proxy or Server 2 timed out waiting for LLM response.";
    }
  }
  return detail;
}

interface ChatStreamDoneEvent {
  type: "done";
  model?: string;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  attached_incident_id?: string | null;
  server_url?: string;
  timestamp?: string;
}

type ChatStreamEvent =
  | { type: "delta"; content?: string }
  | { type: "error"; status_code?: number; detail?: string }
  | ChatStreamDoneEvent;

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
    configured_provider?: string;
    endpoint_provenance?: string;
    current_s2_health?: string;
    gpu_telemetry_verified?: boolean;
    test_environment?: string | null;
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
    exact_rule_id?: string;
    resolution?: string;
    blind_review?: boolean;
  } = {}): Promise<IncidentListResponse> {
    const q = new URLSearchParams();
    if (params.page) q.set("page", params.page.toString());
    if (params.page_size) q.set("page_size", params.page_size.toString());
    if (params.search) q.set("search", params.search);
    if (params.severity) q.set("severity", params.severity);
    if (params.status) q.set("status", params.status);
    if (params.rule_id) q.set("rule_id", params.rule_id);
    if (params.exact_rule_id) q.set("exact_rule_id", params.exact_rule_id);
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

  async processPendingFortiSiemVerdicts(
    max_count: number = 100,
    background: boolean = false
  ): Promise<{
    success?: boolean;
    is_llm_online?: boolean;
    started?: boolean;
    already_running?: boolean;
    processed?: number;
    failed?: number;
    pending_remaining?: number;
    message?: string;
  }> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/process-pending-verdicts?max_count=${max_count}&background=${background}`, {
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

  async syncFortiSiemResolutions(): Promise<FortiSIEMSyncResolutionsResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/sync-resolutions`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to sync resolutions from FortiSIEM" }));
      throw new Error(err.detail || "Resolution sync error");
    }
    return res.json();
  },

  async syncFortiSiemIncidentResolution(incidentId: string): Promise<FortiSIEMSingleSyncResponse> {
    const res = await fetchWithAuth(`${API_BASE}/fortisiem/incident/${encodeURIComponent(incidentId)}/sync-resolution`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Failed to sync resolution for incident '${incidentId}'` }));
      throw new Error(err.detail || "Single incident resolution sync error");
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
    action_type?: string;
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

  async previewPolicyQuality(ruleId: string, versionId?: string): Promise<PolicyQualityAssessmentResponse> {
    const url = versionId
      ? `${API_BASE}/prompts/rule/${ruleId}/quality-preview?version_id=${versionId}`
      : `${API_BASE}/prompts/rule/${ruleId}/quality-preview`;
    const res = await fetchWithAuth(url);
    if (!res.ok) throw new Error("Failed to load read-only policy quality preview");
    return res.json();
  },

  async validatePolicyQuality(ruleId: string, versionId?: string): Promise<PolicyQualityAssessmentResponse> {
    const url = versionId ? `${API_BASE}/prompts/rule/${ruleId}/validate-quality?version_id=${versionId}` : `${API_BASE}/prompts/rule/${ruleId}/validate-quality`;
    const res = await fetchWithAuth(url, { method: "POST" });
    if (!res.ok) throw new Error("Failed to validate policy quality");
    return res.json();
  },

  async evaluatePolicySimulation(
    ruleId: string,
    versionId?: string,
    options?: {
      provider_type?: "OPENAI_COMPATIBLE" | "SIMULATED";
      sample_limit?: number;
      include_unlabeled_replay?: boolean;
      async_execution?: boolean;
    }
  ): Promise<PolicySimulationResult> {
    const params = new URLSearchParams();
    if (versionId) params.set("version_id", versionId);
    if (options?.provider_type) params.set("provider_type", options.provider_type);
    if (options?.sample_limit !== undefined) params.set("sample_limit", String(options.sample_limit));
    if (options?.include_unlabeled_replay !== undefined) {
      params.set("include_unlabeled_replay", String(options.include_unlabeled_replay));
    }
    if (options?.async_execution !== undefined) {
      params.set("async_execution", String(options.async_execution));
    }
    const qs = params.toString();
    const url = qs
      ? `${API_BASE}/prompts/rule/${ruleId}/evaluate-simulation?${qs}`
      : `${API_BASE}/prompts/rule/${ruleId}/evaluate-simulation`;
    const res = await fetchWithAuth(url, { method: "POST" });
    if (!res.ok) {
      let msg = "Failed to evaluate policy simulation";
      try {
        const body = await res.json();
        if (body && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        }
      } catch (_) {}
      throw new Error(msg);
    }
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

  // =================== SOC AI CHATBOT (LOCAL LLM SERVER 2) ===================
  async getChatStatus(): Promise<ChatStatusResponse> {
    const res = await fetchWithAuth(`${API_BASE}/chat/status`);
    if (!res.ok) throw new Error("Failed to check Server 2 Chatbot status");
    return res.json();
  },

  async sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
    const res = await fetchWithAuth(`${API_BASE}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(await parseChatHttpError(res));
    }
    return res.json();
  },

  async streamChatMessage(
    req: ChatRequest,
    callbacks: {
      onDelta: (chunk: string) => void;
    }
  ): Promise<ChatResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 300_000);
    try {
      const res = await fetchWithAuth(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      // Fallback cleanly if streaming endpoint is not available (e.g. older backend instance)
      if (res.status === 404 || res.status === 405) {
        return this.sendChatMessage(req);
      }

      if (!res.ok || !res.body) {
        throw new Error(await parseChatHttpError(res));
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";
      const metaHolder: { done: ChatStreamDoneEvent | null } = { done: null };

      const processLine = (rawLine: string) => {
        const line = rawLine.trim();
        if (!line || line.startsWith(":") || !line.startsWith("data:")) return;
        const jsonPart = line.slice(5).trim();
        if (!jsonPart || jsonPart === "[DONE]") return;
        let evt: ChatStreamEvent;
        try {
          evt = JSON.parse(jsonPart) as ChatStreamEvent;
        } catch {
          return;
        }
        if (evt.type === "delta" && typeof evt.content === "string") {
          accumulated += evt.content;
          callbacks.onDelta(evt.content);
        } else if (evt.type === "error") {
          throw new Error(evt.detail || "Server 2 LLM stream error");
        } else if (evt.type === "done") {
          metaHolder.done = evt;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const l of lines) {
          processLine(l);
        }
      }
      if (buffer.trim()) {
        processLine(buffer);
      }

      const doneMeta = metaHolder.done;
      return {
        message: {
          role: "assistant",
          content: accumulated,
          timestamp: doneMeta?.timestamp || new Date().toISOString(),
        },
        model: doneMeta?.model || "local-llm",
        latency_ms: doneMeta?.latency_ms || 0,
        prompt_tokens: doneMeta?.prompt_tokens || 0,
        completion_tokens: doneMeta?.completion_tokens || 0,
        total_tokens: doneMeta?.total_tokens || 0,
        attached_incident_id: doneMeta?.attached_incident_id ?? undefined,
        server_url: doneMeta?.server_url || "",
        is_simulated: false,
      };
    } finally {
      clearTimeout(timer);
    }
  },

  // =================== PHASE 9: CONTROLLED SOC PILOT & ELIGIBILITY ===================
  async getPilotConfig(): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/config`);
    if (!res.ok) throw new Error("Failed to load pilot configuration");
    return res.json();
  },

  async updatePilotConfig(payload: Record<string, any>): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update pilot configuration" }));
      throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
    }
    return res.json();
  },

  async activatePilot(mode: "SHADOW" | "ANALYST_ASSISTED" | "DISABLED", change_reason: string): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, change_reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to activate pilot" }));
      throw new Error(err.detail || "Failed to activate pilot");
    }
    return res.json();
  },

  async pausePilot(reason: string): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/pause`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to pause pilot" }));
      throw new Error(err.detail || "Failed to pause pilot");
    }
    return res.json();
  },

  async resumePilot(reason: string): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to resume pilot" }));
      throw new Error(err.detail || "Failed to resume pilot");
    }
    return res.json();
  },

  async disablePilot(reason: string): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/disable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to disable pilot" }));
      throw new Error(err.detail || "Failed to disable pilot");
    }
    return res.json();
  },

  async rollbackPilot(target_version: number, reason: string): Promise<PilotConfig> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/rollback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_version, reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to roll back pilot" }));
      throw new Error(err.detail || "Failed to roll back pilot");
    }
    return res.json();
  },

  async getPilotMetrics(): Promise<PilotMetricsResponse> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/metrics`);
    if (!res.ok) throw new Error("Failed to load pilot metrics");
    return res.json();
  },

  async getPilotHistory(): Promise<PilotConfigHistoryItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/history`);
    if (!res.ok) throw new Error("Failed to load pilot history");
    return res.json();
  },

  async getPilotAuditLogs(): Promise<{ items: any[]; total: number }> {
    const res = await fetchWithAuth(`${API_BASE}/pilot/audit`);
    if (!res.ok) throw new Error("Failed to load pilot audit logs");
    return res.json();
  },

  async getPilotEvaluations(mode?: string, includeSimulated: boolean = true): Promise<PilotEvaluationItem[]> {
    const q = new URLSearchParams();
    if (mode) q.set("mode", mode);
    q.set("include_simulated", String(includeSimulated));
    const res = await fetchWithAuth(`${API_BASE}/pilot/evaluations?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to load pilot evaluations");
    return res.json();
  },

  async runPilotBatch(payload: { incident_ids?: string[]; max_batch?: number; source_type?: "LIVE" | "HISTORICAL"; allow_simulated?: boolean }) {
    const res = await fetchWithAuth(`${API_BASE}/pilot/run-batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to run pilot batch" }));
      throw new Error(err.detail || "Failed to run pilot batch");
    }
    return res.json();
  },

  async submitPilotFeedback(evaluationId: string, payload: { action: string; analyst_decision: string; reason: string }) {
    const res = await fetchWithAuth(`${API_BASE}/pilot/evaluations/${encodeURIComponent(evaluationId)}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to submit pilot feedback" }));
      throw new Error(err.detail || "Failed to submit pilot feedback");
    }
    return res.json();
  },

  async supervisorVerifyPilotFeedback(evaluationId: string, payload: { approved: boolean; notes?: string }) {
    const res = await fetchWithAuth(`${API_BASE}/pilot/evaluations/${encodeURIComponent(evaluationId)}/supervisor-verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to verify pilot feedback" }));
      throw new Error(err.detail || "Failed to verify pilot feedback");
    }
    return res.json();
  },

  async getHistoricalEligibilityReport(ruleId?: string): Promise<HistoricalEligibilityReport> {
    const url = ruleId
      ? `${API_BASE}/verdict-intelligence/eligibility-report?rule_id=${encodeURIComponent(ruleId)}`
      : `${API_BASE}/verdict-intelligence/eligibility-report`;
    const res = await fetchWithAuth(url);
    if (!res.ok) throw new Error("Failed to load historical eligibility report");
    return res.json();
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
  historical_trust_score?: number | null;
  trust_cap_applied?: boolean;
  trust_cap_reason?: string | null;
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
  average_trust_score?: number | null;
  average_sufficiency_score?: number | null;
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

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  incident_id?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  model: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  attached_incident_id?: string;
  server_url: string;
  is_simulated: boolean;
}

export interface ChatStatusResponse {
  is_online: boolean;
  host: string;
  port: number;
  protocol: string;
  base_url: string;
  model_name: string;
  available_models: string[];
  latency_ms?: number | null;
  status_message: string;
  configured_provider?: string;
  endpoint_provenance?: string;
  current_s2_health?: string;
  gpu_telemetry_verified?: boolean;
  test_environment?: string | null;
}

export interface PilotConfig {
  id: string;
  pilot_name: string;
  description: string;
  version_number: number;
  mode: "DISABLED" | "SHADOW" | "ANALYST_ASSISTED";
  is_paused: boolean;
  selected_rule_ids: string[];
  selected_archetypes: string[];
  included_severities: string[];
  ingestion_source: "ALL" | "LIVE" | "HISTORICAL";
  daily_evaluation_budget: number;
  hourly_evaluation_budget: number;
  max_concurrent_inference: number;
  request_timeout_seconds: number;
  require_analyst_review: boolean;
  require_approved_policy: boolean;
  allow_external_writeback: boolean;
  allow_auto_incident_closure: boolean;
  error_handling_policy: string;
  consecutive_error_pause_threshold: number;
  reporting_schedule: string;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface PilotConfigHistoryItem {
  id: string;
  pilot_id: string;
  version_number: number;
  action: string;
  mode: string;
  is_paused: boolean;
  config_snapshot: Record<string, any>;
  change_reason: string;
  changed_by: string;
  changed_at: string;
}

export interface PilotEvaluationItem {
  id: string;
  pilot_id: string;
  pilot_version: number;
  incident_id: string;
  incident_db_id?: string | null;
  rule_id: string;
  archetype: string;
  severity: string;
  execution_mode: string;
  source_type: string;
  eligibility_status: string;
  proposed_verdict?: string | null;
  validated_verdict?: string | null;
  validation_status?: string | null;
  abstention_reason?: string | null;
  trust_score?: number | null;
  historical_trust_score?: number | null;
  raw_trust_score?: number | null;
  is_calibrated: boolean;
  evidence_completeness?: number | null;
  grounding_ratio?: number | null;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  missing_evidence: string[];
  policy_version_id?: string | null;
  policy_version_number?: number | null;
  policy_digest?: string | null;
  model_identifier: string;
  is_simulated: boolean;
  configured_provider?: string;
  execution_provenance?: string;
  historical_execution_provenance?: string | null;
  test_environment?: string | null;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  evidence_snapshot_hash?: string | null;
  error_message?: string | null;
  analyst_feedback_action?: string | null;
  analyst_decision?: string | null;
  analyst_override_reason?: string | null;
  analyst_user?: string | null;
  analyst_decided_at?: string | null;
  supervisor_verified: boolean;
  supervisor_user?: string | null;
  supervisor_verified_at?: string | null;
  created_at: string;
}

export interface PilotMetricsResponse {
  pilot: PilotConfig;
  population_notice: string;
  operational: {
    total_incidents_received: number;
    eligible_pilot_incidents: number;
    incidents_evaluated: number;
    simulated_evaluations_excluded_count: number;
    pending_incidents: number;
    tp_recommendations: number;
    fp_recommendations: number;
    requires_attention: number;
    inference_failures: number;
    avg_latency_ms?: number | null;
    p50_latency_ms?: number | null;
    p95_latency_ms?: number | null;
    token_consumption_live: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
    token_consumption_simulated_isolated: { total_tokens: number };
    hourly_budget_used: number;
    hourly_budget_limit: number;
    daily_budget_used: number;
    daily_budget_limit: number;
    queue_backlog: number;
    provider_available: boolean;
    configured_provider?: string;
    endpoint_provenance?: string;
    current_s2_health?: string;
    gpu_telemetry_verified?: boolean;
    test_environment?: string | null;
    live_provider_evaluations_count?: number;
    http_mock_evaluations_count?: number;
    historical_evaluations_count?: number;
    guard_abstention_evaluations_count?: number;
    circuit_breaker_state: string;
  };
  reliability: {
    sample_size: number;
    guardrail_acceptance_rate?: number | null;
    unsupported_claim_rate?: number | null;
    contradiction_rate?: number | null;
    evidence_completeness_avg?: number | null;
    abstention_rate?: number | null;
    analyst_reviewed_count: number;
    analyst_disagreement_rate?: number | null;
    policy_failure_distribution: Record<string, number>;
  };
  empirical_accuracy: {
    verified_tp_cases: number;
    verified_fp_cases: number;
    verified_total_cases: number;
    tp_precision?: number | null;
    tp_recall?: number | null;
    fp_specificity?: number | null;
    balanced_accuracy?: number | null;
    selective_accuracy?: number | null;
    decision_coverage?: number | null;
    false_negatives: number;
    metric_status: string;
    balanced_accuracy_reason: string;
    calibration_status: string;
    is_calibrated: boolean;
    trust_scale_label: string;
  };
}

export interface HistoricalEligibilityReport {
  generated_at: string;
  rule_filter?: string | null;
  integrity_notice: string;
  summary: {
    available_incident_count: number;
    verified_tp_count: number;
    verified_fp_count: number;
    disputed_count: number;
    insufficient_evidence_count: number;
    unverified_or_ml_count: number;
    synthetic_count: number;
    duplicate_group_count: number;
    eligible_independent_count: number;
    g8_eligibility: string;
    calibration_eligibility: string;
    holdout_partitions: Record<string, number>;
    time_window: { earliest_epoch?: number | null; latest_epoch?: number | null };
    missing_evidence_fields: Array<{ field: string; missing_count: number }>;
  };
  rules: Array<{
    rule_uuid: string;
    rule_id: string;
    rule_name: string;
    available_incident_count: number;
    verified_tp_count: number;
    verified_fp_count: number;
    disputed_count: number;
    insufficient_evidence_count: number;
    unverified_or_ml_count: number;
    synthetic_count: number;
    duplicate_group_count: number;
    duplicate_excluded_count: number;
    eligible_independent_count: number;
    missing_evidence_fields: Array<{ field: string; missing_count: number }>;
    g8_eligibility: string;
    calibration_eligibility: string;
    holdout_partitions: Record<string, number>;
  }>;
}





