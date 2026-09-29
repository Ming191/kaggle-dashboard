from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AccountConfig(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    config_dir: str = Field(min_length=1)


class ResourceQuota(BaseModel):
    used_hours: float
    remaining_hours: float
    total_hours: float
    refresh_at: str | None = None


class AccountSnapshot(BaseModel):
    account_id: str
    name: str
    status: str
    error: str | None = None
    checked_at: datetime
    gpu: ResourceQuota | None = None
    tpu: ResourceQuota | None = None
