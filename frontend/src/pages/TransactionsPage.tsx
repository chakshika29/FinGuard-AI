import { useEffect, useState } from "react";
import { Download, Search, X } from "lucide-react";
import { Banner, EmptyState, LoadingState, Pagination, riskVariant, StatusBadge } from "../components/UI";
import { api, downloadCsvReport, getErrorMessage } from "../services/api";
import { TransactionItem } from "../types";

export function TransactionsPage() {
  const [items, setItems] = useState<TransactionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [country, setCountry] = useState("");
  const [merchantCategory, setMerchantCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTx, setSelectedTx] = useState<any>(null);

  const fetchTx = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/api/transactions", {
        params: {
          page,
          page_size: 20,
          search: search || undefined,
          risk_level: riskLevel || undefined,
          status: status || undefined,
          country: country || undefined,
          merchant_category: merchantCategory || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
      });
      setItems(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTx();
  }, [page, riskLevel, status, country, merchantCategory, dateFrom, dateTo]);

  const openDetail = async (id: string) => {
    try {
      const res = await api.get(`/api/transactions/${id}`);
      setSelectedTx(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      {error && <Banner type="error" message={error} onClose={() => setError(null)} />}

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search transaction ID, customer, merchant, city..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setPage(1);
                  fetchTx();
                }
              }}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
            />
          </div>
          <button
            onClick={() => {
              setPage(1);
              fetchTx();
            }}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
          >
            Search
          </button>
          <button
            onClick={() => downloadCsvReport("transactions")}
            className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          <select value={riskLevel} onChange={(e) => { setPage(1); setRiskLevel(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
            <option value="">All Risk Levels</option>
            <option value="Critical Risk">Critical Risk</option>
            <option value="High Risk">High Risk</option>
            <option value="Medium Risk">Medium Risk</option>
            <option value="Low Risk">Low Risk</option>
          </select>
          <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
            <option value="">All Statuses</option>
            <option value="APPROVED">APPROVED</option>
            <option value="DECLINED">DECLINED</option>
            <option value="FAILED">FAILED</option>
            <option value="PENDING">PENDING</option>
          </select>
          <select value={country} onChange={(e) => { setPage(1); setCountry(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
            <option value="">All Countries</option>
            {["US", "GB", "CA", "IN", "SG", "DE", "FR", "AU", "JP"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select value={merchantCategory} onChange={(e) => { setPage(1); setMerchantCategory(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
            <option value="">All Merchant Categories</option>
            {["RETAIL", "GROCERY", "DINING", "TRAVEL_AIRLINES", "ELECTRONICS", "DIGITAL_GOODS", "CRYPTO_EXCHANGE", "WIRE_TRANSFER", "LUXURY_GOODS"].map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <input type="date" value={dateFrom} onChange={(e) => { setPage(1); setDateFrom(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" />
          <input type="date" value={dateTo} onChange={(e) => { setPage(1); setDateTo(e.target.value); }} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        {loading ? (
          <LoadingState />
        ) : items.length === 0 ? (
          <EmptyState title="No matching transactions" description="Adjust filters or ingest synthetic transaction batches." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 pr-3">Transaction ID</th>
                    <th className="py-2.5 pr-3">Customer</th>
                    <th className="py-2.5 pr-3">Card Token</th>
                    <th className="py-2.5 pr-3">Amount</th>
                    <th className="py-2.5 pr-3">Merchant Category</th>
                    <th className="py-2.5 pr-3">Country</th>
                    <th className="py-2.5 pr-3">Status</th>
                    <th className="py-2.5 pr-3">Risk Score</th>
                    <th className="py-2.5">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {items.map((tx) => (
                    <tr
                      key={tx.transaction_id}
                      onClick={() => openDetail(tx.transaction_id)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition"
                    >
                      <td className="py-2.5 pr-3 font-mono text-xs text-blue-600 dark:text-blue-400">{tx.transaction_id}</td>
                      <td className="py-2.5 pr-3 font-mono text-xs">{tx.customer_id}</td>
                      <td className="py-2.5 pr-3 font-mono text-xs text-slate-500">{tx.card_token_masked}</td>
                      <td className="py-2.5 pr-3 font-semibold">${tx.transaction_amount.toLocaleString()} {tx.currency}</td>
                      <td className="py-2.5 pr-3 text-xs">{tx.merchant_category}</td>
                      <td className="py-2.5 pr-3 text-xs">{tx.transaction_country}</td>
                      <td className="py-2.5 pr-3">
                        <StatusBadge label={tx.transaction_status} variant={tx.transaction_status === "APPROVED" ? "green" : "amber"} />
                      </td>
                      <td className="py-2.5 pr-3">
                        <StatusBadge label={`${tx.fraud_risk_score} (${tx.fraud_risk_level})`} variant={riskVariant(tx.fraud_risk_level)} />
                      </td>
                      <td className="py-2.5 text-xs text-slate-500">{tx.transaction_timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={20} total={total} onPageChange={setPage} />
          </>
        )}
      </div>

      {/* Transaction Detail Drawer */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 h-full overflow-y-auto p-6 shadow-2xl border-l border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold">{selectedTx.transaction_id}</h3>
                <p className="text-xs text-slate-500">Curated Transaction Lineage & Risk Context</p>
              </div>
              <button onClick={() => setSelectedTx(null)} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800">
                <div className="text-xs text-slate-500">Amount</div>
                <div className="font-bold text-lg">${selectedTx.transaction_amount.toLocaleString()} {selectedTx.currency}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800">
                <div className="text-xs text-slate-500">Fraud Risk Score</div>
                <div className="font-bold text-lg">{selectedTx.fraud_risk_score} / 100</div>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Customer / Segment</span>
                <span className="font-medium">{selectedTx.customer_id} ({selectedTx.customer_segment})</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Masked Card Token</span>
                <span className="font-mono">{selectedTx.card_token_masked}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Merchant</span>
                <span>{selectedTx.merchant_name || selectedTx.merchant_id} ({selectedTx.merchant_category})</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Location vs Home</span>
                <span>{selectedTx.transaction_city}, {selectedTx.transaction_country} (Home: {selectedTx.customer_home_country})</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Device & Source</span>
                <span>{selectedTx.device_id} · {selectedTx.source_system}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Ingestion Job ID</span>
                <span className="font-mono">{selectedTx.ingestion_job_id}</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">Explainable Risk Indicators</h4>
              {selectedTx.risk_explanations?.length > 0 ? (
                <ul className="space-y-1.5 text-xs bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 p-3 rounded-lg">
                  {selectedTx.risk_explanations.map((r: string, i: number) => (
                    <li key={i}>• {r}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">No elevated risk indicators triggered.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
