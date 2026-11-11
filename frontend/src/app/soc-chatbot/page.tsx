"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Bot,
  Send,
  RefreshCw,
  Trash2,
  Server,
  AlertTriangle,
  Check,
  Copy,
  Sparkles,
  ShieldAlert,
  Paperclip,
  X,
  SlidersHorizontal,
  Settings,
  Terminal,
  Cpu,
  Clock,
  Activity,
} from "lucide-react";
import {
  api,
  ChatMessage,
  ChatStatusResponse,
  IncidentListItem,
} from "@/lib/api";
import { BrandLogo } from "@/components/common/BrandLogo";

interface RichChatMessage extends ChatMessage {
  id: string;
  model?: string;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  attached_incident_id?: string;
}

const SOC_QUICK_PROMPTS = [
  {
    title: "Triage Attached Incident",
    prompt:
      "Analyze the attached incident telemetry, assess True Positive vs False Positive likelihood, identify key supporting indicators, and list any missing evidence.",
    requiresIncident: true,
  },
  {
    title: "MITRE ATT&CK Mapping",
    prompt:
      "Map the activity in the attached incident or log to MITRE ATT&CK Tactics and Techniques (include T-codes) and explain the adversary objective.",
    requiresIncident: false,
  },
  {
    title: "Deobfuscate PowerShell / Command",
    prompt:
      "Deobfuscate and analyze the following suspicious command line or payload for malicious intent, C2 indicators, and execution behavior:\n\n```\n<paste command or log here>\n```",
    requiresIncident: false,
  },
  {
    title: "Containment & Playbook",
    prompt:
      "Provide an immediate Tier-2 SOC containment, isolation, and forensic evidence collection checklist for a suspected compromised host or heavy network scanner.",
    requiresIncident: false,
  },
];

function FormattedMessageContent({ content }: { content: string }) {
  const [copiedBlockIdx, setCopiedBlockIdx] = useState<number | null>(null);

  // Split by fenced code blocks ```...```
  const parts = content.split(/(```[\s\S]*?```)/g);

  const renderInlineFormatting = (text: string) => {
    // Handle bold **text** and inline code `code`
    const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return tokens.map((tok, i) => {
      if (tok.startsWith("**") && tok.endsWith("**")) {
        return (
          <strong key={i} className="font-bold text-slate-100">
            {tok.slice(2, -2)}
          </strong>
        );
      }
      if (tok.startsWith("`") && tok.endsWith("`")) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-[11px] text-cyan-300"
          >
            {tok.slice(1, -1)}
          </code>
        );
      }
      return <span key={i}>{tok}</span>;
    });
  };

  return (
    <div className="space-y-2 text-xs leading-relaxed text-slate-200">
      {parts.map((part, idx) => {
        if (part.startsWith("```") && part.endsWith("```")) {
          const lines = part.slice(3, -3).split("\n");
          const lang = lines[0]?.trim() && !lines[0].includes(" ") ? lines[0].trim() : "text";
          const codeBody =
            lang !== "text" || (lines[0]?.trim() === "" && lines.length > 1)
              ? lines.slice(1).join("\n")
              : lines.join("\n");

          return (
            <div
              key={idx}
              className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden my-2 shadow-inner"
            >
              <div className="flex items-center justify-between px-3 py-1 bg-slate-900/90 border-b border-slate-800 text-[10px] font-mono text-slate-400">
                <span className="flex items-center gap-1.5 uppercase">
                  <Terminal className="w-3 h-3 text-cyan-400" />
                  {lang || "output"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(codeBody);
                    setCopiedBlockIdx(idx);
                    setTimeout(() => setCopiedBlockIdx(null), 1500);
                  }}
                  className="flex items-center gap-1 text-slate-400 hover:text-cyan-300 transition-colors"
                >
                  {copiedBlockIdx === idx ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3 overflow-x-auto font-mono text-[11px] text-cyan-200 leading-relaxed">
                <code>{codeBody}</code>
              </pre>
            </div>
          );
        }

        // Render regular paragraphs and bullet points
        const paragraphs = part.split("\n");
        return (
          <div key={idx} className="space-y-1">
            {paragraphs.map((line, lIdx) => {
              const trimmed = line.trim();
              if (!trimmed) return <div key={lIdx} className="h-1" />;

              // Headings
              if (trimmed.startsWith("### ")) {
                return (
                  <h4 key={lIdx} className="text-xs font-bold text-cyan-300 pt-1.5">
                    {renderInlineFormatting(trimmed.slice(4))}
                  </h4>
                );
              }
              if (trimmed.startsWith("## ")) {
                return (
                  <h3 key={lIdx} className="text-sm font-bold text-cyan-200 pt-2 border-b border-slate-800/80 pb-0.5">
                    {renderInlineFormatting(trimmed.slice(3))}
                  </h3>
                );
              }
              // Bullet lists
              if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                return (
                  <div key={lIdx} className="flex items-start gap-2 pl-1">
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <div className="flex-1">{renderInlineFormatting(trimmed.slice(2))}</div>
                  </div>
                );
              }
              // Numbered lists
              const numMatch = trimmed.match(/^(\d+\.)\s+(.*)/);
              if (numMatch) {
                return (
                  <div key={lIdx} className="flex items-start gap-2 pl-1">
                    <span className="font-mono font-bold text-cyan-400 text-[11px] shrink-0">
                      {numMatch[1]}
                    </span>
                    <div className="flex-1">{renderInlineFormatting(numMatch[2])}</div>
                  </div>
                );
              }

              return <p key={lIdx}>{renderInlineFormatting(line)}</p>;
            })}
          </div>
        );
      })}
    </div>
  );
}

export default function SocChatbotPage() {
  const [serverStatus, setServerStatus] = useState<ChatStatusResponse | null>(null);
  const [checkingStatus, setCheckingStatus] = useState(true);

  const [messages, setMessages] = useState<RichChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Incident attachment & model settings
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [attachedIncidentId, setAttachedIncidentId] = useState<string>("");
  const [temperature, setTemperature] = useState<number>(0.3);
  const [showSettings, setShowSettings] = useState(false);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamSeqRef = useRef<number>(0);

  const loadStatus = async () => {
    setCheckingStatus(true);
    try {
      const st = await api.getChatStatus();
      setServerStatus(st);
    } catch (err: any) {
      console.error("Failed to check chatbot Server 2 status", err);
    } finally {
      setCheckingStatus(false);
    }
  };

  const loadIncidents = async () => {
    try {
      const data = await api.getIncidents({ page: 1, page_size: 40 });
      setIncidents(data?.items || []);
    } catch {
      // ignore non-critical background fetch
    }
  };

  useEffect(() => {
    loadStatus();
    loadIncidents();
    const interval = setInterval(loadStatus, 20000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSendMessage = async (overrideText?: string) => {
    const content = (overrideText ?? inputText).trim();
    if (!content || sending) return;

    const userMsg: RichChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      attached_incident_id: attachedIncidentId || undefined,
    };

    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    if (!overrideText) setInputText("");
    setErrorMsg(null);
    setSending(true);

    streamSeqRef.current += 1;
    const streamingId = `a-stream-${streamSeqRef.current}`;
    let hasStreamedChunk = false;

    try {
      const res = await api.streamChatMessage(
        {
          messages: nextMessages.map((m) => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
          })),
          incident_id: attachedIncidentId || undefined,
          temperature,
          max_tokens: 1024,
        },
        {
          onDelta: (delta) => {
            if (!hasStreamedChunk) {
              hasStreamedChunk = true;
              setMessages((prev) => [
                ...prev,
                {
                  id: streamingId,
                  role: "assistant",
                  content: delta,
                  timestamp: new Date().toISOString(),
                },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamingId ? { ...m, content: m.content + delta } : m
                )
              );
            }
          },
        }
      );

      const finalMsg: RichChatMessage = {
        id: streamingId,
        role: "assistant",
        content: res.message.content,
        timestamp: res.message.timestamp || new Date().toISOString(),
        model: res.model,
        latency_ms: res.latency_ms,
        prompt_tokens: res.prompt_tokens,
        completion_tokens: res.completion_tokens,
        total_tokens: res.total_tokens,
        attached_incident_id: res.attached_incident_id || undefined,
      };
      setMessages((prev) =>
        prev.some((m) => m.id === streamingId)
          ? prev.map((m) => (m.id === streamingId ? finalMsg : m))
          : [...prev, finalMsg]
      );
    } catch (err: any) {
      if (hasStreamedChunk) {
        setMessages((prev) => prev.filter((m) => m.id !== streamingId));
      }
      setErrorMsg(err.message || "Failed to connect to Local LLM (Server 2).");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setErrorMsg(null);
  };

  const selectedIncidentObj = incidents.find(
    (inc) => inc.incident_id === attachedIncidentId || inc.id === attachedIncidentId
  );

  return (
    <div className="flex flex-col h-[calc(100vh-3.75rem)] w-full space-y-2">
      {/* Top Header & Server 2 Status */}
      <div className="rounded-xl border border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/30 p-3.5 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="p-1 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <BrandLogo size={30} />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-slate-100 flex items-center gap-2">
              SOC AI Chatbot
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                Local LLM (Server 2)
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Interactive Tier-2/3 Security Analyst Copilot connected directly to your on-premise Server 2 inference engine
            </p>
          </div>
        </div>

        {/* Server 2 Live Telemetry Badges & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {checkingStatus && !serverStatus ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-slate-900 text-slate-400 border border-slate-700">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Probing Server 2...
            </span>
          ) : serverStatus?.is_online ? (
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700 shadow-sm"
              title={serverStatus.status_message}
            >
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Server 2 Online ({serverStatus.host}:{serverStatus.port}) · {serverStatus.latency_ms}ms
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold bg-amber-950/80 text-amber-300 border border-amber-700"
              title={serverStatus?.status_message || "Server 2 unreachable"}
            >
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              Server 2 Offline ({serverStatus?.host || "127.0.0.1"}:{serverStatus?.port || 8000})
            </span>
          )}

          <button
            type="button"
            onClick={loadStatus}
            disabled={checkingStatus}
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 transition-colors"
            title="Refresh Server 2 Connection Status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checkingStatus ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={`px-2.5 py-1 rounded-lg border text-xs flex items-center gap-1.5 transition-colors ${
              showSettings
                ? "bg-indigo-950 border-indigo-700 text-indigo-200"
                : "bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            Options
          </button>

          <Link
            href="/agent-configuration"
            className="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs flex items-center gap-1.5 transition-colors"
            title="Configure Local LLM Server 2 IP & Port"
          >
            <Settings className="w-3.5 h-3.5 text-cyan-400" />
            Configure
          </Link>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              className="px-2.5 py-1 rounded-lg border border-rose-900/60 bg-rose-950/30 hover:bg-rose-900/50 text-rose-300 text-xs flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Expandable Server 2 Parameters & Incident Context Bar */}
      <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[260px]">
          <span className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
            <Paperclip className="w-3.5 h-3.5 text-cyan-400" />
            Attach Incident Context:
          </span>
          <select
            value={attachedIncidentId}
            onChange={(e) => setAttachedIncidentId(e.target.value)}
            className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-cyan-600 max-w-xs sm:max-w-md"
          >
            <option value="">-- No Incident Context Attached (General SOC Chat) --</option>
            {incidents.map((inc) => (
              <option key={inc.id} value={inc.incident_id}>
                #{inc.incident_id} · [{inc.severity}] {inc.title || inc.event_type}
              </option>
            ))}
          </select>

          {attachedIncidentId && (
            <button
              type="button"
              onClick={() => setAttachedIncidentId("")}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300 text-[11px] font-mono hover:bg-cyan-900/60"
            >
              <span>Attached: #{attachedIncidentId}</span>
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            Model: <strong className="text-slate-200">{serverStatus?.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ"}</strong>
          </span>
        </div>
      </div>

      {/* Optional Inference Tuning Controls */}
      {showSettings && (
        <div className="rounded-lg border border-indigo-900/60 bg-slate-950 p-3 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="text-[11px] font-semibold text-slate-300 block mb-1">
              Temperature: <span className="font-mono text-cyan-400">{temperature}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1.0"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-indigo-500"
            />
            <span className="text-[10px] text-slate-500">Lower values (0.1–0.3) keep SOC triage analysis factual.</span>
          </div>
          <div>
            <span className="text-[11px] font-semibold text-slate-300 block mb-1">Active Endpoint (Server 2)</span>
            <div className="font-mono text-[11px] text-slate-400 bg-slate-900 px-2.5 py-1.5 rounded border border-slate-800 truncate">
              {serverStatus?.base_url || "http://127.0.0.1:8000/v1"}
            </div>
          </div>
          <div>
            <span className="text-[11px] font-semibold text-slate-300 block mb-1">Available Models on Server 2</span>
            <div className="flex flex-wrap gap-1">
              {(serverStatus?.available_models || [serverStatus?.model_name || "Qwen2.5-7B"]).map((m, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono text-[10px]">
                  {m}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Chat Conversation Viewport */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-5 py-8">
            <div className="p-3.5 rounded-2xl bg-indigo-950/50 border border-indigo-800/70 text-indigo-400 shadow-lg shadow-indigo-950/20">
              <Bot className="w-9 h-9" />
            </div>
            <div className="max-w-lg space-y-1.5">
              <h2 className="text-base font-bold text-slate-100">
                Ask Verdictum AI Copilot on Server 2
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Analyze suspicious payloads, query FortiSIEM detection rule logic, investigate attached incidents, or map telemetry to MITRE ATT&amp;CK directly using your private Server 2 Local LLM.
              </p>
            </div>

            {/* Starter Prompt Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-2xl w-full pt-2">
              {SOC_QUICK_PROMPTS.map((item, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    if (item.requiresIncident && !attachedIncidentId) {
                      setInputText(item.prompt);
                    } else if (item.prompt.includes("<paste")) {
                      setInputText(item.prompt);
                    } else {
                      handleSendMessage(item.prompt);
                    }
                  }}
                  className="p-3 rounded-lg border border-slate-800 bg-slate-900/70 hover:bg-slate-900 hover:border-indigo-700/80 text-left transition-all group space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200 group-hover:text-indigo-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      {item.title}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {item.prompt}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center shrink-0 mt-0.5 text-indigo-300">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-3xl rounded-xl p-3.5 border shadow-sm space-y-2 ${
                      isUser
                        ? "bg-cyan-950/30 border-cyan-800/70 text-slate-100"
                        : "bg-slate-900/80 border-slate-800 text-slate-200 w-full"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4 border-b border-slate-800/70 pb-1.5 text-[10px] font-mono text-slate-400">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold ${isUser ? "text-cyan-300" : "text-indigo-300"}`}>
                          {isUser ? "SOC Analyst" : `Server 2 · ${msg.model || "Local LLM"}`}
                        </span>
                        {msg.attached_incident_id && (
                          <span className="px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                            Context: #{msg.attached_incident_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {msg.latency_ms && (
                          <span className="text-slate-500">
                            {msg.latency_ms}ms · {msg.total_tokens || 0} tokens
                          </span>
                        )}
                        {!isUser && (
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(msg.content);
                              setCopiedMsgId(msg.id);
                              setTimeout(() => setCopiedMsgId(null), 1500);
                            }}
                            className="text-slate-400 hover:text-slate-200 flex items-center gap-1"
                            title="Copy response"
                          >
                            {copiedMsgId === msg.id ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>

                    {isUser ? (
                      <div className="text-xs whitespace-pre-wrap leading-relaxed text-slate-100">
                        {msg.content}
                      </div>
                    ) : (
                      <FormattedMessageContent content={msg.content} />
                    )}
                  </div>
                </div>
              );
            })}

            {sending &&
              !(
                messages.length > 0 &&
                messages[messages.length - 1].role === "assistant" &&
                messages[messages.length - 1].latency_ms === undefined
              ) && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center shrink-0 text-indigo-300">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                </div>
                <div className="rounded-xl p-3.5 border border-slate-800 bg-slate-900/70 text-xs text-slate-300 flex items-center gap-2.5">
                  <span className="animate-pulse font-mono text-indigo-300">
                    Generating analysis via Server 2 ({serverStatus?.host}:{serverStatus?.port})...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Alert Banner */}
      {errorMsg && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/60 p-3 text-xs text-rose-200 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-rose-300">Server 2 Connection Error</strong>
              <span className="text-[11px]">{errorMsg}</span>
            </div>
          </div>
          <Link
            href="/agent-configuration"
            className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-100 text-[11px] font-semibold shrink-0"
          >
            Check Server 2 Settings →
          </Link>
        </div>
      )}

      {/* Input Composer */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-2.5 shadow-lg space-y-2">
        {selectedIncidentObj && (
          <div className="px-2 py-1 rounded bg-cyan-950/30 border border-cyan-900/50 text-[10px] font-mono text-cyan-300 flex items-center justify-between">
            <span className="truncate">
              Active Incident Context: <strong>#{selectedIncidentObj.incident_id}</strong> ({selectedIncidentObj.title}) · Source IP: {selectedIncidentObj.source_ip || "N/A"}
            </span>
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Server 2 LLM to analyze logs, deobfuscate scripts, explain alerts, or draft SIEM rules... (Enter to send, Shift+Enter for new line)"
            rows={2}
            disabled={sending}
            className="flex-1 resize-none rounded-lg bg-slate-900 border border-slate-800 px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-600 disabled:opacity-60 leading-relaxed"
          />
          <button
            type="button"
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim() || sending}
            className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
          >
            {sending ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Thinking</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Send</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

