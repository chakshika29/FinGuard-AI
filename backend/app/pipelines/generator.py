"""Reproducible synthetic financial transaction, customer, account, and merchant generator.

IMPORTANT DISCLAIMER:
All generated records are 100% synthetic. No real customer PII, credit card numbers,
or actual financial accounts are used or stored anywhere in this platform.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "INR", "SGD", "AUD", "JPY"]
COUNTRIES = ["US", "GB", "CA", "IN", "SG", "DE", "FR", "AU", "JP"]
CITY_BY_COUNTRY = {
    "US": ["New York", "Chicago", "San Francisco", "Austin", "Miami"],
    "GB": ["London", "Manchester", "Edinburgh"],
    "CA": ["Toronto", "Vancouver", "Montreal"],
    "IN": ["Mumbai", "Bengaluru", "Delhi", "Hyderabad"],
    "SG": ["Singapore"],
    "DE": ["Frankfurt", "Berlin", "Munich"],
    "FR": ["Paris", "Lyon"],
    "AU": ["Sydney", "Melbourne"],
    "JP": ["Tokyo", "Osaka"],
}
MERCHANT_CATEGORIES = [
    ("RETAIL", "LOW"),
    ("GROCERY", "LOW"),
    ("DINING", "LOW"),
    ("TRAVEL_AIRLINES", "MEDIUM"),
    ("HOTEL_LODGING", "MEDIUM"),
    ("ELECTRONICS", "HIGH"),
    ("DIGITAL_GOODS", "HIGH"),
    ("CRYPTO_EXCHANGE", "CRITICAL"),
    ("WIRE_TRANSFER", "CRITICAL"),
    ("LUXURY_GOODS", "HIGH"),
]
TRANSACTION_TYPES = ["PURCHASE", "ONLINE_PAYMENT", "CONTACTLESS", "ATM_WITHDRAWAL", "RECURRING"]
PAYMENT_METHODS = ["CREDIT_CARD", "VIRTUAL_CARD", "MOBILE_WALLET", "CHIP_PIN"]
TRANSACTION_STATUSES = ["APPROVED", "APPROVED", "APPROVED", "APPROVED", "DECLINED", "PENDING", "FAILED"]
REPAYMENT_STATUSES = ["CURRENT", "CURRENT", "CURRENT", "CURRENT", "PAST_DUE_30", "PAST_DUE_60", "PAST_DUE_90", "DEFAULT"]
SEGMENTS = ["RETAIL_PRIME", "PREMIUM_CARD", "SMALL_BUSINESS", "EMERGING_CREDIT"]
RISK_CATEGORIES = ["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH"]
INCOME_BANDS = ["$40k-$75k", "$75k-$120k", "$120k-$200k", "$200k+"]
SOURCE_SYSTEMS = ["CORE_CARD_AUTH_V2", "DIGITAL_WALLET_GW", "MERCHANT_ACQUIRER_FEED"]


def generate_synthetic_dataset(
    num_records: int = 10000,
    seed: int = 42,
    output_dir: str | Path = "data/raw",
    inject_quality_issues: bool = True,
    quality_issue_rate: float = 0.03,
    fraud_rate: float = 0.025,
    file_format: str = "csv",
    prefix: str = "synthetic_batch",
) -> dict[str, Any]:
    """Generate reproducible synthetic customers, accounts, merchants, transactions, and ground-truth manifest."""
    rng = np.random.default_rng(seed)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    num_customers = max(250, min(25000, num_records // 10))
    num_merchants = max(60, min(1500, num_records // 50))

    # 1. Generate Customers
    customer_ids = [f"CUST-{i:06d}" for i in range(1, num_customers + 1)]
    home_countries = rng.choice(COUNTRIES, size=num_customers, p=[0.42, 0.14, 0.10, 0.12, 0.06, 0.05, 0.04, 0.04, 0.03])
    home_cities = [rng.choice(CITY_BY_COUNTRY[c]) for c in home_countries]
    customer_segments = rng.choice(SEGMENTS, size=num_customers, p=[0.45, 0.25, 0.15, 0.15])
    customer_risks = rng.choice(RISK_CATEGORIES, size=num_customers)
    income_bands = rng.choice(INCOME_BANDS, size=num_customers)
    open_days_ago = rng.integers(90, 2500, size=num_customers)
    base_date = datetime(2026, 11, 20, tzinfo=timezone.utc)
    open_dates = [(base_date - timedelta(days=int(d))).strftime("%Y-%m-%d") for d in open_days_ago]

    customers_df = pd.DataFrame({
        "customer_id": customer_ids,
        "full_name_synthetic": [f"Synthetic_Customer_{i:06d}" for i in range(1, num_customers + 1)],
        "customer_segment": customer_segments,
        "customer_risk_category": customer_risks,
        "home_country": home_countries,
        "home_city": home_cities,
        "income_band": income_bands,
        "account_open_date": open_dates,
    })

    # 2. Generate Accounts (1 account per customer for clean mapping + realistic credit profiles)
    account_ids = [f"ACCT-{i:06d}" for i in range(1, num_customers + 1)]
    card_tokens = [f"TOK-{rng.integers(100000, 999999)}-{i % 9000 + 1000:04d}" for i in range(1, num_customers + 1)]
    credit_limits = np.round(rng.choice([3000, 5000, 10000, 15000, 25000, 50000, 75000], size=num_customers, p=[0.15, 0.20, 0.25, 0.18, 0.12, 0.07, 0.03]), 2)
    util_factors = np.clip(rng.beta(2.2, 4.5, size=num_customers), 0.02, 0.98)
    outstanding_balances = np.round(credit_limits * util_factors, 2)
    repayment_statuses = rng.choice(REPAYMENT_STATUSES, size=num_customers)
    delinquency_map = {"CURRENT": 0, "PAST_DUE_30": 35, "PAST_DUE_60": 68, "PAST_DUE_90": 96, "DEFAULT": 140}
    delinquency_days = [delinquency_map[s] for s in repayment_statuses]

    accounts_df = pd.DataFrame({
        "account_id": account_ids,
        "customer_id": customer_ids,
        "card_token": card_tokens,
        "credit_limit": credit_limits,
        "outstanding_balance": outstanding_balances,
        "repayment_status": repayment_statuses,
        "delinquency_days": delinquency_days,
        "account_status": np.where(np.array(repayment_statuses) == "DEFAULT", "SUSPENDED", "ACTIVE"),
    })

    # 3. Generate Merchants
    merchant_ids = [f"MERCH-{i:05d}" for i in range(1, num_merchants + 1)]
    cat_indices = rng.integers(0, len(MERCHANT_CATEGORIES), size=num_merchants)
    m_cats = [MERCHANT_CATEGORIES[idx][0] for idx in cat_indices]
    m_tiers = [MERCHANT_CATEGORIES[idx][1] for idx in cat_indices]
    m_countries = rng.choice(COUNTRIES, size=num_merchants)

    merchants_df = pd.DataFrame({
        "merchant_id": merchant_ids,
        "merchant_name": [f"Synth_{m_cats[i].title()}_{i+1:03d}" for i in range(num_merchants)],
        "merchant_category": m_cats,
        "merchant_country": m_countries,
        "merchant_risk_tier": m_tiers,
    })

    # 4. Generate Clean Base Transactions (Vectorized)
    cust_idx = rng.integers(0, num_customers, size=num_records)
    merch_idx = rng.integers(0, num_merchants, size=num_records)

    tx_ids = np.array([f"TXN-{seed}-{i:08d}" for i in range(1, num_records + 1)], dtype=object)
    tx_cust_ids = np.array(customer_ids, dtype=object)[cust_idx]
    tx_acct_ids = np.array(account_ids, dtype=object)[cust_idx]
    tx_card_tokens = np.array(card_tokens, dtype=object)[cust_idx]
    tx_credit_limits = credit_limits[cust_idx]
    tx_balances = outstanding_balances[cust_idx]
    tx_repay = np.array(repayment_statuses, dtype=object)[cust_idx]
    tx_cust_risk = np.array(customer_risks, dtype=object)[cust_idx]
    tx_home_country = home_countries[cust_idx]

    tx_merch_ids = np.array(merchant_ids, dtype=object)[merch_idx]
    tx_merch_cats = np.array(m_cats, dtype=object)[merch_idx]

    # Timestamps over the last 90 days
    seconds_offset = rng.integers(0, 90 * 86400, size=num_records)
    base_ts = int(datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    tx_epoch = base_ts - seconds_offset
    tx_timestamps = pd.to_datetime(tx_epoch, unit="s", utc=True).strftime("%Y-%m-%dT%H:%M:%SZ").to_numpy(dtype=object)

    # Normal amounts log-normal around $45-$280
    tx_amounts = np.round(np.clip(rng.lognormal(mean=4.2, sigma=0.9, size=num_records), 2.50, 4500.0), 2).astype(object)
    tx_currencies = np.where(tx_home_country == "US", "USD", rng.choice(SUPPORTED_CURRENCIES, size=num_records))
    tx_types = rng.choice(TRANSACTION_TYPES, size=num_records)
    tx_methods = rng.choice(PAYMENT_METHODS, size=num_records)
    tx_countries = tx_home_country.copy().astype(object)
    tx_cities = np.array([rng.choice(CITY_BY_COUNTRY[c]) for c in tx_countries], dtype=object)
    tx_devices = np.array([f"DEV-{c_idx % 5000:05d}-{rng.integers(1, 3)}" for c_idx in cust_idx], dtype=object)
    tx_statuses = rng.choice(TRANSACTION_STATUSES, size=num_records)
    tx_sources = rng.choice(SOURCE_SYSTEMS, size=num_records)
    ingestion_ts = np.full(num_records, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), dtype=object)

    # 5. Inject Realistic Fraud Patterns (Synthetic Labels)
    fraud_labels = np.zeros(num_records, dtype=int)
    n_fraud = max(1, int(num_records * fraud_rate))
    fraud_indices = rng.choice(num_records, size=n_fraud, replace=False)
    fraud_labels[fraud_indices] = 1

    # Pattern mix across fraudulent indices
    for idx_pos, idx in enumerate(fraud_indices):
        pattern = idx_pos % 4
        if pattern == 0:
            # High amount + high-risk merchant
            tx_amounts[idx] = round(float(rng.uniform(4800.0, 28500.0)), 2)
            tx_merch_cats[idx] = rng.choice(["CRYPTO_EXCHANGE", "WIRE_TRANSFER", "ELECTRONICS", "LUXURY_GOODS"])
        elif pattern == 1:
            # Geo-hopping foreign country + device anomaly + high amount
            foreign = rng.choice([c for c in COUNTRIES if c != tx_home_country[idx]])
            tx_countries[idx] = foreign
            tx_cities[idx] = rng.choice(CITY_BY_COUNTRY[foreign])
            tx_devices[idx] = f"DEV-ANOM-{rng.integers(90000, 99999)}"
            tx_amounts[idx] = round(float(rng.uniform(1800.0, 12000.0)), 2)
        elif pattern == 2:
            # Velocity burst: cluster 2-3 transactions within 3 minutes for same customer
            if idx + 1 < num_records:
                tx_cust_ids[idx + 1] = tx_cust_ids[idx]
                tx_acct_ids[idx + 1] = tx_acct_ids[idx]
                tx_card_tokens[idx + 1] = tx_card_tokens[idx]
                base_dt = datetime.strptime(str(tx_timestamps[idx]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                tx_timestamps[idx + 1] = (base_dt + timedelta(seconds=int(rng.integers(30, 180)))).strftime("%Y-%m-%dT%H:%M:%SZ")
                tx_amounts[idx] = round(float(rng.uniform(950.0, 6500.0)), 2)
                tx_amounts[idx + 1] = round(float(rng.uniform(950.0, 6500.0)), 2)
                fraud_labels[idx + 1] = 1
        else:
            # Repeated failed/declined + sudden spike
            tx_statuses[idx] = "FAILED"
            tx_amounts[idx] = round(float(rng.uniform(3200.0, 15000.0)), 2)
            tx_devices[idx] = f"DEV-ANOM-{rng.integers(80000, 89999)}"

    # 6. Inject Configurable Data Quality Issues + Ground-Truth Manifest
    injected_issues: dict[str, int] = {
        "duplicate_transaction_ids": 0,
        "missing_mandatory_values": 0,
        "invalid_currency_codes": 0,
        "invalid_timestamps": 0,
        "incorrect_data_types": 0,
        "inconsistent_country_names": 0,
        "invalid_transaction_amounts": 0,
        "referential_integrity_violations": 0,
    }
    manifest_records: list[dict[str, Any]] = []

    if inject_quality_issues and quality_issue_rate > 0:
        n_issues = max(8, int(num_records * quality_issue_rate))
        # Keep fraud indices clean from corruption so fraud evaluation has clean records, where possible
        clean_candidates = np.where(fraud_labels == 0)[0]
        if len(clean_candidates) < n_issues:
            clean_candidates = np.arange(num_records)
        issue_indices = rng.choice(clean_candidates, size=min(n_issues, len(clean_candidates)), replace=False)

        issue_types = list(injected_issues.keys())
        for pos, idx in enumerate(issue_indices):
            itype = issue_types[pos % len(issue_types)]
            orig_tx_id = str(tx_ids[idx])
            if itype == "duplicate_transaction_ids" and idx > 0:
                tx_ids[idx] = tx_ids[max(0, idx - 1)]
            elif itype == "missing_mandatory_values":
                if pos % 2 == 0:
                    tx_cust_ids[idx] = ""
                else:
                    tx_amounts[idx] = ""
            elif itype == "invalid_currency_codes":
                tx_currencies[idx] = rng.choice(["XXX", "ZZZ", "999", "BTC_BAD"])
            elif itype == "invalid_timestamps":
                tx_timestamps[idx] = rng.choice(["not-a-timestamp", "2026-99-99T00:00:00Z", "2099-05-01T12:00:00Z"])
            elif itype == "incorrect_data_types":
                tx_amounts[idx] = rng.choice(["INVALID_AMT", "N/A", "twelve"])
            elif itype == "inconsistent_country_names":
                # Standardizer should fix these rather than dropping them!
                tx_countries[idx] = rng.choice(["USA", "United States", "U.S.", "UK", "United Kingdom", "India", "IND"])
            elif itype == "invalid_transaction_amounts":
                tx_amounts[idx] = rng.choice([-125.50, 0.0, 9999999.99])
            elif itype == "referential_integrity_violations":
                if pos % 2 == 0:
                    tx_cust_ids[idx] = f"CUST-GHOST-{rng.integers(100, 999)}"
                else:
                    tx_merch_ids[idx] = f"MERCH-GHOST-{rng.integers(100, 999)}"

            injected_issues[itype] += 1
            if len(manifest_records) < 2000:
                manifest_records.append({
                    "row_index": int(idx),
                    "original_transaction_id": orig_tx_id,
                    "issue_type": itype,
                })

    transactions_df = pd.DataFrame({
        "transaction_id": tx_ids,
        "customer_id": tx_cust_ids,
        "account_id": tx_acct_ids,
        "card_token": tx_card_tokens,
        "transaction_timestamp": tx_timestamps,
        "transaction_amount": tx_amounts,
        "currency": tx_currencies,
        "merchant_id": tx_merch_ids,
        "merchant_category": tx_merch_cats,
        "transaction_type": tx_types,
        "payment_method": tx_methods,
        "transaction_country": tx_countries,
        "transaction_city": tx_cities,
        "device_id": tx_devices,
        "transaction_status": tx_statuses,
        "credit_limit": tx_credit_limits,
        "outstanding_balance": tx_balances,
        "repayment_status": tx_repay,
        "customer_risk_category": tx_cust_risk,
        "fraud_label": fraud_labels,
        "ingestion_timestamp": ingestion_ts,
        "source_system": tx_sources,
    })

    # Write files
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"{prefix}_{num_records}_{seed}_{ts_tag}"

    customers_path = out_path / f"{base_name}_customers.csv"
    accounts_path = out_path / f"{base_name}_accounts.csv"
    merchants_path = out_path / f"{base_name}_merchants.csv"

    customers_df.to_csv(customers_path, index=False)
    accounts_df.to_csv(accounts_path, index=False)
    merchants_df.to_csv(merchants_path, index=False)

    if file_format.lower() == "json":
        tx_path = out_path / f"{base_name}_transactions.json"
        transactions_df.to_json(tx_path, orient="records", lines=True)
    else:
        tx_path = out_path / f"{base_name}_transactions.csv"
        transactions_df.to_csv(tx_path, index=False)

    manifest = {
        "synthetic_data_disclaimer": "100% synthetic financial data generated for portfolio/testing purposes. Contains zero real PII or PCI.",
        "seed": seed,
        "num_records": num_records,
        "num_customers": num_customers,
        "num_accounts": num_customers,
        "num_merchants": num_merchants,
        "synthetic_fraud_count": int(fraud_labels.sum()),
        "synthetic_fraud_rate": round(float(fraud_labels.mean()), 4),
        "injected_quality_issues_summary": injected_issues,
        "total_injected_issues": sum(injected_issues.values()),
        "sample_issue_manifest": manifest_records[:500],
        "files": {
            "transactions": str(tx_path),
            "customers": str(customers_path),
            "accounts": str(accounts_path),
            "merchants": str(merchants_path),
        },
    }
    manifest_path = out_path / f"{base_name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "transactions_file": str(tx_path),
        "customers_file": str(customers_path),
        "accounts_file": str(accounts_path),
        "merchants_file": str(merchants_path),
        "manifest_file": str(manifest_path),
        "manifest": manifest,
    }
