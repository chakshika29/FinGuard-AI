import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  Landmark,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Banner, KpiCard, LoadingState, StatusBadge } from "../components/UI";
import { api, getErrorMessage } from "../services/api";

const PIE_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"];

export function OverviewPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/dashboard/summary")
      .then((res) => setData(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState message="Loading executive governance & risk summary..." />;
  if (error) return <Banner type="error" message={error} />;
  if (!data) return null;

  const { kpis, charts, recent_governance_violations } = data;

  return (
    <div className="space-y-6">
      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          title="Total Curated Transactions"
          value={kpis.total_transactions.toLocaleString()}
          subtitle="Deduplicated & validated ledger"
          icon={<Activity className="w-5 h-5" />}
          tone="blue"
        />
        <KpiCard
          title="Total Transaction Value"
          value={`$${(kpis.total_transaction_value / 1_000_000).toFixed(2)}M`}
          subtitle={`$${kpis.total_transaction_value.toLocaleString()}`}
          icon={<DollarSign className="w-5 h-5" />}
          tone="emerald"
        />
        <KpiCard
          title="Data Quality Score"
          value={`${kpis.data_quality_score.toFixed(2)}%`}
          subtitle="7-dimension weighted score"
          icon={<CheckCircle2 className="w-5 h-5" />}
          tone={kpis.data_quality_score >= 95 ? "emerald" : "amber"}
        />
        <KpiCard
          title="Suspicious Transactions"
          value={kpis.suspicious_transactions.toLocaleString()}
          subtitle="Risk indicators >= 50 (not confirmed fraud)"
          icon={<AlertTriangle className="w-5 h-5" />}
          tone="red"
        />
        <KpiCard
          title="High-Risk Credit Accounts"
          value={kpis.high_risk_accounts.toLocaleString()}
          subtitle="Utilization >= 75% or High/Critical tier"
          icon={<Landmark className="w-5 h-5" />}
          tone="amber"
        />
        <KpiCard
          title="Active Quality Rules"
          value={kpis.active_governance_rules}
          subtitle={`${kpis.active_policies} active governance policies`}
          icon={<ShieldCheck className="w-5 h-5" />}
          tone="indigo"
        />
        <KpiCard
          title="Failed Validations (Latest)"
          value={kpis.failed_validations.toLocaleString()}
          subtitle={`${kpis.open_quarantined.toLocaleString()} open quarantined records`}
          icon={<ShieldAlert className="w-5 h-5" />}
          tone="red"
        />
        <KpiCard
          title="Latest Ingestion Status"
          value={kpis.latest_ingestion_status}
          subtitle={kpis.latest_ingestion_file || "Awaiting ingestion"}
          icon={<UploadCloud className="w-5 h-5" />}
          tone="slate"
        />
      </div>

      {/* Primary Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Transaction Volume & Suspicious Activity Over Time</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={charts.transaction_volume_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="transactions" name="Transactions" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.2} />
                <Area type="monotone" dataKey="suspicious" name="Suspicious" stroke="#ef4444" fill="#ef4444" fillOpacity={0.25} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Data Quality Dimension Scores (%)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.quality_dimension_scores} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="dimension" width={130} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="score" name="Pass Score (%)" fill="#1d4ed8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Secondary Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Fraud Risk Severity Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={charts.fraud_risk_distribution} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={80} label>
                  {charts.fraud_risk_distribution.map((_: any, i: number) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Transaction Amount Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.transaction_amount_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Transactions" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Credit Utilization Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.credit_utilization_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Accounts" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Merchant Risk & Quality Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Risk by Merchant Category (Suspicious Count)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.risk_by_merchant_category}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="category" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={55} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="suspicious" name="Suspicious Tx" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-sm font-semibold mb-4">Data Quality Score History</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={charts.data_quality_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={[80, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="score" name="Quality Score %" stroke="#10b981" strokeWidth={2.5} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Governance Violations */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <h3 className="text-sm font-semibold mb-3">Recent Data Quality & Governance Violations</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-4">Rule ID</th>
                <th className="py-2 pr-4">Rule Name</th>
                <th className="py-2 pr-4">Dimension</th>
                <th className="py-2 pr-4">Severity</th>
                <th className="py-2 pr-4">Failed Records</th>
                <th className="py-2">Pass Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {recent_governance_violations.map((v: any, idx: number) => (
                <tr key={idx}>
                  <td className="py-2.5 pr-4 font-mono text-xs">{v.rule_id}</td>
                  <td className="py-2.5 pr-4 font-medium">{v.rule_name}</td>
                  <td className="py-2.5 pr-4">{v.dimension}</td>
                  <td className="py-2.5 pr-4">
                    <StatusBadge label={v.severity} variant={v.severity === "CRITICAL" ? "red" : "amber"} />
                  </td>
                  <td className="py-2.5 pr-4 font-mono">{v.failed_count.toLocaleString()}</td>
                  <td className="py-2.5">{v.pass_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
