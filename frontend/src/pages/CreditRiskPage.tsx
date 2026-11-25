import { useEffect, useState } from "react";
import { AlertCircle, DollarSign, Landmark, Percent } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, KpiCard, LoadingState, Pagination, riskVariant, StatusBadge } from "../components/UI";
import { api, getErrorMessage } from "../services/api";

const COLORS = ["#10b981", "#f59e0b", "#fb923c", "#ef4444", "#991b1b"];

export function CreditRiskPage() {
  const [summary, setSummary] = useState<any>(null);
  const [accounts, setAccounts] = useState<any>({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [repayFilter, setRepayFilter] = useState("");
  const [riskTier, setRiskTier] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get("/api/credit-risk/summary"),
      api.get("/api/credit-risk/accounts", {
        params: {
          page,
          page_size: 15,
          repayment_status: repayFilter || undefined,
          risk_tier: riskTier || undefined,
        },
      }),
    ])
      .then(([sRes, aRes]) => {
        setSummary(sRes.data);
        setAccounts(aRes.data);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, repayFilter, riskTier]);

  if (loading) return <LoadingState />;
  if (error) return <Banner type="error" message={error} />;

  return (
    <div className="space-y-6">
      <Banner
        type="info"
        message={summary?.disclaimer || "Educational demonstration model only — not a validated credit decision system."}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Portfolio Exposure" value={`$${((summary?.total_outstanding_balance || 0) / 1_000_000).toFixed(2)}M`} subtitle={`Limit: $${((summary?.total_credit_limit || 0) / 1_000_000).toFixed(2)}M`} icon={<DollarSign className="w-5 h-5" />} tone="blue" />
        <KpiCard title="Avg Credit Utilization" value={`${summary?.avg_utilization_pct || 0}%`} subtitle={`${(summary?.high_utilization_accounts || 0).toLocaleString()} accounts >= 75%`} icon={<Percent className="w-5 h-5" />} tone="amber" />
        <KpiCard title="Overdue Accounts" value={(summary?.overdue_accounts || 0).toLocaleString()} subtitle={`${summary?.overdue_rate_pct || 0}% delinquency rate`} icon={<AlertCircle className="w-5 h-5" />} tone="red" />
        <KpiCard title="High-Risk Credit Accounts" value={(summary?.high_risk_accounts || 0).toLocaleString()} subtitle={`Avg Credit Risk Score: ${summary?.avg_credit_risk_score}`} icon={<Landmark className="w-5 h-5" />} tone="indigo" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold mb-3">Exposure by Customer Segment ($)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary?.exposure_by_segment || []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="segment" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total_exposure" name="Outstanding Exposure" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold mb-3">Repayment Status Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={summary?.repayment_distribution || []} dataKey="account_count" nameKey="repayment_status" cx="50%" cy="50%" outerRadius={80} label>
                  {(summary?.repayment_distribution || []).map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Accounts Table */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold">Account-Level Credit Risk Profiles</h3>
          <div className="flex gap-2">
            <select value={repayFilter} onChange={(e) => { setPage(1); setRepayFilter(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded border dark:bg-slate-800 dark:border-slate-700">
              <option value="">All Repayment Statuses</option>
              {["CURRENT", "PAST_DUE_30", "PAST_DUE_60", "PAST_DUE_90", "DEFAULT"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select value={riskTier} onChange={(e) => { setPage(1); setRiskTier(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded border dark:bg-slate-800 dark:border-slate-700">
              <option value="">All Credit Tiers</option>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-3">Account / Customer</th>
                <th className="py-2 pr-3">Segment</th>
                <th className="py-2 pr-3">Credit Limit</th>
                <th className="py-2 pr-3">Balance</th>
                <th className="py-2 pr-3">Utilization</th>
                <th className="py-2 pr-3">Repayment</th>
                <th className="py-2 pr-3">Delinq. Days</th>
                <th className="py-2">Demo Credit Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {accounts.items.map((a: any) => (
                <tr key={a.account_id}>
                  <td className="py-2.5 pr-3">
                    <div className="font-mono font-semibold">{a.account_id}</div>
                    <div className="text-[11px] text-slate-500">{a.customer_id} · {a.card_token_masked}</div>
                  </td>
                  <td className="py-2.5 pr-3">{a.customer_segment}</td>
                  <td className="py-2.5 pr-3">${a.credit_limit.toLocaleString()}</td>
                  <td className="py-2.5 pr-3 font-semibold">${a.outstanding_balance.toLocaleString()}</td>
                  <td className="py-2.5 pr-3">{a.credit_utilization_pct}%</td>
                  <td className="py-2.5 pr-3">
                    <StatusBadge label={a.repayment_status} variant={a.repayment_status === "CURRENT" ? "green" : "red"} />
                  </td>
                  <td className="py-2.5 pr-3 font-mono">{a.delinquency_days}d</td>
                  <td className="py-2.5">
                    <StatusBadge label={`${a.credit_risk_score} (${a.credit_risk_tier})`} variant={riskVariant(a.credit_risk_tier)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={15} total={accounts.total} onPageChange={setPage} />
      </div>
    </div>
  );
}
