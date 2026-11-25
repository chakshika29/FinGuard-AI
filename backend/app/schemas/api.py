"""Pydantic request and response schemas for FinGuard AI REST APIs."""

from typing import Any
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=128)
    role: str = Field(..., pattern="^(Administrator|Data Steward|Risk Analyst)$")
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(Administrator|Data Steward|Risk Analyst)$")
    is_active: bool | None = None
    full_name: str | None = None


class GenerateDatasetRequest(BaseModel):
    num_records: int = Field(default=10000, ge=100, le=1000000)
    seed: int = Field(default=42, ge=0, le=999999)
    inject_quality_issues: bool = True
    quality_issue_rate: float = Field(default=0.03, ge=0.0, le=0.25)
    fraud_rate: float = Field(default=0.025, ge=0.001, le=0.20)
    file_format: str = Field(default="csv", pattern="^(csv|json)$")
    auto_ingest: bool = True


class QualityRuleCreate(BaseModel):
    rule_id: str | None = None
    rule_name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., min_length=5)
    dataset: str = Field(default="transactions")
    column_name: str = Field(..., min_length=1, max_length=64)
    dimension: str = Field(..., pattern="^(Completeness|Accuracy|Consistency|Uniqueness|Validity|Timeliness|Referential Integrity)$")
    severity: str = Field(..., pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    threshold: float = Field(default=99.0, ge=0.0, le=100.0)
    enabled: bool = True
    owner: str = Field(default="Marcus Chen (Data Steward)")
    rule_type: str = Field(..., pattern="^(not_null|unique|allowed_values|range|timestamp_valid|timeliness|referential_integrity)$")
    rule_config: dict[str, Any] = Field(default_factory=dict)


class QualityRuleUpdate(BaseModel):
    rule_name: str | None = None
    description: str | None = None
    severity: str | None = Field(default=None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    threshold: float | None = Field(default=None, ge=0.0, le=100.0)
    enabled: bool | None = None
    owner: str | None = None
    rule_config: dict[str, Any] | None = None


class QuarantineUpdateRequest(BaseModel):
    remediation_status: str = Field(..., pattern="^(OPEN|REVIEWED|RESOLVED|IGNORED)$")
    remediation_notes: str = Field(default="", max_length=1000)


class CatalogUpdateRequest(BaseModel):
    business_owner: str | None = None
    technical_owner: str | None = None
    data_steward: str | None = None
    data_classification: str | None = Field(default=None, pattern="^(Public|Internal|Confidential|Restricted)$")
    retention_policy: str | None = None


class PolicyUpdateRequest(BaseModel):
    enabled: bool | None = None
    severity: str | None = Field(default=None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    threshold_rule: str | None = None
    owner: str | None = None


class FraudAlertUpdateRequest(BaseModel):
    investigation_status: str = Field(..., pattern="^(OPEN|INVESTIGATING|ESCALATED|DISMISSED|CONFIRMED_TEST_PATTERN)$")
    analyst_notes: str = Field(default="", max_length=1000)
    assigned_analyst: str | None = None
