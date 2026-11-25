import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  ClipboardList,
  Cloud,
  Database,
  FileDown,
  GitBranch,
  HardDrive,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Scale,
  Settings,
  ShieldCheck,
  Sun,
  UploadCloud,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { NavPage, SystemStatus } from "../types";

const NAV_ITEMS: { id: NavPage; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: "transactions", label: "Transactions", icon: <Activity className="w-4 h-4" /> },
  { id: "ingestion", label: "Data Ingestion", icon: <UploadCloud className="w-4 h-4" /> },
  { id: "quality", label: "Data Quality", icon: <BarChart3 className="w-4 h-4" /> },
  { id: "fraud", label: "Fraud Analytics", icon: <AlertTriangle className="w-4 h-4" /> },
  { id: "credit", label: "Credit Risk", icon: <Landmark className="w-4 h-4" /> },
  { id: "catalog", label: "Data Catalog", icon: <BookOpen className="w-4 h-4" /> },
  { id: "lineage", label: "Data Lineage", icon: <GitBranch className="w-4 h-4" /> },
  { id: "policies", label: "Governance Policies", icon: <Scale className="w-4 h-4" /> },
  { id: "audit", label: "Audit Logs", icon: <ClipboardList className="w-4 h-4" /> },
  { id: "reports", label: "Reports", icon: <FileDown className="w-4 h-4" /> },
  { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" /> },
];

export function DashboardLayout({
  activePage,
  onNavigate,
  systemStatus,
  darkMode,
  onToggleDark,
  children,
}: {
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
  systemStatus: SystemStatus | null;
  darkMode: boolean;
  onToggleDark: () => void;
  children: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isBigQuery = systemStatus?.data_backend === "bigquery";

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-navy-900 text-slate-200 flex flex-col border-r border-slate-800 transform transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-blue-600/20 border border-blue-400/30">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-white tracking-tight">FinGuard AI</div>
              <div className="text-[10px] text-blue-300 uppercase tracking-wider">Risk & Governance</div>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onNavigate(item.id);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  active
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-3 border-t border-slate-800 text-xs text-slate-400 space-y-2">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-slate-800/60">
            <Database className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span className="truncate">
              {systemStatus
                ? `${systemStatus.warehouse_counts.transactions.toLocaleString()} Curated Tx`
                : "Warehouse Ready"}
            </span>
          </div>
          <div className="px-2 text-[11px] text-slate-500">
            100% Synthetic Financial Data
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-base lg:text-lg font-semibold text-slate-900 dark:text-white capitalize">
              {NAV_ITEMS.find((i) => i.id === activePage)?.label}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden md:inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800">
              Portfolio Demo · Synthetic Data
            </span>
            {/* Backend Mode Indicator */}
            <div
              className={`hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                isBigQuery
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
                  : "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800"
              }`}
            >
              {isBigQuery ? <Cloud className="w-3.5 h-3.5" /> : <HardDrive className="w-3.5 h-3.5" />}
              <span>{isBigQuery ? "GCP BigQuery Mode" : "Local Mode (DuckDB)"}</span>
            </div>

            <button
              onClick={onToggleDark}
              aria-label="Toggle theme"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <div className="flex items-center gap-2.5 pl-2 border-l border-slate-200 dark:border-slate-700">
              <div className="text-right hidden md:block">
                <div className="text-xs font-semibold text-slate-900 dark:text-white">{user?.full_name}</div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">{user?.role}</div>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="p-2 rounded-lg text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-6 overflow-y-auto space-y-6">{children}</main>
      </div>
    </div>
  );
}
