export type UserRole = "Administrator" | "Data Steward" | "Risk Analyst";

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active?: boolean;
}

export type NavPage =
  | "overview"
  | "transactions"
  | "ingestion"
  | "quality"
  | "fraud"
  | "credit"
  | "catalog"
  | "lineage"
  | "policies"
  | "audit"
  | "reports"
  | "settings";

export interface SystemStatus {
  app_name: string;
  data_backend: "local" | "bigquery";
  local_engine: string;
  gcp_status: {
    configured: boolean;
    verified: boolean;
    mode: string;
    message?: string;
    project_id?: string;
  };
  datasets: Record<string, string>;
  warehouse_counts: {
    transactions: number;
    customers: number;
    accounts: number;
    merchants: number;
  };
  current_user_role: string;
}

export interface TransactionItem {
  transaction_id: string;
  customer_id: string;
  account_id: string;
  card_token_masked: string;
  transaction_timestamp: string;
  transaction_amount: number;
  currency: string;
  merchant_id: string;
  merchant_category: string;
  transaction_type: string;
  payment_method: string;
  transaction_country: string;
  transaction_city: string;
  device_id: string;
  transaction_status: string;
  fraud_risk_score: number;
  fraud_risk_level: string;
  risk_explanations: string[];
  customer_risk_category: string;
}

export interface IngestionJobItem {
  job_id: string;
  source_file: string;
  file_format: string;
  file_checksum: string;
  status: string;
  records_received: number;
  records_processed: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  quarantined_records: number;
  processing_duration_sec: number;
  idempotent_skip: boolean;
  failure_reason: string | null;
  triggered_by: string;
  backend_target: string;
  created_at: string | null;
  completed_at: string | null;
}

export interface QualityRuleItem {
  rule_id: string;
  rule_name: string;
  description: string;
  dataset: string;
  column_name: string;
  dimension: string;
  severity: string;
  threshold: number;
  enabled: boolean;
  owner: string;
  rule_type: string;
  rule_config: Record<string, unknown>;
  created_at: string | null;
  last_execution_date: string | null;
}

export interface FraudAlertItem {
  alert_id: string;
  transaction_id: string;
  customer_id: string;
  merchant_id: string;
  merchant_category: string;
  transaction_amount: number;
  transaction_country: string;
  transaction_timestamp: string;
  risk_score: number;
  risk_level: string;
  explanations: string[];
  ml_anomaly_score: number;
  investigation_status: string;
  assigned_analyst: string | null;
  analyst_notes: string;
  updated_at: string | null;
}
