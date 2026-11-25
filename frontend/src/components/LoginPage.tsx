import React, { useState } from "react";
import { ShieldCheck, Lock, User as UserIcon, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../services/api";

const DEMO_ACCOUNTS = [
  { label: "Administrator", username: "admin", pass: "Admin@FinGuard2026!", desc: "System config, users, policies & full access" },
  { label: "Data Steward", username: "steward", pass: "Steward@FinGuard2026!", desc: "Quality rules, catalog, ownership & quarantine" },
  { label: "Risk Analyst", username: "analyst", pass: "Analyst@FinGuard2026!", desc: "Fraud alerts, credit risk & CSV exports" },
];

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin@FinGuard2026!");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-navy-900 via-slate-900 to-navy-700 p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800">
        {/* Left Brand Panel */}
        <div className="p-8 bg-navy-800 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2.5 rounded-xl bg-blue-600/20 border border-blue-400/30">
                <ShieldCheck className="w-7 h-7 text-blue-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight">FinGuard AI</h1>
                <p className="text-xs text-blue-300">Enterprise Data Governance & Risk</p>
              </div>
            </div>
            <h2 className="text-2xl font-semibold leading-snug mb-3">
              Credit & Fraud Risk Data Governance Platform
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              End-to-end medallion ETL, 7-dimension data quality enforcement, data catalog & lineage,
              explainable fraud scoring, and portfolio credit risk analytics.
            </p>
          </div>

          <div className="mt-8 space-y-2.5">
            <p className="text-xs uppercase tracking-wider text-blue-300 font-semibold">
              Quick-Fill Demo Roles
            </p>
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                type="button"
                onClick={() => {
                  setUsername(acc.username);
                  setPassword(acc.pass);
                }}
                className="w-full text-left p-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition flex items-center justify-between"
              >
                <div>
                  <div className="text-sm font-medium text-white">{acc.label}</div>
                  <div className="text-xs text-slate-400">{acc.desc}</div>
                </div>
                <span className="text-xs font-mono text-blue-300">{acc.username}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="p-8 flex flex-col justify-center">
          <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">Sign in to Workspace</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Authenticated via JWT with Role-Based Access Control.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Username
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-sm transition shadow-sm"
            >
              {submitting ? "Authenticating..." : "Sign In"}
            </button>
          </form>

          <p className="mt-6 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-4">
            <strong>Synthetic Data Notice:</strong> All financial transactions, accounts, and card tokens are 100% synthetic for governance & analytics demonstration.
          </p>
        </div>
      </div>
    </div>
  );
}
