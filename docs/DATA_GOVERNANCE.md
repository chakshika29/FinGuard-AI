# Enterprise Data Governance Methodology

## 1. Governance Pillars Implemented in FinGuard AI

1. **Data Catalog & Metadata Management**: Every table across the 5 medallion layers is registered with business purpose, technical/business owners, data steward, schema metadata, live record count, quality score, classification, and retention policy.
2. **Data Ownership & Stewardship**: Clear separation between Business Owner (accountability), Technical Owner (platform reliability), and Data Steward (quality rule tuning and quarantine remediation).
3. **Business Glossary**: Standardized definitions and formulas for *Transaction Amount*, *Credit Utilization*, *Fraud Risk Score*, *Data Quality Score*, *Outstanding Balance*, *Delinquency*, *Suspicious Transaction*, and *Data Lineage*.
4. **Data Classification**: Four-tier sensitivity taxonomy (`Public`, `Internal`, `Confidential`, `Restricted`) paired with card token masking (`****1234`) in APIs, UI, and CSV exports.
5. **End-to-End Data Lineage**: Automated tracking of `job_id`, transformation name, source table, destination table, and record counts across `Source Files → Raw → Staging → Curated / Quarantine → Analytics → Dashboard`.
6. **7-Dimension Data Quality Framework**:
   - **Completeness**: Mandatory fields (`transaction_id`, `customer_id`).
   - **Accuracy**: Positive transaction amount and credit limit ranges.
   - **Consistency**: Standardized ISO country codes (`USA`/`United States` → `US`) and valid transaction statuses.
   - **Uniqueness**: Duplicate `transaction_id` detection within and across batches.
   - **Validity**: ISO-4217 currency codes and valid non-future UTC timestamps.
   - **Timeliness**: Freshness checks against configured age SLA.
   - **Referential Integrity**: Foreign-key checks against `customers` and `merchants` master tables.
7. **Zero Silent Data Loss (Quarantine Mandate)**: Invalid records are never silently dropped; they are preserved in `finguard_governance.quarantined_records` with failure reasons, failed rule IDs, severity, and steward remediation workflow (`OPEN → REVIEWED → RESOLVED / IGNORED`).

## 2. Transparent Quality Scoring Formula

$$\text{Rule Pass Rate} = \frac{\text{Total Evaluated} - \text{Failed Count}}{\text{Total Evaluated}} \times 100$$

$$\text{Overall Quality Score} = \frac{\sum_{i} (\text{PassRate}_i \times \text{Weight}_i)}{\sum_{i} \text{Weight}_i}$$

Where severity weights are: `CRITICAL = 4`, `HIGH = 3`, `MEDIUM = 2`, `LOW = 1`.
