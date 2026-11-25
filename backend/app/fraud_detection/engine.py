"""Explainable Fraud Risk Analytics Engine & Optional IsolationForest Anomaly Detector.

DISCLAIMER:
Suspicious transactions identified by this engine are risk indicators for analyst
investigation, NOT confirmed fraud.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session
from backend.app.models.metadata import FraudAlert, MLModelEvaluation

try:
    from sklearn.ensemble import IsolationForest as SklearnIsolationForest
    SKLEARN_IF_AVAILABLE = True
except ImportError:
    SklearnIsolationForest = None
    SKLEARN_IF_AVAILABLE = False


class _IsolationTreeNode:
    __slots__ = ("split_attr", "split_val", "left", "right", "size")

    def __init__(self, split_attr=None, split_val=None, left=None, right=None, size=0):
        self.split_attr = split_attr
        self.split_val = split_val
        self.left = left
        self.right = right
        self.size = size


class PureNumpyIsolationForest:
    """Liu-Ting-Zhou Isolation Forest implemented in pure NumPy (used if WDAC blocks sklearn.tree DLLs)."""

    def __init__(self, n_estimators: int = 100, max_samples: int = 256, contamination: float = 0.03, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.rng = np.random.default_rng(random_state)
        self.trees: list[_IsolationTreeNode] = []
        self.height_limit = 8
        self.threshold_ = 0.5

    @staticmethod
    def _c_factor(n: int) -> float:
        if n <= 1:
            return 0.0
        if n == 2:
            return 1.0
        return 2.0 * (np.log(n - 1.0) + 0.5772156649) - (2.0 * (n - 1.0) / n)

    def _build_tree(self, X: np.ndarray, depth: int) -> _IsolationTreeNode:
        n_samples, n_features = X.shape
        if depth >= self.height_limit or n_samples <= 1:
            return _IsolationTreeNode(size=n_samples)
        attr = int(self.rng.integers(0, n_features))
        col = X[:, attr]
        c_min, c_max = float(col.min()), float(col.max())
        if c_min == c_max:
            return _IsolationTreeNode(size=n_samples)
        split_val = float(self.rng.uniform(c_min, c_max))
        left_mask = col < split_val
        return _IsolationTreeNode(
            split_attr=attr,
            split_val=split_val,
            left=self._build_tree(X[left_mask], depth + 1),
            right=self._build_tree(X[~left_mask], depth + 1),
        )

    def _path_length_batch(self, X: np.ndarray, node: _IsolationTreeNode, depth: int) -> np.ndarray:
        if node.left is None or node.right is None:
            return np.full(len(X), depth + self._c_factor(node.size), dtype=float)
        mask = X[:, node.split_attr] < node.split_val
        out = np.empty(len(X), dtype=float)
        if mask.any():
            out[mask] = self._path_length_batch(X[mask], node.left, depth + 1)
        if (~mask).any():
            out[~mask] = self._path_length_batch(X[~mask], node.right, depth + 1)
        return out

    def fit(self, X: np.ndarray) -> "PureNumpyIsolationForest":
        n_samples = len(X)
        sub_n = min(self.max_samples, n_samples)
        self.height_limit = max(1, int(np.ceil(np.log2(max(2, sub_n)))))
        self.trees = []
        for _ in range(self.n_estimators):
            idx = self.rng.choice(n_samples, size=sub_n, replace=False)
            self.trees.append(self._build_tree(X[idx], 0))
        scores = self.decision_function(X)
        self.threshold_ = float(np.quantile(scores, self.contamination))
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        sub_n = min(self.max_samples, max(2, len(X)))
        c_n = max(1e-6, self._c_factor(sub_n))
        avg_depths = np.mean([self._path_length_batch(X, t, 0) for t in self.trees], axis=0)
        anomaly_s = np.power(2.0, -avg_depths / c_n)
        return 0.5 - anomaly_s  # Negative = anomaly, matching sklearn convention

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.where(self.decision_function(X) < self.threshold_, -1, 1)


HIGH_RISK_MERCHANTS = {"CRYPTO_EXCHANGE", "WIRE_TRANSFER", "ELECTRONICS", "LUXURY_GOODS", "DIGITAL_GOODS"}
CRITICAL_RISK_MERCHANTS = {"CRYPTO_EXCHANGE", "WIRE_TRANSFER"}


def classify_risk_level(score: float) -> str:
    if score >= 75.0:
        return "Critical Risk"
    if score >= 50.0:
        return "High Risk"
    if score >= 25.0:
        return "Medium Risk"
    return "Low Risk"


def score_transactions_and_generate_alerts(db: Session, df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized explainable fraud risk scoring (0-100) with transparent per-transaction reasons."""
    if df.empty:
        return df

    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    scored = df.copy()
    scored["transaction_timestamp"] = pd.to_datetime(scored["transaction_timestamp"], errors="coerce")

    # Fetch customer home country & historical baseline from DuckDB if available
    cust_home_map: dict[str, str] = {}
    with duckdb_session() as conn:
        cust_df = conn.execute(f"SELECT customer_id, home_country FROM {curated}.customers").fetchdf()
        if not cust_df.empty:
            cust_home_map = dict(zip(cust_df["customer_id"], cust_df["home_country"]))

    # Sort first so all Series share the exact same 0..N-1 index
    scored = scored.sort_values(["customer_id", "transaction_timestamp"]).reset_index(drop=True)

    # Customer-level average spending within batch
    cust_mean_amt = scored.groupby("customer_id")["transaction_amount"].transform("mean").clip(lower=50.0)
    batch_global_mean = float(scored["transaction_amount"].mean()) if len(scored) > 0 else 150.0

    # Velocity: count transactions per customer within +/- 15 minutes using sorted epoch diff
    ts_sec = scored["transaction_timestamp"].astype("int64") // 10**9
    same_cust_prev = scored["customer_id"] == scored["customer_id"].shift(1)
    same_cust_next = scored["customer_id"] == scored["customer_id"].shift(-1)
    prev_gap = np.where(same_cust_prev, ts_sec - ts_sec.shift(1).fillna(0), 999999)
    next_gap = np.where(same_cust_next, ts_sec.shift(-1).fillna(0) - ts_sec, 999999)
    velocity_burst = (prev_gap <= 900) | (next_gap <= 900)

    # Geo mismatch vs customer home_country
    home_countries = scored["customer_id"].map(cust_home_map).fillna(scored["transaction_country"])
    geo_mismatch = scored["transaction_country"] != home_countries

    # Device anomaly (unrecognized anomaly prefix or device shared across >= 3 customers)
    device_cust_counts = scored.groupby("device_id")["customer_id"].transform("nunique")
    device_anomaly = scored["device_id"].str.startswith("DEV-ANOM") | (device_cust_counts >= 3)

    # Rule triggers (vectorized boolean masks)
    r_extreme_amt = scored["transaction_amount"] >= 4500.0
    r_spike_vs_hist = (scored["transaction_amount"] >= cust_mean_amt * 3.5) & (scored["transaction_amount"] >= 800.0)
    r_high_vs_global = scored["transaction_amount"] >= max(2500.0, batch_global_mean * 4.5)
    r_velocity = velocity_burst
    r_geo = geo_mismatch
    r_failed = scored["transaction_status"].isin(["FAILED", "DECLINED"])
    r_crit_merch = scored["merchant_category"].isin(CRITICAL_RISK_MERCHANTS)
    r_high_merch = scored["merchant_category"].isin(HIGH_RISK_MERCHANTS) & (~r_crit_merch)
    r_device = device_anomaly
    r_high_util = (scored["credit_limit"] > 0) & ((scored["outstanding_balance"] / scored["credit_limit"]) >= 0.85)
    r_high_risk_cust = scored["customer_risk_category"] == "HIGH"

    # Weighted additive score (0-100)
    raw_score = (
        np.where(r_extreme_amt, 30.0, 0.0)
        + np.where(r_spike_vs_hist, 22.0, 0.0)
        + np.where(r_high_vs_global, 12.0, 0.0)
        + np.where(r_velocity, 26.0, 0.0)
        + np.where(r_geo, 22.0, 0.0)
        + np.where(r_failed, 14.0, 0.0)
        + np.where(r_crit_merch, 22.0, 0.0)
        + np.where(r_high_merch, 10.0, 0.0)
        + np.where(r_device, 24.0, 0.0)
        + np.where(r_high_util, 8.0, 0.0)
        + np.where(r_high_risk_cust, 7.0, 0.0)
    )
    risk_scores = np.round(np.clip(raw_score, 0.0, 100.0), 2)
    risk_levels = np.select(
        [risk_scores >= 75.0, risk_scores >= 50.0, risk_scores >= 25.0],
        ["Critical Risk", "High Risk", "Medium Risk"],
        default="Low Risk",
    )

    scored["fraud_risk_score"] = risk_scores
    scored["fraud_risk_level"] = risk_levels
    scored["ml_anomaly_score"] = 0.0

    # Generate transparent explanation JSON only for scores >= 25 (Low Risk gets empty/minimal list fast)
    explanations_list: list[str] = ["[]"] * len(scored)
    flagged_indices = np.where(risk_scores >= 25.0)[0]

    for idx in flagged_indices:
        reasons: list[str] = []
        if r_extreme_amt.iloc[idx] or r_spike_vs_hist.iloc[idx]:
            reasons.append("Transaction amount significantly exceeds historical spending baseline.")
        if r_velocity[idx]:
            reasons.append("Multiple transactions detected within a 15-minute velocity window.")
        if r_geo.iloc[idx]:
            reasons.append("Transaction country differs from customer home geography.")
        if r_device.iloc[idx]:
            reasons.append("Unusual or shared device fingerprint detected.")
        if r_failed.iloc[idx]:
            reasons.append("Transaction associated with failed or declined authorization attempt.")
        if r_crit_merch.iloc[idx] or r_high_merch.iloc[idx]:
            reasons.append(f"Elevated-risk merchant category ({scored['merchant_category'].iloc[idx]}).")
        if r_high_util.iloc[idx]:
            reasons.append("Account credit utilization exceeds 85% threshold.")
        if r_high_risk_cust.iloc[idx]:
            reasons.append("Customer profile carries elevated baseline risk tier.")
        explanations_list[idx] = json.dumps(reasons)

    scored["risk_explanations"] = explanations_list

    # Create FraudAlert records for High & Critical Risk transactions (up to batch cap to avoid SQLite bloat on 1M runs, prioritize highest scores)
    high_risk_df = scored[scored["fraud_risk_score"] >= 50.0].sort_values("fraud_risk_score", ascending=False).head(5000)
    if not high_risk_df.empty:
        existing_alert_tx = {
            r[0] for r in db.query(FraudAlert.transaction_id).filter(
                FraudAlert.transaction_id.in_(high_risk_df["transaction_id"].tolist())
            ).all()
        }
        now = datetime.now(timezone.utc)
        for row in high_risk_df.itertuples(index=False):
            if row.transaction_id in existing_alert_tx:
                continue
            db.add(
                FraudAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:10].upper()}",
                    transaction_id=row.transaction_id,
                    customer_id=row.customer_id,
                    merchant_id=row.merchant_id,
                    merchant_category=row.merchant_category,
                    transaction_amount=float(row.transaction_amount),
                    transaction_country=row.transaction_country,
                    transaction_timestamp=str(row.transaction_timestamp),
                    risk_score=float(row.fraud_risk_score),
                    risk_level=row.fraud_risk_level,
                    explanations_json=row.risk_explanations,
                    ml_anomaly_score=float(row.ml_anomaly_score),
                    investigation_status="OPEN",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.flush()

    return scored


def train_and_evaluate_isolation_forest(db: Session, contamination: float = 0.03) -> dict[str, Any]:
    """Train IsolationForest without label leakage and evaluate against held-out synthetic fraud_label."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    with duckdb_session() as conn:
        df = conn.execute(f"""
            SELECT
                t.transaction_id,
                t.transaction_amount,
                t.credit_limit,
                t.outstanding_balance,
                t.merchant_category,
                t.transaction_status,
                t.transaction_country,
                t.device_id,
                t.customer_risk_category,
                t.fraud_label,
                COALESCE(c.home_country, t.transaction_country) AS home_country
            FROM {curated}.transactions t
            LEFT JOIN {curated}.customers c ON t.customer_id = c.customer_id
        """).fetchdf()

    if len(df) < 50:
        raise ValueError("At least 50 curated transactions are required to train and evaluate Isolation Forest.")

    # Engineer strictly non-label numerical features (NO fraud_label in X!)
    features = pd.DataFrame(index=df.index)
    features["log_amount"] = np.log1p(df["transaction_amount"].clip(lower=0.0))
    features["amt_to_limit_ratio"] = np.where(df["credit_limit"] > 0, df["transaction_amount"] / df["credit_limit"], 0.0)
    features["utilization_ratio"] = np.where(df["credit_limit"] > 0, df["outstanding_balance"] / df["credit_limit"], 0.0)
    features["is_geo_mismatch"] = (df["transaction_country"] != df["home_country"]).astype(float)
    features["is_high_risk_merchant"] = df["merchant_category"].isin(HIGH_RISK_MERCHANTS).astype(float)
    features["is_failed_or_declined"] = df["transaction_status"].isin(["FAILED", "DECLINED"]).astype(float)
    features["is_anom_device"] = df["device_id"].str.startswith("DEV-ANOM").astype(float)
    features["is_high_risk_customer"] = (df["customer_risk_category"] == "HIGH").astype(float)

    feature_names = list(features.columns)
    y = df["fraud_label"].astype(int).to_numpy()

    # Proper stratified train/test split (or standard split if only 1 class exists)
    stratify_arg = y if len(np.unique(y)) > 1 and np.min(np.bincount(y)) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        features.to_numpy(), y, test_size=0.30, random_state=42, stratify=stratify_arg
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    X_all_scaled = scaler.transform(features.to_numpy())

    # IsolationForest is unsupervised (trained on X_train_scaled without y_train)
    contam = min(0.25, max(0.005, contamination))
    if SKLEARN_IF_AVAILABLE and SklearnIsolationForest is not None:
        model = SklearnIsolationForest(
            n_estimators=150,
            contamination=contam,
            random_state=42,
            n_jobs=-1,
        )
        engine_label = "IsolationForest (scikit-learn)"
    else:
        model = PureNumpyIsolationForest(
            n_estimators=120,
            max_samples=256,
            contamination=contam,
            random_state=42,
        )
        engine_label = "IsolationForest (Pure-NumPy Fallback)"
    model.fit(X_train_scaled)

    # Evaluate on held-out test split
    test_preds_raw = model.predict(X_test_scaled)  # -1 anomaly, 1 normal
    y_pred = (test_preds_raw == -1).astype(int)
    # Higher score = more anomalous
    test_scores = -model.decision_function(X_test_scaled)
    all_scores = np.round(np.clip((-model.decision_function(X_all_scaled) + 0.5) * 100.0, 0.0, 100.0), 2)

    precision = round(float(precision_score(y_test, y_pred, zero_division=0)), 4)
    recall = round(float(recall_score(y_test, y_pred, zero_division=0)), 4)
    f1 = round(float(f1_score(y_test, y_pred, zero_division=0)), 4)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    tn, fp, fn, tp = [int(x) for x in cm.ravel()]
    fpr = round(fp / max(1, fp + tn), 4)
    pr_auc = round(float(average_precision_score(y_test, test_scores)) if len(np.unique(y_test)) > 1 else 0.0, 4)

    # Persist ML anomaly scores back to DuckDB curated.transactions
    score_df = pd.DataFrame({
        "transaction_id": df["transaction_id"],
        "ml_anomaly_score": all_scores,
    })
    with duckdb_session() as conn:
        conn.register("tmp_ml_scores", score_df)
        conn.execute(f"""
            UPDATE {curated}.transactions AS t
            SET ml_anomaly_score = s.ml_anomaly_score
            FROM tmp_ml_scores AS s
            WHERE t.transaction_id = s.transaction_id
        """)
        conn.unregister("tmp_ml_scores")

    cm_dict = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
    eval_record = MLModelEvaluation(
        model_name=engine_label,
        train_size=len(X_train),
        test_size=len(X_test),
        precision=precision,
        recall=recall,
        f1_score=f1,
        false_positive_rate=fpr,
        pr_auc=pr_auc,
        confusion_matrix_json=json.dumps(cm_dict),
        feature_list_json=json.dumps(feature_names),
        notes="Evaluated on 30% held-out split against synthetic fraud_label. Zero label leakage; fraud_label excluded from training features.",
        evaluated_at=datetime.now(timezone.utc),
    )
    db.add(eval_record)
    db.commit()

    return {
        "model_name": eval_record.model_name,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": fpr,
        "pr_auc": pr_auc,
        "confusion_matrix": cm_dict,
        "features": feature_names,
        "notes": eval_record.notes,
        "evaluated_at": eval_record.evaluated_at.isoformat(),
    }
