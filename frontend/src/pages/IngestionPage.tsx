import React, { useEffect, useState } from "react";
import { Play, RefreshCw, UploadCloud } from "lucide-react";
import { Banner, LoadingState, StatusBadge } from "../components/UI";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../services/api";
import { IngestionJobItem } from "../types";

export function IngestionPage() {
  const { user } = useAuth();
  const canIngest = user?.role === "Administrator" || user?.role === "Data Steward";

  const [jobs, setJobs] = useState<IngestionJobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [numRecords, setNumRecords] = useState(10000);
  const [seed, setSeed] = useState(101);
  const [issueRate, setIssueRate] = useState(0.03);
  const [fileFormat, setFileFormat] = useState<"csv" | "json">("csv");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [forceReprocess, setForceReprocess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchJobs = async () => {
    try {
      const res = await api.get<IngestionJobItem[]>("/api/ingestion/jobs");
      setJobs(res.data);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const timer = setInterval(fetchJobs, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleGenerate = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const res = await api.post("/api/ingestion/generate", {
        num_records: numRecords,
        seed,
        inject_quality_issues: true,
        quality_issue_rate: issueRate,
        fraud_rate: 0.025,
        file_format: fileFormat,
        auto_ingest: true,
      });
      setNotice({
        type: "success",
        text: `Generated ${numRecords.toLocaleString()} synthetic records & queued job ${res.data.job_id}.`,
      });
      fetchJobs();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setBusy(true);
    setNotice(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("force_reprocess", String(forceReprocess));
      const res = await api.post("/api/ingestion/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setNotice({ type: "success", text: `Uploaded ${selectedFile.name} as job ${res.data.job_id}.` });
      setSelectedFile(null);
      fetchJobs();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {notice && <Banner type={notice.type} message={notice.text} onClose={() => setNotice(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Synthetic Generator Card */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold">Generate & Ingest Synthetic Dataset</h3>
              <p className="text-xs text-slate-500">Seeded reproducible financial transactions with injected DQ issues & fraud patterns.</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Dataset Size</label>
              <select
                value={numRecords}
                onChange={(e) => setNumRecords(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
              >
                <option value={10000}>10,000 records</option>
                <option value={50000}>50,000 records</option>
                <option value={100000}>100,000 records</option>
                <option value={250000}>250,000 records</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Random Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Quality Issue Rate</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="0.25"
                value={issueRate}
                onChange={(e) => setIssueRate(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Format</label>
              <select
                value={fileFormat}
                onChange={(e) => setFileFormat(e.target.value as "csv" | "json")}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON Lines</option>
              </select>
            </div>
          </div>

          <button
            disabled={!canIngest || busy}
            onClick={handleGenerate}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" /> {canIngest ? "Generate & Run ETL Pipeline" : "Requires Admin or Data Steward Role"}
          </button>
        </div>

        {/* File Upload Card */}
        <form onSubmit={handleUpload} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-semibold">Upload Transaction Batch (CSV / JSON)</h3>
            <p className="text-xs text-slate-500">Idempotent SHA-256 deduplication prevents duplicate ingestion on retries.</p>
          </div>

          <input
            type="file"
            accept=".csv,.json"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-950 dark:file:text-blue-300"
          />

          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
            <input
              type="checkbox"
              checked={forceReprocess}
              onChange={(e) => setForceReprocess(e.target.checked)}
            />
            Force reprocess even if SHA-256 checksum matches an earlier completed job
          </label>

          <button
            type="submit"
            disabled={!canIngest || !selectedFile || busy}
            className="w-full py-2.5 rounded-lg bg-navy-700 hover:bg-navy-600 disabled:opacity-50 text-white text-sm font-semibold flex items-center justify-center gap-2"
          >
            <UploadCloud className="w-4 h-4" /> Upload & Trigger ETL
          </button>
        </form>
      </div>

      {/* Job History Table */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold">Ingestion Job Execution History</h3>
          <button onClick={fetchJobs} className="text-xs text-blue-600 flex items-center gap-1 hover:underline">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2 pr-3">Job ID</th>
                  <th className="py-2 pr-3">Source File</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Received</th>
                  <th className="py-2 pr-3">Valid</th>
                  <th className="py-2 pr-3">Quarantined</th>
                  <th className="py-2 pr-3">Duplicates</th>
                  <th className="py-2 pr-3">Duration</th>
                  <th className="py-2">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {jobs.map((j) => (
                  <tr key={j.job_id}>
                    <td className="py-2.5 pr-3 font-mono text-xs">{j.job_id}</td>
                    <td className="py-2.5 pr-3 text-xs truncate max-w-[200px]" title={j.source_file}>{j.source_file}</td>
                    <td className="py-2.5 pr-3">
                      <StatusBadge
                        label={j.status}
                        variant={j.status === "FAILED" ? "red" : j.status.includes("QUARANTINE") ? "amber" : j.status.includes("COMPLETED") ? "green" : "blue"}
                      />
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-xs">{j.records_received.toLocaleString()}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs text-emerald-600">{j.valid_records.toLocaleString()}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs text-amber-600">{j.quarantined_records.toLocaleString()}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs">{j.duplicate_records.toLocaleString()}</td>
                    <td className="py-2.5 pr-3 text-xs">{j.processing_duration_sec}s</td>
                    <td className="py-2.5 text-xs uppercase">{j.backend_target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
