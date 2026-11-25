import { useEffect, useState } from "react";
import { AlertTriangle, Cpu, ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, KpiCard, LoadingState, Pagination, riskVariant, StatusBadge } from "../components/UI";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../services/api";
import { FraudAlertItem } from "../types";

export function FraudAnalyticsPage() {
  const { user } = useAuth();
  const canInvestigate = user?.role === "Administrator" || user?.role === "Risk Analyst" || user?.role === "Data Steward";
  const canTrainML = user?.role === "Administrator" || user?.role === "Risk Analyst";

  const [summary, setSummary] = useState<any>(null);
  const [alerts, setAlerts] = useState<{ items: FraudAlertItem[]; total: number }>({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [training, setTraining] = useState(false);

  const loadData = async () => {
    try {
      const [sumRes, altRes] = await Promise.all([
        api.get("/api/fraud/summary"),
        api.get("/api/fraud/alerts", {
          params: { page, page_size: 12, risk_level: riskFilter || undefined, status_filter: statusFilter || undefined },
        }),
      ]);
      setSummary(sumRes.data);
      setAlerts(altRes.data);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, riskFilter, statusFilter]);

  const handleReviewAlert = async (alertId: string, nextStatus: string) => {
    try {
      await api.patch(`/api/fraud/alerts/${alertId}`, {
        investigation_status: nextStatus,
        analyst_notes: `Reviewed as ${nextStatus} by ${user?.username}`,
      });
      setNotice({ type: "success", text: `Alert ${alertId} updated to ${nextStatus}.` });
      loadData();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  const handleTrainML = async () => {
    setTraining(true);
    try {
      const res = await api.post("/api/fraud/train-ml");
      setNotice({
        type: "success",
        text: `IsolationForest evaluated on ${res.data.test_size} held-out records: F1=${res.data.f1_score}, PR-AUC=${res.data.pr_auc}`,
      });
      loadData();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setTraining(false);
    }
  };

  if (loading) return <LoadingState />;

  const ml = summary?.ml_evaluation;

  return (
    <div className="space-y-6">
      <Banner
        type="info"
        message={summary?.disclaimer || "Suspicious transactions are risk indicators for analyst investigation, not confirmed fraud."}
      />
      {notice && <Banner type={notice.type} message={notice.text} onClose={() => setNotice(null)} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Suspicious Transactions" value={(summary?.suspicious_transactions || 0).toLocaleString()} subtitle={`${summary?.suspicious_rate_pct}% of curated ledger`} icon={<AlertTriangle className="w-5 h-5" />} tone="red" />
        <KpiCard title="Critical Risk Tx" value={(summary?.critical_risk_transactions || 0).toLocaleString()} subtitle="Risk Score >= 75" icon={<ShieldAlert className="w-5 h-5" />} tone="amber" />
        <KpiCard title="Flagged Exposure" value={`$${((summary?.flagged_exposure_value || 0) / 1000).toFixed(1)}K`} subtitle={`Avg Risk Score: ${summary?.avg_fraud_risk_score}`} icon={<AlertTriangle className="w-5 h-5" />} tone="blue" />
        <KpiCard title="Open Fraud Alerts" value={(summary?.open_alerts || 0).toLocaleString()} subtitle="Awaiting analyst disposition" icon={<ShieldAlert className="w-5 h-5" />} tone="indigo" />
      </div>

      {/* Charts + ML Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold mb-3">Daily Suspicious & Critical Transaction Trends</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary?.fraud_trends || []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="suspicious_count" name="Suspicious" stroke="#f59e0b" strokeWidth={2} />
                <Line type="monotone" dataKey="critical_count" name="Critical" stroke="#ef4444" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Measured ML Evaluation */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-blue-600" /> IsolationForest Anomaly ML
              </h3>
              {canTrainML && (
                <button
                  disabled={training}
                  onClick={handleTrainML}
                  className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
                >
                  {training ? "Evaluating..." : "Re-Evaluate"}
                </button>
              )}
            </div>
            {ml ? (
              <div className="space-y-2 text-xs">
                <p className="text-slate-500">{ml.model_name}</p>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                    <div className="text-slate-500">Precision</div>
                    <div className="font-bold text-sm">{(ml.precision * 100).toFixed(2)}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                    <div className="text-slate-500">Recall</div>
                    <div className="font-bold text-sm">{(ml.recall * 100).toFixed(2)}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                    <div className="text-slate-500">F1-Score</div>
                    <div className="font-bold text-sm">{(ml.f1_score * 100).toFixed(2)}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                    <div className="text-slate-500">PR-AUC / FPR</div>
                    <div className="font-bold text-sm">{ml.pr_auc} / {(ml.false_positive_rate * 100).toFixed(2)}%</div>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500 pt-1">
                  Confusion Matrix (Test N={ml.test_size.toLocaleString()}): TP={ml.confusion_matrix.tp}, FP={ml.confusion_matrix.fp}, FN={ml.confusion_matrix.fn}, TN={ml.confusion_matrix.tn}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Click Re-Evaluate to run unsupervised IsolationForest evaluation.</p>
            )}
          </div>
          <p className="text-[11px] text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-2">
            Measured on held-out synthetic split; zero label leakage.
          </p>
        </div>
      </div>

      {/* Merchant Risk Breakdown */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <h3 className="text-sm font-semibold mb-3">Merchant Category Risk Breakdown</h3>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary?.merchant_risk_breakdown || []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="merchant_category" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="suspicious_rate_pct" name="Suspicious Rate (%)" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Suspicious Transaction Alerts Table */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold">Suspicious Transaction Alerts & Explainability</h3>
          <div className="flex gap-2">
            <select value={riskFilter} onChange={(e) => { setPage(1); setRiskFilter(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded border dark:bg-slate-800 dark:border-slate-700">
              <option value="">All Severities</option>
              <option value="Critical Risk">Critical Risk</option>
              <option value="High Risk">High Risk</option>
            </select>
            <select value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded border dark:bg-slate-800 dark:border-slate-700">
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="ESCALATED">ESCALATED</option>
              <option value="DISMISSED">DISMISSED</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-3">Transaction</th>
                <th className="py-2 pr-3">Amount</th>
                <th className="py-2 pr-3">Category / Country</th>
                <th className="py-2 pr-3">Score</th>
                <th className="py-2 pr-3">Explainable Risk Triggers</th>
                <th className="py-2 pr-3">Status</th>
                {canInvestigate && <th className="py-2">Review Workflow</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {alerts.items.map((a) => (
                <tr key={a.alert_id}>
                  <td className="py-2.5 pr-3">
                    <div className="font-mono font-semibold text-blue-600 dark:text-blue-400">{a.transaction_id}</div>
                    <div className="text-[11px] text-slate-500">{a.customer_id}</div>
                  </td>
                  <td className="py-2.5 pr-3 font-semibold">${a.transaction_amount.toLocaleString()}</td>
                  <td className="py-2.5 pr-3">{a.merchant_category} · {a.transaction_country}</td>
                  <td className="py-2.5 pr-3">
                    <StatusBadge label={`${a.risk_score} (${a.risk_level})`} variant={riskVariant(a.risk_level)} />
                  </td>
                  <td className="py-2.5 pr-3 max-w-xs">
                    <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-slate-600 dark:text-slate-300">
                      {a.explanations.map((ex, i) => (
                        <li key={i}>{ex}</li>
                      ))}
                    </ul>
                  </td>
                  <td className="py-2.5 pr-3">
                    <StatusBadge label={a.investigation_status} variant={a.investigation_status === "OPEN" ? "amber" : a.investigation_status === "ESCALATED" ? "red" : "green"} />
                  </td>
                  {canInvestigate && (
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-1">
                        <button onClick={() => handleReviewAlert(a.alert_id, "INVESTIGATING")} className="px-2 py-1 rounded bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">Investigate</button>
                        <button onClick={() => handleReviewAlert(a.alert_id, "ESCALATED")} className="px-2 py-1 rounded bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300">Escalate</button>
                        <button onClick={() => handleReviewAlert(a.alert_id, "DISMISSED")} className="px-2 py-1 rounded bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">Dismiss</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={12} total={alerts.total} onPageChange={setPage} />
      </div>
    </div>
  );
}
