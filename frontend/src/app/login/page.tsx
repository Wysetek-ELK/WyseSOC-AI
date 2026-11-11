"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Lock, User, AlertCircle, ArrowRight } from "lucide-react";
import { useApp } from "@/context/AppContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useApp();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await login(username, password);
      router.push("/agent-mission-control");
    } catch (err: any) {
      setError(err.message || "Authentication failed. Check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4 font-sans">
      <div className="w-full max-w-sm rounded-xl theme-glass-panel p-6 shadow-2xl">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400 border border-sky-500/40 shadow-lg mb-3">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold tracking-tight text-sky-300">AI VERDICT</h1>
          <p className="text-[11px] text-cyan-400 font-mono mt-0.5 tracking-wider uppercase">
            Agentic SOC Intelligence Platform
          </p>
          <p className="text-[10px] text-slate-400 font-medium mt-1">
            Evidence-Driven Security Intelligence
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">
              Username or Analyst ID
            </label>
            <div className="relative">
              <User className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                required
                className="w-full rounded-md border border-slate-800 bg-slate-950/80 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full rounded-md border border-slate-800 bg-slate-950/80 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 flex items-center justify-center gap-2 rounded-md theme-primary-btn py-1.5 text-xs font-semibold disabled:opacity-50 transition-all"
          >
            <span>{isSubmitting ? "Authenticating..." : "Sign In to Platform"}</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>

        <div className="mt-5 border-t border-slate-800/80 pt-3 text-center">
          <p className="text-[10px] text-slate-500 font-mono">
            Authorized SOC Personnel Only • JWT &amp; RBAC Protected
          </p>
        </div>
      </div>
    </div>
  );
}
