import { useEffect, useState } from "react";
import { ArrowRight, Database, FileSpreadsheet, ShieldAlert, BarChart } from "lucide-react";
import { Banner, LoadingState, StatusBadge } from "../components/UI";
import { api, getErrorMessage } from "../services/api";

export function LineagePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/governance/lineage")
      .then((res) => setData(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <Banner type="error" message={error} />;

  const mainFlow = (data?.pipeline_stages || []).filter((s: any) => s.id !== "quarantine");
  const quarantineStage = (data?.pipeline_stages || []).find((s: any) => s.id === "quarantine");

  return (
    <div className="space-y-6">
      {/* Interactive Architecture Lineage Diagram */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <h3 className="text-base font-semibold mb-1">End-to-End Medallion Data Lineage</h3>
        <p className="text-xs text-slate-500 mb-6">
          Traceability from raw synthetic file ingestion through standardization, quality quarantine, curation, and BI consumption.
        </p>

        <div className="flex flex-wrap items-center gap-3 justify-between">
          {mainFlow.map((stage: any, idx: number) => (
            <div key={stage.id} className="flex items-center gap-3 flex-1 min-w-[160px]">
              <div className="flex-1 p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/30">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  {idx === 0 ? <FileSpreadsheet className="w-3.5 h-3.5" /> : idx === mainFlow.length - 1 ? <BarChart className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />}
                  {stage.layer}
                </div>
                <div className="text-sm font-bold mt-1">{stage.label}</div>
                <div className="text-[11px] font-mono text-slate-500 mt-1 break-all">{stage.dataset}</div>
              </div>
              {idx < mainFlow.length - 1 && <ArrowRight className="w-5 h-5 text-blue-500 shrink-0 hidden md:block" />}
            </div>
          ))}
        </div>

        {quarantineStage && (
          <div className="mt-4 flex justify-center">
            <div className="p-3.5 rounded-xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/30 flex items-center gap-3 max-w-md">
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
              <div>
                <div className="text-xs font-bold text-amber-800 dark:text-amber-300">
                  Staging Validation Branch → {quarantineStage.label}
                </div>
                <div className="text-[11px] font-mono text-slate-600 dark:text-slate-400">{quarantineStage.dataset}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Lineage Execution History */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        <h3 className="text-sm font-semibold mb-3">Recorded Transformation Lineage Events</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2 pr-3">Job ID</th>
                <th className="py-2 pr-3">Transformation</th>
                <th className="py-2 pr-3">Source Table</th>
                <th className="py-2 pr-3">Destination Table</th>
                <th className="py-2 pr-3">In / Out</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {(data?.recent_events || []).map((ev: any) => (
                <tr key={ev.id}>
                  <td className="py-2.5 pr-3 font-mono">{ev.job_id}</td>
                  <td className="py-2.5 pr-3 font-medium">{ev.transformation_name}</td>
                  <td className="py-2.5 pr-3 font-mono">{ev.source_table}</td>
                  <td className="py-2.5 pr-3 font-mono">{ev.destination_table}</td>
                  <td className="py-2.5 pr-3 font-mono">{ev.records_in.toLocaleString()} → {ev.records_out.toLocaleString()}</td>
                  <td className="py-2.5 pr-3"><StatusBadge label={ev.status} variant="green" /></td>
                  <td className="py-2.5 text-slate-500">{ev.executed_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
