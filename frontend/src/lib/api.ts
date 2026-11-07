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
  confidence: number;
  reason: string;
  supporting_evidence: string[];
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

export interface DashboardMetrics {
  total_incidents: number;
  total_rules: number;
  historical_true_positives: number;
  historical_false_positives: number;
  unresolved_incidents: number;
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
    if (!res.ok) throw new Error("Failed to approve prompt version");
    return res.json();
  },

  async rollbackPromptVersion(ruleId: string, versionId: string): Promise<PromptVersion> {
    const res = await fetchWithAuth(`${API_BASE}/prompts/rule/${ruleId}/rollback/${versionId}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to rollback prompt version");
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


