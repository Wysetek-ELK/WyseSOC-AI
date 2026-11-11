"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  Shield,
  Database,
  Cpu,
  Lock,
  Sliders,
  Server,
  Zap,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  RefreshCw,
  Save,
  Globe,
  Radio,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import {
  api,
  FortiSIEMConfigResponse,
  FortiSIEMTestConnectionResponse,
  LLMConfigResponse,
  LLMTestConnectionResponse,
} from "@/lib/api";

export default function AgentConfigurationPage() {
  const { blindReviewMode, setBlindReviewMode, theme, toggleTheme, user } = useApp();

  // FortiSIEM Configuration States
  const [host, setHost] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [verifySsl, setVerifySsl] = useState(false);
  const [timeout, setTimeoutSec] = useState(25);
  const [mockFallback, setMockFallback] = useState(true);
  const [isPasswordSet, setIsPasswordSet] = useState(false);
  const [isConfigured, setIsConfigured] = useState(false);

  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [testResult, setTestResult] = useState<FortiSIEMTestConnectionResponse | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Local LLM Server 2 States
  const [llmHost, setLlmHost] = useState("");
  const [llmPort, setLlmPort] = useState(8000);
  const [llmProtocol, setLlmProtocol] = useState("http");
  const [llmModelName, setLlmModelName] = useState("Qwen/Qwen2.5-7B-Instruct-AWQ");
  const [llmTimeout, setLlmTimeout] = useState(60);
  const [llmAllowMockFallback, setLlmAllowMockFallback] = useState(true);
  const [llmBaseUrl, setLlmBaseUrl] = useState("");
  const [llmIsOnline, setLlmIsOnline] = useState(false);
  const [server1OutboundIp, setServer1OutboundIp] = useState<string | null>(null);

  const [isLoadingLLM, setIsLoadingLLM] = useState(true);
  const [isSavingLLM, setIsSavingLLM] = useState(false);
  const [isTestingLLM, setIsTestingLLM] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<LLMTestConnectionResponse | null>(null);
  const [llmSaveSuccess, setLlmSaveSuccess] = useState<string | null>(null);
  const [llmSaveError, setLlmSaveError] = useState<string | null>(null);

  const loadFortiSiemConfig = async () => {
    setIsLoadingConfig(true);
    try {
      const cfg = await api.getFortiSiemConfig();
      setHost(cfg.host || "");
      setUsername(cfg.username || "");
      setIsPasswordSet(cfg.is_password_set);
      setVerifySsl(cfg.verify_ssl);
      setTimeoutSec(cfg.timeout || 25);
      setMockFallback(cfg.mock_fallback);
      setIsConfigured(cfg.is_configured);
    } catch (err) {
      console.error("Failed to load FortiSIEM configuration", err);
    } finally {
      setIsLoadingConfig(false);
    }
  };

  const loadLLMConfig = async () => {
    setIsLoadingLLM(true);
    try {
      const cfg = await api.getLLMConfig();
      setLlmHost(cfg.host || "");
      setLlmPort(cfg.port || 8000);
      setLlmProtocol(cfg.protocol || "http");
      setLlmModelName(cfg.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ");
      setLlmTimeout(cfg.timeout || 30);
      setLlmAllowMockFallback(cfg.allow_mock_fallback);
      setLlmBaseUrl(cfg.base_url || "");
      setLlmIsOnline(cfg.is_online);
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("llm-status-change", {
            detail: {
              is_healthy: Boolean(cfg.is_online),
              model: cfg.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ",
            },
          })
        );
      }
      if (cfg.server1_outbound_ip) {
        setServer1OutboundIp(cfg.server1_outbound_ip);
      }
    } catch (err) {
      console.error("Failed to load LLM configuration", err);
    } finally {
      setIsLoadingLLM(false);
    }
  };

  useEffect(() => {
    loadFortiSiemConfig();
    loadLLMConfig();
  }, []);

  const handleTestLLMConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!llmHost.trim()) {
      setLlmSaveError("LLM Server IP address or hostname is required to test connection.");
      return;
    }

    setIsTestingLLM(true);
    setLlmTestResult(null);
    setLlmSaveError(null);
    setLlmSaveSuccess(null);

    try {
      const res = await api.testLLMConnection({
        host: llmHost.trim(),
        port: llmPort,
        protocol: llmProtocol,
        timeout: 5,
      });
      setLlmTestResult(res);
      if (res.success) {
        setLlmIsOnline(true);
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("llm-status-change", {
              detail: {
                is_healthy: true,
                model: (res.models && res.models[0]) || llmModelName,
              },
            })
          );
        }
      }
    } catch (err: any) {
      setLlmTestResult({
        success: false,
        message: err.message || "Failed to reach LLM Server 2",
        models: [],
        tested_url: `${llmProtocol}://${llmHost.trim()}:${llmPort}/v1/models`,
      });
    } finally {
      setIsTestingLLM(false);
    }
  };

  const handleSaveLLMConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!llmHost.trim()) {
      setLlmSaveError("LLM Server IP address or hostname is required.");
      return;
    }

    setIsSavingLLM(true);
    setLlmSaveError(null);
    setLlmSaveSuccess(null);

    try {
      const updated = await api.updateLLMConfig({
        host: llmHost.trim(),
        port: llmPort,
        protocol: llmProtocol,
        model_name: llmModelName.trim(),
        timeout: llmTimeout,
        allow_mock_fallback: llmAllowMockFallback,
      });
      setLlmHost(updated.host);
      setLlmPort(updated.port);
      setLlmProtocol(updated.protocol);
      setLlmBaseUrl(updated.base_url);
      setLlmModelName(updated.model_name);
      setLlmTimeout(updated.timeout);
      setLlmAllowMockFallback(updated.allow_mock_fallback);
      setLlmSaveSuccess(`LLM Server configuration saved! Target base URL updated to ${updated.base_url}`);
      setLlmTestResult(null);
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("llm-status-change", {
            detail: {
              is_healthy: Boolean(updated.is_online),
              model: updated.model_name,
            },
          })
        );
      }
    } catch (err: any) {
      setLlmSaveError(err.message || "Failed to save LLM configuration.");
    } finally {
      setIsSavingLLM(false);
    }
  };

  const handleTestConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!host.trim() || !username.trim()) {
      setSaveError("Host URL and Username are required to test connection.");
      return;
    }

    setIsTesting(true);
    setTestResult(null);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const res = await api.testFortiSiemConnection({
        host: host.trim(),
        username: username.trim(),
        password: password.trim() ? password.trim() : undefined,
        verify_ssl: verifySsl,
        timeout,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Failed to reach FortiSIEM Supervisor",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!host.trim() || !username.trim()) {
      setSaveError("Host URL and Username are required.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const updated = await api.updateFortiSiemConfig({
        host: host.trim(),
        username: username.trim(),
        password: password.trim() ? password.trim() : undefined,
        verify_ssl: verifySsl,
        timeout,
        mock_fallback: mockFallback,
      });
      setIsPasswordSet(updated.is_password_set);
      setIsConfigured(updated.is_configured);
      setPassword(""); // Clear input after successful save
      setSaveSuccess("FortiSIEM configuration and credentials saved successfully!");
      setTestResult(null);
    } catch (err: any) {
      setSaveError(err.message || "Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  const isAdmin = user?.role === "Administrator";

  return (
    <div className="space-y-3.5 max-w-4xl mx-auto pb-6">
      <div>
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
          <Settings className="h-4 w-4 text-cyan-400" />
          Agent Configuration
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Configuration parameters for FortiSIEM live connectors, blind review safeguards, and platform profile
        </p>
      </div>

      <div className="space-y-3">
        {/* 1. FortiSIEM Integration & Credentials Panel */}
        <div id="fortisiem" className="rounded-xl border border-cyan-900/60 bg-gradient-to-br from-slate-950 via-slate-900/90 to-cyan-950/20 p-3.5 sm:p-4 space-y-3 shadow-lg shadow-cyan-950/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-slate-800">
            <div>
              <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-2">
                <Server className="h-4 w-4 text-cyan-400" />
                FortiSIEM Supervisor Integration & Credentials
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Configure FortiSIEM Supervisor IP/URL and service credentials for on-demand incident pulling
              </p>
            </div>

            {/* Live Indicator */}
            <div>
              {isConfigured ? (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live Configured
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-950 text-amber-300 border border-amber-800 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  Not Configured (Fixture Mode)
                </span>
              )}
            </div>
          </div>

          {!isAdmin && (
            <div className="rounded-lg border border-amber-800/80 bg-amber-950/30 p-2.5 text-xs text-amber-300 flex items-center gap-2">
              <Lock className="h-3.5 w-3.5 shrink-0 text-amber-400" />
              <span>You are viewing in read-only mode. Administrator permissions are required to update SIEM credentials.</span>
            </div>
          )}

          {isLoadingConfig ? (
            <div className="flex items-center gap-2 text-xs text-slate-400 py-3">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-cyan-400" />
              Loading configuration...
            </div>
          ) : (
            <form onSubmit={handleSaveConfig} className="space-y-3 pt-0.5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Host IP / FQDN */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    Supervisor Host IP / FQDN <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    disabled={!isAdmin || isSaving}
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    placeholder="e.g., https://172.26.x.x or https://fortisiem.corp"
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Protocol (https://) will be added automatically if omitted.
                  </span>
                </div>

                {/* Username */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    API / Service Username <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    disabled={!isAdmin || isSaving}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g., svc_ai_verdict or admin"
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    User only requires Read-Only permissions on Incidents.
                  </span>
                </div>

                {/* Password */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-semibold text-slate-300 block">
                      Service Password
                    </label>
                    {isPasswordSet && (
                      <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                        <CheckCircle2 className="h-2.5 w-2.5" /> Saved
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      disabled={!isAdmin || isSaving}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={isPasswordSet ? "•••••••• (Leave blank to keep existing)" : "Enter service password"}
                      className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 pl-2.5 pr-9 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs"
                    >
                      {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                    </button>
                  </div>
                  <span className="text-[10px] text-slate-400 block">
                    Stored only on the server. Never committed to version control.
                  </span>
                </div>

                {/* Request Timeout */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    API Request Timeout (Seconds)
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={120}
                    disabled={!isAdmin || isSaving}
                    value={timeout}
                    onChange={(e) => setTimeoutSec(Number(e.target.value))}
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Recommended: 25 to 30 seconds for complex event payload queries.
                  </span>
                </div>
              </div>

              {/* Toggles */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 border-t border-slate-800">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    disabled={!isAdmin || isSaving}
                    checked={verifySsl}
                    onChange={(e) => setVerifySsl(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 disabled:opacity-50"
                  />
                  <div>
                    <span className="font-semibold block text-[11px]">Verify SSL Certificate</span>
                    <span className="text-[10px] text-slate-400 block">Uncheck if FortiSIEM uses internal/self-signed certs</span>
                  </div>
                </label>

                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    disabled={!isAdmin || isSaving}
                    checked={mockFallback}
                    onChange={(e) => setMockFallback(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 disabled:opacity-50"
                  />
                  <div>
                    <span className="font-semibold block text-[11px]">Allow Offline Fixture Fallback</span>
                    <span className="text-[10px] text-slate-400 block">Falls back to local sample archive if offline</span>
                  </div>
                </label>
              </div>

              {/* Feedback Alerts */}
              {saveSuccess && (
                <div className="rounded-md border border-emerald-800 bg-emerald-950/40 p-2.5 text-xs text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  <span>{saveSuccess}</span>
                </div>
              )}

              {saveError && (
                <div className="rounded-md border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                  <span>{saveError}</span>
                </div>
              )}

              {/* Test Connection Result Box */}
              {testResult && (
                <div
                  className={`rounded-md border p-2.5 text-xs font-mono space-y-0.5 ${testResult.success
                      ? "border-emerald-800 bg-emerald-950/30 text-emerald-300"
                      : "border-rose-800 bg-rose-950/30 text-rose-300"
                    }`}
                >
                  <div className="flex items-center gap-2 font-bold text-xs">
                    {testResult.success ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                    )}
                    {testResult.success ? "Connection Test Successful" : "Connection Test Failed"}
                  </div>
                  <p className="text-[11px] font-sans text-slate-300">{testResult.message}</p>
                  {testResult.latency_ms !== undefined && (
                    <span className="text-[10px] text-slate-400 block font-mono">
                      Roundtrip Latency: {testResult.latency_ms} ms
                    </span>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              {isAdmin && (
                <div className="flex flex-wrap items-center gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={isTesting || isSaving || !host.trim() || !username.trim()}
                    className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
                  >
                    {isTesting ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin text-cyan-400" />
                        Pinging Supervisor...
                      </>
                    ) : (
                      <>
                        <Zap className="h-3 w-3 text-amber-400" />
                        Test Connection
                      </>
                    )}
                  </button>

                  <button
                    type="submit"
                    disabled={isSaving || isTesting || !host.trim() || !username.trim()}
                    className="rounded-md bg-cyan-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm shadow-cyan-900/40"
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin" />
                        Saving Configuration...
                      </>
                    ) : (
                      <>
                        <Save className="h-3 w-3 text-cyan-200" />
                        Save Configuration
                      </>
                    )}
                  </button>
                </div>
              )}
            </form>
          )}
        </div>

        {/* 2. Local LLM Inference Engine (Server 2) Integration Panel */}
        <div id="llm-server" className="rounded-xl border border-indigo-900/60 bg-gradient-to-br from-slate-950 via-slate-900/90 to-indigo-950/20 p-3.5 sm:p-4 space-y-3 shadow-lg shadow-indigo-950/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-slate-800">
            <div>
              <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-2">
                <Cpu className="h-4 w-4 text-indigo-400" />
                Local LLM Inference Engine (Server 2) Integration
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Configure LLM Server IP address, inference port, and OpenAI-compatible endpoint parameters
              </p>
            </div>

            {/* Live Indicator */}
            <div>
              {llmIsOnline ? (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Online &amp; Reachable
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-950 text-amber-300 border border-amber-800 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  Offline / Standby
                </span>
              )}
            </div>
          </div>

          {!isAdmin && (
            <div className="rounded-lg border border-amber-800/80 bg-amber-950/30 p-2.5 text-xs text-amber-300 flex items-center gap-2">
              <Lock className="h-3.5 w-3.5 shrink-0 text-amber-400" />
              <span>You are viewing in read-only mode. Administrator permissions are required to update LLM Server IP.</span>
            </div>
          )}

          {isLoadingLLM ? (
            <div className="flex items-center gap-2 text-xs text-slate-400 py-3">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-indigo-400" />
              Loading LLM configuration...
            </div>
          ) : (
            <form onSubmit={handleSaveLLMConfig} className="space-y-3 pt-0.5">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Host IP / FQDN */}
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    LLM Server IP Address / FQDN <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    disabled={!isAdmin || isSavingLLM}
                    value={llmHost}
                    onChange={(e) => setLlmHost(e.target.value)}
                    placeholder="e.g., 192.0.2.10 or llm.example.com"
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Target IP of Server 2 hosting vLLM or OpenAI-compatible inference.
                  </span>
                </div>

                {/* Port */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    Inference Port <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={65535}
                    disabled={!isAdmin || isSavingLLM}
                    value={llmPort}
                    onChange={(e) => setLlmPort(Number(e.target.value))}
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Standard: 8000 (vLLM), 8080, or 11434 (Ollama)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Protocol */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    Protocol
                  </label>
                  <select
                    disabled={!isAdmin || isSavingLLM}
                    value={llmProtocol}
                    onChange={(e) => setLlmProtocol(e.target.value)}
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  >
                    <option value="http">http://</option>
                    <option value="https">https://</option>
                  </select>
                </div>

                {/* Model Name */}
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    Model Identifier
                  </label>
                  <input
                    type="text"
                    disabled={!isAdmin || isSavingLLM}
                    value={llmModelName}
                    onChange={(e) => setLlmModelName(e.target.value)}
                    placeholder="e.g., Qwen/Qwen2.5-7B-Instruct-AWQ"
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Computed Endpoint Preview & Network Diagnostic */}
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5 space-y-2 text-[11px]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="text-slate-400 font-sans">Active Target Base URL:</span>
                  <code className="text-indigo-300 font-mono font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    {llmBaseUrl || `${llmProtocol}://${llmHost || "127.0.0.1"}:${llmPort}/v1`}
                  </code>
                </div>

                {server1OutboundIp && (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-1.5 border-t border-slate-800/80">
                    <span className="text-slate-400 font-sans">
                      Server 1 Outbound Public IP (for AWS Security Group):
                    </span>
                    <span className="text-emerald-400 font-mono font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                      {server1OutboundIp}
                    </span>
                  </div>
                )}
              </div>

              {/* Toggles */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 border-t border-slate-800">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-300 block">
                    Inference Timeout (Seconds)
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={180}
                    disabled={!isAdmin || isSavingLLM}
                    value={llmTimeout}
                    onChange={(e) => setLlmTimeout(Number(e.target.value))}
                    className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 px-2.5 text-xs font-mono text-slate-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Recommended: 60 seconds for complex incident reasoning and evidence synthesis.
                  </span>
                </div>

                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none pt-2">
                  <input
                    type="checkbox"
                    disabled={!isAdmin || isSavingLLM}
                    checked={llmAllowMockFallback}
                    onChange={(e) => setLlmAllowMockFallback(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-0 disabled:opacity-50"
                  />
                  <div>
                    <span className="font-semibold block text-[11px]">Allow Offline Heuristic Fallback</span>
                    <span className="text-[10px] text-slate-400 block">
                      Enables simulated fallback if Server 2 is undergoing maintenance
                    </span>
                  </div>
                </label>
              </div>

              {/* Feedback Alerts */}
              {llmSaveSuccess && (
                <div className="rounded-md border border-emerald-800 bg-emerald-950/40 p-2.5 text-xs text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  <span>{llmSaveSuccess}</span>
                </div>
              )}

              {llmSaveError && (
                <div className="rounded-md border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                  <span>{llmSaveError}</span>
                </div>
              )}

              {/* Test Connection Result Box */}
              {llmTestResult && (
                <div
                  className={`rounded-md border p-2.5 text-xs font-mono space-y-1 ${
                    llmTestResult.success
                      ? "border-emerald-800 bg-emerald-950/30 text-emerald-300"
                      : "border-rose-800 bg-rose-950/30 text-rose-300"
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold text-xs">
                    {llmTestResult.success ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                    )}
                    {llmTestResult.success ? "LLM Server Connection Successful" : "LLM Server Connection Failed"}
                  </div>
                  <p className="text-[11px] font-sans text-slate-300">{llmTestResult.message}</p>
                  <div className="flex flex-wrap gap-4 text-[10px] text-slate-400 pt-0.5">
                    {llmTestResult.latency_ms !== undefined && (
                      <span>Latency: {llmTestResult.latency_ms} ms</span>
                    )}
                    {llmTestResult.tested_url && (
                      <span>Endpoint: {llmTestResult.tested_url}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              {isAdmin && (
                <div className="flex flex-wrap items-center gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={handleTestLLMConnection}
                    disabled={isTestingLLM || isSavingLLM || !llmHost.trim()}
                    className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50 transition-colors flex items-center gap-1.5"
                  >
                    {isTestingLLM ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin text-indigo-400" />
                        Testing Connection...
                      </>
                    ) : (
                      <>
                        <Zap className="h-3 w-3 text-amber-400" />
                        Test Connection
                      </>
                    )}
                  </button>

                  <button
                    type="submit"
                    disabled={isSavingLLM || isTestingLLM || !llmHost.trim()}
                    className="rounded-md bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm shadow-indigo-900/40"
                  >
                    {isSavingLLM ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin" />
                        Saving Configuration...
                      </>
                    ) : (
                      <>
                        <Save className="h-3 w-3 text-indigo-200" />
                        Save LLM Configuration
                      </>
                    )}
                  </button>
                </div>
              )}
            </form>
          )}
        </div>

        {/* 3. Investigation Controls */}
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 sm:p-4 space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Sliders className="h-3.5 w-3.5 text-cyan-400" />
            Analyst Investigation Safeguards
          </h2>

          <div className="flex items-center justify-between border-t border-slate-800 pt-2.5">
            <div>
              <span className="text-xs font-semibold text-slate-200 block">
                Default Blind Review Mode
              </span>
              <span className="text-[11px] text-slate-400">
                Mask historical resolution and machine-generated verdicts to prevent analyst confirmation bias.
              </span>
            </div>
            <button
              onClick={() => setBlindReviewMode(!blindReviewMode)}
              className={`rounded-md px-2.5 py-1 text-xs font-bold transition-all border ${blindReviewMode
                  ? "bg-amber-950 text-amber-300 border-amber-800 shadow-sm"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
                }`}
            >
              {blindReviewMode ? "ENABLED" : "DISABLED"}
            </button>
          </div>

          <div className="flex items-center justify-between border-t border-slate-800 pt-2.5">
            <div>
              <span className="text-xs font-semibold text-slate-200 block">Theme Preference</span>
              <span className="text-[11px] text-slate-400">
                Switch between Obsidian Glass (Default) and Classic Slate &amp; Cyan theme.
              </span>
            </div>
            <button
              type="button"
              onClick={toggleTheme}
              data-testid="config-theme-toggle-btn"
              className="rounded-md theme-secondary-btn px-2.5 py-1 text-xs font-bold transition-colors"
            >
              {theme === "obsidian" ? "OBSIDIAN GLASS" : "CLASSIC SLATE"}
            </button>
          </div>
        </div>

        {/* 3. Server & Architecture Info */}
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 sm:p-4 space-y-2.5 font-mono text-xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2 font-sans">
            <Database className="h-3.5 w-3.5 text-cyan-400" />
            Infrastructure Topology & Deployment Profile
          </h2>

          <div className="space-y-1.5 text-[11px] pt-0.5">
            <div className="flex justify-between py-1 border-b border-slate-800/80">
              <span className="text-slate-400">Active Node:</span>
              <span className="text-slate-200 font-bold">Server 1 — Application Server</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/80">
              <span className="text-slate-400">Target Operating System:</span>
              <span className="text-slate-200">Ubuntu Server LTS (systemd + Nginx)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/80">
              <span className="text-slate-400">Database Engine:</span>
              <span className="text-slate-200">PostgreSQL (Production) / SQLite (Local Dev)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/80">
              <span className="text-slate-400">Local LLM Host (Server 2):</span>
              <span className={llmIsOnline ? "text-emerald-400 font-mono" : "text-amber-400 font-mono"}>
                {llmBaseUrl || `${llmHost || "Not Configured"}:${llmPort}`} ({llmIsOnline ? "ONLINE" : "STANDBY / OFFLINE"})
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">SIEM Write-Back & Auto Closure:</span>
              <span className="text-slate-400">Disabled (Dry-run read-only phase)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
