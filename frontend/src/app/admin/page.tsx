"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  UserPlus,
  Users,
  History,
  AlertCircle,
  CheckCircle2,
  Lock,
  RefreshCw,
} from "lucide-react";
import { api, User } from "@/lib/api";
import { useApp } from "@/context/AppContext";

export default function AdminPage() {
  const { user: currentUser } = useApp();

  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"users" | "audit">("users");
  const [isLoading, setIsLoading] = useState(true);

  // New user form state
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("SOC Analyst");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [uList, logsRes] = await Promise.all([
        api.getUsers().catch(() => []),
        api.getAuditLogs({ page: 1, page_size: 50 }).catch(() => ({ items: [] })),
      ]);
      setUsers(uList);
      setAuditLogs(logsRes.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    setIsCreating(true);

    try {
      await api.createUser({
        username: newUsername,
        email: newEmail,
        full_name: newFullName,
        password: newPassword,
        role: newRole,
      });
      setFormSuccess(`User '${newUsername}' created successfully.`);
      setNewUsername("");
      setNewEmail("");
      setNewFullName("");
      setNewPassword("");
      loadData();
    } catch (err: any) {
      setFormError(err.message || "Failed to create user");
    } finally {
      setIsCreating(false);
    }
  };

  const formatEpoch = (isoStr: string) => {
    return new Date(isoStr).toLocaleString();
  };

  return (
    <div className="space-y-3.5 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-cyan-400" />
          SOC Administration & Security Auditing
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          User provisioning, role-based access control (RBAC), and immutable security audit logs
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-1 text-xs font-medium">
        <button
          onClick={() => setActiveTab("users")}
          className={`px-3 py-1.5 border-b-2 transition-colors flex items-center gap-1.5 text-xs ${
            activeTab === "users"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          User Management ({users.length})
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-3 py-1.5 border-b-2 transition-colors flex items-center gap-1.5 text-xs ${
            activeTab === "audit"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="h-3.5 w-3.5" />
          Security Audit Trail ({auditLogs.length})
        </button>
      </div>

      {/* Tab 1: Users */}
      {activeTab === "users" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
          {/* User List */}
          <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Provisioned Accounts
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 font-mono text-slate-500 text-[10px] uppercase">
                    <th className="pb-1.5">Username</th>
                    <th className="pb-1.5">Role</th>
                    <th className="pb-1.5">Email</th>
                    <th className="pb-1.5 text-right">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-900/40">
                      <td className="py-1.5 font-bold text-slate-200 text-xs">
                        {u.username}
                        {u.full_name && <span className="block text-[10px] text-slate-400 font-normal">{u.full_name}</span>}
                      </td>
                      <td className="py-1.5">
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${
                            u.role === "Administrator"
                              ? "bg-rose-950 text-rose-300 border-rose-800"
                              : u.role === "SOC Analyst"
                              ? "bg-cyan-950 text-cyan-300 border-cyan-800"
                              : "bg-slate-900 text-slate-400 border-slate-800"
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="py-1.5 text-slate-400 text-[11px]">{u.email}</td>
                      <td className="py-1.5 text-right text-slate-500 text-[10px]">
                        {formatEpoch(u.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Create User Form */}
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5 text-xs">
            <h2 className="font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 text-xs">
              <UserPlus className="h-3.5 w-3.5 text-cyan-400" />
              Create New User
            </h2>

            {formError && (
              <div className="rounded border border-rose-800 bg-rose-950/40 p-2 text-rose-300 text-[10px]">
                {formError}
              </div>
            )}

            {formSuccess && (
              <div className="rounded border border-emerald-800 bg-emerald-950/40 p-2 text-emerald-300 text-[10px]">
                {formSuccess}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-2 font-sans">
              <div>
                <label className="block text-[10px] font-medium text-slate-400 mb-0.5">Username</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                  placeholder="e.g. analyst_smith"
                />
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-400 mb-0.5">Full Name</label>
                <input
                  type="text"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                  placeholder="e.g. Jane Smith"
                />
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-400 mb-0.5">Email</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                  placeholder="e.g. jane@soc.internal"
                />
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-400 mb-0.5">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                  placeholder="Minimum 8 characters"
                />
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-400 mb-0.5">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                >
                  <option value="SOC Analyst">SOC Analyst</option>
                  <option value="Administrator">Administrator</option>
                  <option value="Read-Only Viewer">Read-Only Viewer</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isCreating}
                className="w-full rounded bg-cyan-600 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 mt-1"
              >
                {isCreating ? "Provisioning..." : "Create Account"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab 2: Audit Trail */}
      {activeTab === "audit" && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Security Audit Event Log
            </h2>
            <button
              onClick={loadData}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200"
            >
              <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase">
                  <th className="pb-1.5">Action</th>
                  <th className="pb-1.5">User</th>
                  <th className="pb-1.5">Resource</th>
                  <th className="pb-1.5">Target ID</th>
                  <th className="pb-1.5">Details</th>
                  <th className="pb-1.5 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-[11px]">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500 font-sans text-xs">
                      No audit events recorded yet.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-900/40">
                      <td className="py-1.5 font-bold text-slate-200 text-xs">{log.action}</td>
                      <td className="py-1.5 text-cyan-400">{log.username || "system"}</td>
                      <td className="py-1.5 text-slate-400">{log.resource_type}</td>
                      <td className="py-1.5 text-slate-300 truncate max-w-[140px]">{log.resource_id}</td>
                      <td className="py-1.5 text-slate-400 truncate max-w-[200px]" title={JSON.stringify(log.details)}>
                        {JSON.stringify(log.details)}
                      </td>
                      <td className="py-1.5 text-right text-slate-500 text-[10px]">
                        {formatEpoch(log.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

