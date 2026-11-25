import { useState } from "react";
import { CloudUpload, Database, FileDown } from "lucide-react";
import { Banner } from "../components/UI";
import { api, downloadCsvReport, getErrorMessage } from "../services/api";

const EXPORT_ITEMS = [
  { id: "transactions", title: "Curated Transactions Export", desc: "Cleaned, standardized, fraud-scored transactions with masked card tokens." },
  { id: "fraud_alerts", title: "Suspicious Fraud Alerts Export", desc: "Flagged transactions (score >= 50) with explainable triggers and ML scores." },
  { id: "credit_risk", title: "Credit Risk Accounts Export", desc: "Account credit limits, balances, utilization ratios, and delinquency tiers." },
  { id: "data_quality", title: "Data Quality Issues Export", desc: "Rule-level validation failure history across all 7 quality dimensions." },
  { id: "quarantine", title: "Quarantined Records Export", desc: "Rejected raw payloads, failure reasons, and steward remediation statuses." },
  { id: "audit_logs", title: "Governance Audit Trail Export", desc: "Append-only operational audit logs for security and governance review." },
];

export function ReportsPage() {
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const exportBigQuerySandbox = async () => {
    setBusy(true);
    try {
      const res = await api.get("/api/reports/export", { params: { report_type: "bigquery_sandbox" } });
      setNotice({
        type: "success",
        text: `Exported ${res.data.files.length} BigQuery Sandbox CSVs (${res.data.files.join(", ")}) to ${res.data.directory}/`,
      });
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const exportPowerBIBundle = async () => {
    setBusy(true);
    try {
      const res = await api.get("/api/reports/export", { params: { report_type: "powerbi_bundle" } });
      setNotice({
        type: "success",
        text: `Exported ${res.data.files.length} optional Power BI CSV datasets to ${res.data.directory}`,
      });
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {notice && <Banner type={notice.type} message={notice.text} onClose={() => setNotice(null)} />}

      {/* Primary Free Cloud Export: BigQuery Sandbox */}
      <div className="bg-navy-800 text-white p-6 rounded-xl flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div>
          <h3 className="text-lg font-bold flex items-center gap-2">
            <CloudUpload className="w-5 h-5 text-blue-400" /> BigQuery Sandbox CSV Export (Zero Billing / No GCS)
          </h3>
          <p className="text-xs text-slate-300 mt-1">
            Exports raw_transactions.csv, cleaned_transactions.csv, quarantined_records.csv, fraud_analytics.csv, and credit_risk_analytics.csv to data/bigquery_sandbox/ for direct browser upload.
          </p>
        </div>
        <button
          disabled={busy}
          onClick={exportBigQuerySandbox}
          className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold"
        >
          {busy ? "Exporting..." : "Export BigQuery Sandbox CSVs"}
        </button>
      </div>

      {/* Optional Power BI CSV Sync */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold flex items-center gap-2">
            <Database className="w-4 h-4 text-slate-500" /> Optional: Power BI CSV Bundle Sync
          </h4>
          <p className="text-xs text-slate-500 mt-1">
            Optional star-schema CSV exports into powerbi/datasets/ if you wish to open them in Power BI Desktop.
          </p>
        </div>
        <button
          disabled={busy}
          onClick={exportPowerBIBundle}
          className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold"
        >
          Sync Optional Power BI CSVs
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {EXPORT_ITEMS.map((item) => (
          <div key={item.id} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4">
            <div>
              <h4 className="text-sm font-bold">{item.title}</h4>
              <p className="text-xs text-slate-500 mt-1">{item.desc}</p>
            </div>
            <button
              onClick={() => downloadCsvReport(item.id)}
              className="w-full py-2 rounded-lg border border-blue-600 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 text-xs font-semibold flex items-center justify-center gap-1.5"
            >
              <FileDown className="w-4 h-4" /> Download CSV
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
