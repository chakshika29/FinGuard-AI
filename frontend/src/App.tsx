import { useEffect, useState } from "react";
import { LoginPage } from "./components/LoginPage";
import { LoadingState } from "./components/UI";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CreditRiskPage } from "./pages/CreditRiskPage";
import { DataQualityPage } from "./pages/DataQualityPage";
import { FraudAnalyticsPage } from "./pages/FraudAnalyticsPage";
import { IngestionPage } from "./pages/IngestionPage";
import { LineagePage } from "./pages/LineagePage";
import { OverviewPage } from "./pages/OverviewPage";
import { PoliciesPage } from "./pages/PoliciesPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { api } from "./services/api";
import { NavPage, SystemStatus } from "./types";

function AuthenticatedApp() {
  const { user, loading } = useAuth();
  const [activePage, setActivePage] = useState<NavPage>("overview");
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem("finguard_theme") === "dark");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("finguard_theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    if (user) {
      api
        .get<SystemStatus>("/api/system/status")
        .then((res) => setSystemStatus(res.data))
        .catch(() => {});
    }
  }, [user, activePage]);

  if (loading) return <LoadingState message="Initializing FinGuard AI session..." />;
  if (!user) return <LoginPage />;

  const renderPage = () => {
    switch (activePage) {
      case "overview":
        return <OverviewPage />;
      case "transactions":
        return <TransactionsPage />;
      case "ingestion":
        return <IngestionPage />;
      case "quality":
        return <DataQualityPage />;
      case "fraud":
        return <FraudAnalyticsPage />;
      case "credit":
        return <CreditRiskPage />;
      case "catalog":
        return <CatalogPage />;
      case "lineage":
        return <LineagePage />;
      case "policies":
        return <PoliciesPage />;
      case "audit":
        return <AuditLogsPage />;
      case "reports":
        return <ReportsPage />;
      case "settings":
        return (
          <SettingsPage
            systemStatus={systemStatus}
            darkMode={darkMode}
            onToggleDark={() => setDarkMode((d) => !d)}
          />
        );
    }
  };

  return (
    <DashboardLayout
      activePage={activePage}
      onNavigate={setActivePage}
      systemStatus={systemStatus}
      darkMode={darkMode}
      onToggleDark={() => setDarkMode((d) => !d)}
    >
      {renderPage()}
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}
