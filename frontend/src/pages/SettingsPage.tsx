import { useEffect, useState } from "react";
import { Cloud, HardDrive, Users } from "lucide-react";
import { Banner, StatusBadge } from "../components/UI";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../services/api";
import { SystemStatus } from "../types";

export function SettingsPage({
  systemStatus,
  darkMode,
  onToggleDark,
}: {
  systemStatus: SystemStatus | null;
  darkMode: boolean;
  onToggleDark: () => void;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === "Administrator";
  const [users, setUsers] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAdmin) {
      api
        .get("/api/auth/users")
        .then((res) => setUsers(res.data))
        .catch((err) => setError(getErrorMessage(err)));
    }
  }, [isAdmin]);

  return (
    <div className="space-y-6">
      {error && <Banner type="error" message={error} />}

      {/* Runtime Environment Card */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold flex items-center gap-2">
            {systemStatus?.data_backend === "bigquery" ? <Cloud className="w-5 h-5 text-emerald-500" /> : <HardDrive className="w-5 h-5 text-blue-500" />}
            Platform Runtime & Cloud Integration Status
          </h3>
          <StatusBadge label={systemStatus?.data_backend === "bigquery" ? "GCP BIGQUERY MODE" : "LOCAL MODE (DUCKDB)"} variant={systemStatus?.data_backend === "bigquery" ? "green" : "blue"} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 space-y-1.5">
            <div className="font-semibold text-slate-700 dark:text-slate-200">5-Layer Medallion Datasets</div>
            {Object.entries(systemStatus?.datasets || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500 uppercase">{k}</span>
                <span className="font-mono">{v}</span>
              </div>
            ))}
          </div>
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 space-y-1.5">
            <div className="font-semibold text-slate-700 dark:text-slate-200">Optional Cloud / BigQuery Sandbox Status</div>
            <div>Configured: {systemStatus?.gcp_status?.configured ? "Yes" : "Optional (Running 100% Free in Local DuckDB Mode)"}</div>
            <div>Verified: {systemStatus?.gcp_status?.verified ? "Yes" : "Local Mode Active (No Cloud Billing Needed)"}</div>
            <div className="text-slate-500">For zero-cost BigQuery testing, export CSVs on the Reports page and upload manually in BigQuery Sandbox.</div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-800">
          <span className="text-sm font-medium">Appearance Theme</span>
          <button onClick={onToggleDark} className="px-4 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-semibold">
            {darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          </button>
        </div>
      </div>

      {/* RBAC Users Table (Admin Only) */}
      {isAdmin ? (
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-bold flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-blue-600" /> Application Users & Role-Based Access Control
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2 pr-3">Username</th>
                  <th className="py-2 pr-3">Full Name</th>
                  <th className="py-2 pr-3">Email</th>
                  <th className="py-2 pr-3">Role</th>
                  <th className="py-2">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="py-2.5 pr-3 font-mono font-semibold">{u.username}</td>
                    <td className="py-2.5 pr-3">{u.full_name}</td>
                    <td className="py-2.5 pr-3">{u.email}</td>
                    <td className="py-2.5 pr-3"><StatusBadge label={u.role} variant="blue" /></td>
                    <td className="py-2.5"><StatusBadge label={u.is_active ? "Active" : "Disabled"} variant={u.is_active ? "green" : "red"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <Banner type="info" message={`Signed in as ${user?.role}. User & RBAC administration requires Administrator privileges.`} />
      )}
    </div>
  );
}
