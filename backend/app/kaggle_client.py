from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .models import AccountConfig, AccountSnapshot, ResourceQuota

_HOURS_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)h\s*$", re.IGNORECASE)


def parse_hours(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = _HOURS_RE.match(value)
    if not match:
        raise ValueError(f"Unexpected Kaggle duration: {value!r}")
    return float(match.group(1))


def parse_quota_rows(rows: list[dict]) -> dict[str, ResourceQuota]:
    parsed: dict[str, ResourceQuota] = {}
    for row in rows:
        resource = str(row.get("resource", "")).upper()
        if resource not in {"GPU", "TPU"}:
            continue
        parsed[resource] = ResourceQuota(
            used_hours=parse_hours(row.get("used")),
            remaining_hours=max(0.0, parse_hours(row.get("remaining"))),
            total_hours=parse_hours(row.get("total")),
            refresh_at=row.get("refreshAt"),
        )
    return parsed


def load_accounts(accounts_file: str, credentials_dir: str) -> list[AccountConfig]:
    account_path = Path(accounts_file)
    if account_path.is_file():
        raw = json.loads(account_path.read_text(encoding="utf-8"))
        accounts = [AccountConfig.model_validate(item) for item in raw]
    else:
        root = Path(credentials_dir)
        if not root.exists():
            return []
        accounts = [
            AccountConfig(id=child.name, name=child.name, config_dir=str(child))
            for child in sorted(root.iterdir())
            if child.is_dir() and not child.name.startswith(".")
        ]

    ids = [account.id for account in accounts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate account id in account configuration")
    return accounts


def collect_quota(account: AccountConfig, timeout_seconds: int = 30) -> AccountSnapshot:
    checked_at = datetime.now(timezone.utc)
    config_dir = Path(account.config_dir)

    if not config_dir.is_dir():
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error=f"Credential directory not found: {account.config_dir}",
            checked_at=checked_at,
        )

    env = os.environ.copy()
    for key in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
        env.pop(key, None)
    env["KAGGLE_CONFIG_DIR"] = str(config_dir)

    try:
        result = subprocess.run(
            ["kaggle", "quota", "--format", "json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error=f"Kaggle quota request timed out after {timeout_seconds}s",
            checked_at=checked_at,
        )
    except OSError as exc:
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error=f"Failed to execute Kaggle CLI: {exc}",
            checked_at=checked_at,
        )

    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Kaggle CLI returned an error").strip()
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error=message[:600],
            checked_at=checked_at,
        )

    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list):
            raise ValueError("Expected a JSON list from kaggle quota")
        quota = parse_quota_rows(raw)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error=f"Could not parse Kaggle quota output: {exc}",
            checked_at=checked_at,
        )

    if not quota:
        return AccountSnapshot(
            account_id=account.id,
            name=account.name,
            status="error",
            error="Kaggle returned no GPU or TPU quota rows",
            checked_at=checked_at,
        )

    return AccountSnapshot(
        account_id=account.id,
        name=account.name,
        status="ok",
        checked_at=checked_at,
        gpu=quota.get("GPU"),
        tpu=quota.get("TPU"),
    )
