"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Lock, User, AlertCircle, ArrowRight } from "lucide-react";
import { useApp } from "@/context/AppContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useApp();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("AdminPassword123!");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await login(username, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Authentication failed. Check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-4 font-sans">
      <div className="w-full max-w-sm rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl backdrop-blur-xl">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-950/70 text-cyan-400 border border-cyan-500/40 shadow-lg shadow-cyan-950/50 mb-3">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold tracking-tight text-slate-100">AI VERDICT</h1>
          <p className="text-[11px] text-cyan-400 font-mono mt-0.5 tracking-wider uppercase">
            SOC Incident Analysis Platform · Phase 1
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
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-md border border-slate-800 bg-slate-950 py-1.5 pl-8 pr-2.5 text-xs text-slate-100 placeholder-slate-600 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                placeholder="Enter username"
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
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-slate-800 bg-slate-950 py-1.5 pl-8 pr-2.5 text-xs text-slate-100 placeholder-slate-600 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                placeholder="Enter password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-cyan-600 py-2 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors shadow-md shadow-cyan-900/20 flex items-center justify-center gap-1.5 mt-2"
          >
            {isSubmitting ? "Authenticating..." : "Sign In to SOC Console"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>

        {/* Demo Credentials Box */}
        <div className="mt-5 rounded-md border border-slate-800 bg-slate-950/60 p-2.5 text-[10px] text-slate-400 font-mono">
          <div className="font-semibold text-slate-300 mb-0.5">Initial Administrator Credentials:</div>
          <div>User: <span className="text-cyan-400">admin</span></div>
          <div>Pass: <span className="text-cyan-400">AdminPassword123!</span></div>
        </div>
      </div>
    </div>
  );
}

