import { useEffect, useState } from "react";
import { Banner, LoadingState, StatusBadge } from "../components/UI";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../services/api";

export function PoliciesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Administrator";
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadPolicies = async () => {
    try {
      const res = await api.get("/api/governance/policies");
      setPolicies(res.data);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const togglePolicy = async (p: any) => {
    try {
      await api.patch(`/api/governance/policies/${p.policy_id}`, { enabled: !p.enabled });
      setNotice({ type: "success", text: `Policy ${p.policy_id} updated.` });
      loadPolicies();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err) });
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      {notice && <Banner type={notice.type} message={notice.text} onClose={() => setNotice(null)} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {policies.map((p) => (
          <div key={p.policy_id} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3 shadow-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-xs font-mono text-blue-600">{p.policy_id} · {p.category}</div>
                <h3 className="text-base font-bold mt-0.5">{p.policy_name}</h3>
              </div>
              <StatusBadge
                label={p.compliance_status}
                variant={p.compliance_status === "COMPLIANT" ? "green" : p.compliance_status === "BREACHED" ? "red" : "slate"}
              />
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300">{p.description}</p>
            <div className="text-xs font-mono bg-slate-50 dark:bg-slate-800 p-2 rounded">
              Rule: {p.threshold_rule}
            </div>
            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-slate-500">Owner: {p.owner}</span>
              <button
                disabled={!isAdmin}
                onClick={() => togglePolicy(p)}
                className={`px-3 py-1 rounded font-semibold ${
                  p.enabled ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "bg-slate-200 text-slate-600"
                }`}
              >
                {p.enabled ? "Enforced" : "Disabled"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
