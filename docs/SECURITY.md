# Security, Access Control & Data Protection

## 1. Authentication & Role-Based Access Control (RBAC)
- **Password Hashing**: `bcrypt` with per-user random salt (`backend/app/core/security.py`).
- **Session Tokens**: Signed HS256 JWT tokens (`PyJWT`) with configurable expiration (`JWT_EXPIRE_MINUTES`).
- **Three Application Roles**:
  - **Administrator**: Full access to user management, governance policy toggles, system settings, ingestion, quality rules, and analytics.
  - **Data Steward**: Manage data quality rules, execute quality checks, update catalog metadata/ownership, upload/generate datasets, and remediate quarantined records.
  - **Risk Analyst**: Investigate fraud alerts, run ML anomaly evaluations, inspect transactions/credit risk, and export permitted CSV reports.

## 2. Input Validation, SQL Safety & Masking
- **Parameterized Queries**: All DuckDB and SQLAlchemy queries bind parameters via `?` placeholders or ORM expressions — never raw string interpolation of user search inputs.
- **Restricted File Uploads**: Only `.csv` and `.json` extensions are accepted, enforced with size limits (`MAX_UPLOAD_SIZE_MB=250`).
- **Sensitive Data Masking**: Synthetic `card_token` fields are masked (`****1234`) across transaction lists, detail drawers, credit accounts, and CSV/Power BI exports.
- **CORS & Secrets**: Origins and JWT/demo secrets are configured via `.env` and excluded from Git via `.gitignore`.

## 3. Audit Trail Limitations
- `AuditLog` is implemented as an **append-only application table** recording actor, role, action, resource, previous/updated values, timestamp, and status.
- **Explicit Limitation**: Database administrators with direct SQLite/filesystem access could modify the local file; this is an application-level audit demonstration, not a WORM-compliant regulatory ledger.
