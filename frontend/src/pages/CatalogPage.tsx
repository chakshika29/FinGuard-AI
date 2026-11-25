import { useEffect, useState } from "react";
import { BookOpen, Search } from "lucide-react";
import { Banner, LoadingState, StatusBadge } from "../components/UI";
import { api, getErrorMessage } from "../services/api";

export function CatalogPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [glossary, setGlossary] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<"catalog" | "glossary">("catalog");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get("/api/governance/catalog", { params: { search: search || undefined } }),
      api.get("/api/governance/glossary"),
    ])
      .then(([cRes, gRes]) => {
        setCatalog(cRes.data);
        setGlossary(gRes.data);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [search]);

  if (loading) return <LoadingState />;
  if (error) return <Banner type="error" message={error} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            onClick={() => setTab("catalog")}
            className={`px-4 py-2 rounded-lg text-sm font-semibold ${tab === "catalog" ? "bg-blue-600 text-white" : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"}`}
          >
            Enterprise Data Catalog ({catalog.length})
          </button>
          <button
            onClick={() => setTab("glossary")}
            className={`px-4 py-2 rounded-lg text-sm font-semibold ${tab === "glossary" ? "bg-blue-600 text-white" : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"}`}
          >
            Business Glossary ({glossary.length})
          </button>
        </div>

        {tab === "catalog" && (
          <div className="relative min-w-[260px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter tables or datasets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
            />
          </div>
        )}
      </div>

      {tab === "catalog" ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {catalog.map((c) => (
            <div key={c.id} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-xs font-mono text-blue-600 dark:text-blue-400">{c.dataset_name}</div>
                  <h3 className="text-base font-bold font-mono">{c.table_name}</h3>
                </div>
                <StatusBadge
                  label={c.data_classification}
                  variant={c.data_classification === "Restricted" ? "red" : c.data_classification === "Confidential" ? "amber" : "blue"}
                />
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300">{c.description}</p>
              <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg">
                <div><span className="text-slate-500">Business Owner:</span> <span className="font-medium">{c.business_owner}</span></div>
                <div><span className="text-slate-500">Data Steward:</span> <span className="font-medium">{c.data_steward}</span></div>
                <div><span className="text-slate-500">Records:</span> <span className="font-mono font-semibold">{c.record_count.toLocaleString()}</span></div>
                <div><span className="text-slate-500">Quality Score:</span> <span className="font-semibold text-emerald-600">{c.quality_score}%</span></div>
                <div className="col-span-2"><span className="text-slate-500">Retention:</span> {c.retention_policy}</div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {c.schema.map((col: any, idx: number) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[11px] font-mono">
                    {col.name}: {col.type}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {glossary.map((g) => (
            <div key={g.id} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-blue-600" /> {g.term}
                </h3>
                <StatusBadge label={g.classification} variant="blue" />
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300">{g.definition}</p>
              {g.formula_or_rule && (
                <div className="text-xs font-mono bg-slate-50 dark:bg-slate-800 p-2 rounded">
                  Rule/Formula: {g.formula_or_rule}
                </div>
              )}
              <div className="text-[11px] text-slate-500">Owner: {g.owner} · Datasets: {g.related_datasets}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
