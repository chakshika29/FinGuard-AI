-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 06: Credit Utilization & Governance Reporting
-- Sandbox Safe: Read-only SELECT and CTEs (no DML).
-- Note: Credit risk score is an educational demonstration model only.
-- ============================================================================

-- 1. Credit Utilization & Delinquency Exposure by Customer Segment
SELECT
  customer_segment,
  COUNT(*) AS total_accounts,
  ROUND(SUM(credit_limit), 2) AS total_credit_limit,
  ROUND(SUM(outstanding_balance), 2) AS total_outstanding_balance,
  ROUND(AVG(credit_utilization_ratio) * 100, 2) AS avg_utilization_pct,
  COUNTIF(credit_utilization_ratio >= 0.75) AS high_utilization_accounts,
  COUNTIF(repayment_status != 'CURRENT') AS overdue_accounts,
  ROUND(100.0 * COUNTIF(repayment_status != 'CURRENT') / NULLIF(COUNT(*), 0), 2) AS overdue_rate_pct
FROM `finguard_sandbox.credit_risk_analytics`
GROUP BY customer_segment
ORDER BY total_outstanding_balance DESC;

-- 2. Data Governance Quarantine & Remediation Summary Report
SELECT
  severity,
  remediation_status,
  COUNT(*) AS quarantined_count,
  COUNT(DISTINCT ingestion_job_id) AS affected_jobs,
  MIN(quarantined_at) AS earliest_incident,
  MAX(quarantined_at) AS latest_incident
FROM `finguard_sandbox.quarantined_records`
GROUP BY severity, remediation_status
ORDER BY quarantined_count DESC;
