import { useEffect, useState } from "react";
import { Download, Search } from "lucide-react";
import { Banner, LoadingState, Pagination, StatusBadge } from "../components/UI";
import { api, downloadCsvReport, getErrorMessage } from "../services/api";

export function AuditLogsPage() {
  const [data, setData] = useState<any>({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [actor, setActor] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/governance/audit-logs", {
        params: { page, page_size: 25, search: search || undefined, actor: actor || undefined },
      });
      setData(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, actor]);

  return (
    <div className="space-y-4">
      <Banner type="info" message={data.audit_disclaimer || "Application-level append-only audit records for demonstration."} />
      {error && <Banner type="error" message={error} />}

      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search action, resource ID, details..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchLogs()}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
          />
        </div>
        <select value={actor} onChange={(e) => { setPage(1); setActor(e.target.value); }} className="px-3 py-2 text-sm rounded-lg border dark:bg-slate-800 dark:border-slate-700">
          <option value="">All Actors</option>
          <option value="admin">admin</option>
          <option value="steward">steward</option>
          <option value="analyst">analyst</option>
        </select>
        <button onClick={fetchLogs} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium">Search</button>
        <button onClick={() => downloadCsvReport("audit_logs")} className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium flex items-center gap-1.5">
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800">
        {loading ? (
          <LoadingState />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2 pr-3">Timestamp</th>
                    <th className="py-2 pr-3">Actor / Role</th>
                    <th className="py-2 pr-3">Action</th>
                    <th className="py-2 pr-3">Resource</th>
                    <th className="py-2 pr-3">Updated Value</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {data.items.map((l: any) => (
                    <tr key={l.id}>
                      <td className="py-2.5 pr-3 text-slate-500 whitespace-nowrap">{l.timestamp}</td>
                      <td className="py-2.5 pr-3">
                        <span className="font-semibold">{l.actor}</span> <span className="text-slate-400">({l.actor_role})</span>
                      </td>
                      <td className="py-2.5 pr-3 font-mono font-semibold">{l.action}</td>
                      <td className="py-2.5 pr-3 font-mono">{l.resource_type}: {l.resource_id}</td>
                      <td className="py-2.5 pr-3 max-w-xs truncate" title={l.updated_value}>{l.updated_value || "—"}</td>
                      <td className="py-2.5">
                        <StatusBadge label={l.execution_status} variant={l.execution_status === "SUCCESS" ? "green" : "red"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={25} total={data.total} onPageChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
