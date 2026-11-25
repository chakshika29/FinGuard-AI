import React, { useEffect, useState } from "react";
import { Play, Plus } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, KpiCard, LoadingState, Pagination, StatusBadge } from "../components/UI";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../services/api";
import { QualityRuleItem } from "../types";

export function DataQualityPage() {
  const { user } = useAuth();
  const canEdit = user?.role === "Administrator" || user?.role === "Data Steward";

  const [summary, setSummary] = useState<any>(null);
  const [rules, setRules] = useState<QualityRuleItem[]>([]);
  const [quarantine, setQuarantine] = useState<any>({ items: [], total: 0 });
  const [qPage, setQPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [showNewRule, setShowNewRule] = useState(false);
  const [newRule, setNewRule] = useState({
    rule_name: "",
    description: "",
    column_name: "transaction_amount",
    dimension: "Accuracy",
    severity: "HIGH",
    threshold: 99.0,
    rule_type: "not_null",
  });

  const loadAll = async () => {
    try {
      const [sumRes, rulesRes, qRes] = await Promise.all([
        api.get("/api/data-quality/summary"),
        api.get("/api/data-quality/rules"),
        api.get("/api/data-quality/quarantine", { params: { page: qPage, page_size: 10 } }),
      ]);
      setSummary(sumRes.data);
      setRules(rulesRes.data);
      setQuarantine(qRes.data);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [qPage]);

  const handleRunChecks = async () => {
    try {
      const res = await api.post("/api/data-quality/run");
      setNotice({ type: "success", text: `Quality run ${res.data.run_id} completed: Score ${res.data.overall_score}%` });
      loadAll();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  const toggleRule = async (rule: QualityRuleItem) => {
    try {
      await api.patch(`/api/data-quality/rules/${rule.rule_id}`, { enabled: !rule.enabled });
      setNotice({ type: "success", text: `Rule ${rule.rule_id} ${!rule.enabled ? "enabled" : "disabled"}.` });
      loadAll();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/api/data-quality/rules", newRule);
      setShowNewRule(false);
      setNotice({ type: "success", text: "New quality rule created." });
      loadAll();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  const remediateQuarantine = async (qid: string, status: string) => {
    try {
      await api.patch(`/api/data-quality/quarantine/${qid}`, {
        remediation_status: status,
        remediation_notes: `Updated by ${user?.username} via Governance Console`,
      });
      setNotice({ type: "success", text: `Quarantine record ${qid} marked ${status}.` });
      loadAll();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  if (loading) return <LoadingState />;

  const dimChart = Object.entries(summary?.dimension_scores || {}).map(([dimension, score]) => ({
    dimension,
    score,
  }));

  return (
    <div className="space-y-6">
      {notice && <Banner type={notice.type} message={notice.text} onClose={() => setNotice(null)} />}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">{summary?.scoring_formula}</p>
        {canEdit && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowNewRule(!showNewRule)}
              className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-semibold flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> New Rule
            </button>
            <button
              onClick={handleRunChecks}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5"
            >
              <Play className="w-4 h-4" /> Run Quality Checks
            </button>
          </div>
        )}
      </div>

      {showNewRule && (
        <form onSubmit={handleCreateRule} className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-blue-200 dark:border-blue-800 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <input required placeholder="Rule Name" value={newRule.rule_name} onChange={(e) => setNewRule({ ...newRule, rule_name: e.target.value })} className="px-3 py-2 rounded border dark:bg-slate-800 dark:border-slate-700" />
          <input required placeholder="Description" value={newRule.description} onChange={(e) => setNewRule({ ...newRule, description: e.target.value })} className="px-3 py-2 rounded border dark:bg-slate-800 dark:border-slate-700" />
          <input required placeholder="Column Name" value={newRule.column_name} onChange={(e) => setNewRule({ ...newRule, column_name: e.target.value })} className="px-3 py-2 rounded border dark:bg-slate-800 dark:border-slate-700" />
          <select value={newRule.dimension} onChange={(e) => setNewRule({ ...newRule, dimension: e.target.value })} className="px-3 py-2 rounded border dark:bg-slate-800 dark:border-slate-700">
            {["Completeness", "Accuracy", "Consistency", "Uniqueness", "Validity", "Timeliness", "Referential Integrity"].map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select value={newRule.severity} onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })} className="px-3 py-2 rounded border dark:bg-slate-800 dark:border-slate-700">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button type="submit" className="px-4 py-2 rounded bg-blue-600 text-white font-semibold">Save Rule</button>
        </form>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Overall Quality Score" value={`${summary?.overall_score?.toFixed(2)}%`} icon={<Play className="w-5 h-5" />} tone="emerald" />
        <KpiCard title="Records Evaluated" value={(summary?.total_records_evaluated || 0).toLocaleString()} icon={<Play className="w-5 h-5" />} tone="blue" />
        <KpiCard title="Failed Validations" value={(summary?.failed_validation_count || 0).toLocaleString()} icon={<Play className="w-5 h-5" />} tone="amber" />
        <KpiCard title="Open Quarantined" value={(summary?.quarantine_summary?.OPEN || 0).toLocaleString()} icon={<Play className="w-5 h-5" />} tone="red" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold mb-3">7-Dimension Quality Breakdown</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dimChart}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="dimension" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={50} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="score" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold mb-3">Quality Score History</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary?.history || []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="run_id" tick={{ fontSize: 10 }} />
                <YAxis domain={[80, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="overall_score" stroke="#10b981" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Rule Management Table */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <h3 className="text-sm font-semibold mb-3">Configurable Data Quality Rules ({rules.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-3">Rule ID</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Column</th>
                <th className="py-2 pr-3">Dimension</th>
                <th className="py-2 pr-3">Severity</th>
                <th className="py-2 pr-3">Threshold</th>
                <th className="py-2 pr-3">Pass Rate</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rules.map((r) => {
                const rr = summary?.rule_results?.find((x: any) => x.rule_id === r.rule_id);
                return (
                  <tr key={r.rule_id}>
                    <td className="py-2.5 pr-3 font-mono">{r.rule_id}</td>
                    <td className="py-2.5 pr-3 font-medium">{r.rule_name}</td>
                    <td className="py-2.5 pr-3 font-mono">{r.column_name}</td>
                    <td className="py-2.5 pr-3">{r.dimension}</td>
                    <td className="py-2.5 pr-3">
                      <StatusBadge label={r.severity} variant={r.severity === "CRITICAL" ? "red" : "amber"} />
                    </td>
                    <td className="py-2.5 pr-3">{r.threshold}%</td>
                    <td className="py-2.5 pr-3 font-semibold">{rr ? `${rr.pass_rate}%` : "—"}</td>
                    <td className="py-2.5">
                      <button
                        disabled={!canEdit}
                        onClick={() => toggleRule(r)}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold ${
                          r.enabled
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}
                      >
                        {r.enabled ? "Enabled" : "Disabled"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quarantined Records */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <h3 className="text-sm font-semibold mb-3">Quarantined Records (Preserved for Investigation)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-3">Quarantine ID</th>
                <th className="py-2 pr-3">Transaction ID</th>
                <th className="py-2 pr-3">Failure Reasons</th>
                <th className="py-2 pr-3">Severity</th>
                <th className="py-2 pr-3">Status</th>
                {canEdit && <th className="py-2">Remediation</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {quarantine.items.map((q: any) => (
                <tr key={q.quarantine_id}>
                  <td className="py-2.5 pr-3 font-mono">{q.quarantine_id}</td>
                  <td className="py-2.5 pr-3 font-mono">{q.transaction_id || "(empty)"}</td>
                  <td className="py-2.5 pr-3 text-red-600 dark:text-red-400">{q.failure_reasons}</td>
                  <td className="py-2.5 pr-3"><StatusBadge label={q.severity} variant="red" /></td>
                  <td className="py-2.5 pr-3"><StatusBadge label={q.remediation_status} variant={q.remediation_status === "RESOLVED" ? "green" : "amber"} /></td>
                  {canEdit && (
                    <td className="py-2.5 flex gap-1.5">
                      <button onClick={() => remediateQuarantine(q.quarantine_id, "REVIEWED")} className="px-2 py-1 rounded bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">Review</button>
                      <button onClick={() => remediateQuarantine(q.quarantine_id, "RESOLVED")} className="px-2 py-1 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">Resolve</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={qPage} pageSize={10} total={quarantine.total} onPageChange={setQPage} />
      </div>
    </div>
  );
}
