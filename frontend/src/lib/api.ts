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
  created_at: string;
  updated_at: string;
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
};
