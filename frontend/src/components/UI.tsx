import React from "react";
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Info, Loader2 } from "lucide-react";

export function KpiCard({
  title,
  value,
  subtitle,
  icon,
  tone = "blue",
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  tone?: "blue" | "emerald" | "amber" | "red" | "indigo" | "slate";
}) {
  const toneClasses: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400",
    emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400",
    red: "bg-red-50 text-red-600 dark:bg-red-950/60 dark:text-red-400",
    indigo: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400",
    slate: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  };

  const valStr = String(value);
  const valSizeClass = valStr.length > 14 ? "text-base sm:text-lg break-all" : "text-2xl";

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm hover:shadow-md transition">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</p>
          <p className={`${valSizeClass} font-bold text-slate-900 dark:text-white mt-1`}>{value}</p>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate" title={subtitle}>{subtitle}</p>}
        </div>
        <div className={`p-2.5 rounded-lg shrink-0 ${toneClasses[tone]}`}>{icon}</div>
      </div>
    </div>
  );
}

export function StatusBadge({ label, variant = "slate" }: { label: string; variant?: "green" | "amber" | "red" | "blue" | "slate" | "purple" }) {
  const styles: Record<string, string> = {
    green: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800",
    amber: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800",
    red: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800",
    blue: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800",
    purple: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/50 dark:text-purple-300 dark:border-purple-800",
    slate: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${styles[variant]}`}>
      {label}
    </span>
  );
}

export function riskVariant(level: string): "green" | "amber" | "red" | "blue" | "slate" {
  const l = level.toLowerCase();
  if (l.includes("critical")) return "red";
  if (l.includes("high")) return "amber";
  if (l.includes("medium")) return "blue";
  if (l.includes("low")) return "green";
  return "slate";
}

export function LoadingState({ message = "Loading enterprise telemetry..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-500 dark:text-slate-400">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
      <Info className="w-8 h-8 text-slate-400 mb-2" />
      <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</h4>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">{description}</p>
    </div>
  );
}

export function Banner({
  type,
  message,
  onClose,
}: {
  type: "error" | "success" | "info";
  message: string;
  onClose?: () => void;
}) {
  const styles = {
    error: "bg-red-50 border-red-200 text-red-800 dark:bg-red-950/60 dark:border-red-800 dark:text-red-200",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/60 dark:border-emerald-800 dark:text-emerald-200",
    info: "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950/60 dark:border-blue-800 dark:text-blue-200",
  };
  return (
    <div className={`p-3 rounded-lg border text-sm flex items-center justify-between gap-2 ${styles[type]}`}>
      <div className="flex items-center gap-2">
        {type === "error" ? <AlertCircle className="w-4 h-4 shrink-0" /> : <CheckCircle2 className="w-4 h-4 shrink-0" />}
        <span>{message}</span>
      </div>
      {onClose && (
        <button onClick={onClose} className="text-xs font-semibold underline">
          Dismiss
        </button>
      )}
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 pt-3">
      <span>
        Showing {total === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()} records
      </span>
      <div className="flex items-center gap-1.5">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-1"
        >
          <ChevronLeft className="w-3.5 h-3.5" /> Prev
        </button>
        <span className="px-2 font-medium">
          Page {page} / {totalPages}
        </span>
        <button
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-1"
        >
          Next <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
