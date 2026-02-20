"""Data models for alert ingestion and normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"


class RawAlert(BaseModel):
    """Alertmanager webhook payload for a single alert."""

    status: str
    labels: dict[str, str]
    annotations: dict[str, str] = {}
    starts_at: str = Field(alias="startsAt", default="")
    ends_at: str = Field(alias="endsAt", default="")
    generator_url: str = Field(alias="generatorURL", default="")
    fingerprint: str = ""


class AlertmanagerPayload(BaseModel):
    """Full Alertmanager webhook payload."""

    version: str = "4"
    group_key: str = Field(alias="groupKey", default="")
    status: str = "firing"
    receiver: str = ""
    group_labels: dict[str, str] = Field(alias="groupLabels", default={})
    common_labels: dict[str, str] = Field(alias="commonLabels", default={})
    common_annotations: dict[str, str] = Field(alias="commonAnnotations", default={})
    external_url: str = Field(alias="externalURL", default="")
    alerts: list[RawAlert] = []


class NormalizedAlert(BaseModel):
    """Internal standardized alert representation."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    severity: AlertSeverity
    status: AlertStatus
    source: str = "alertmanager"
    summary: str = ""
    description: str = ""
    labels: dict[str, str] = {}
    starts_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ends_at: datetime | None = None
    generator_url: str = ""
    fingerprint: str = ""
    raw: dict = {}
