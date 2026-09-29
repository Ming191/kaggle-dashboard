from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import get_snapshot, init_db, list_snapshots, upsert_snapshot
from .kaggle_client import collect_quota, load_accounts
from .models import AccountConfig, AccountSnapshot

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/quota.db")
CREDENTIALS_DIR = os.getenv("CREDENTIALS_DIR", "/credentials")
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "/config/accounts.json")
REFRESH_INTERVAL_SECONDS = max(60, int(os.getenv("REFRESH_INTERVAL_SECONDS", "600")))
MAX_CONCURRENT_CHECKS = max(1, int(os.getenv("MAX_CONCURRENT_CHECKS", "4")))

_refresh_lock = asyncio.Lock()


def configured_accounts() -> list[AccountConfig]:
    return load_accounts(ACCOUNTS_FILE, CREDENTIALS_DIR)


async def refresh_account(account: AccountConfig) -> AccountSnapshot:
    snapshot = await asyncio.to_thread(collect_quota, account)
    await asyncio.to_thread(upsert_snapshot, DATABASE_PATH, snapshot)
    return snapshot


async def refresh_all() -> list[AccountSnapshot]:
    async with _refresh_lock:
        accounts = configured_accounts()
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)

        async def guarded(account: AccountConfig) -> AccountSnapshot:
            async with semaphore:
                return await refresh_account(account)

        return await asyncio.gather(*(guarded(account) for account in accounts))


async def refresh_loop() -> None:
    while True:
        try:
            await refresh_all()
        except Exception:
            # Keep the scheduler alive. Per-account errors are represented in snapshots.
            pass
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(DATABASE_PATH)
    task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Kaggle Quota Dashboard", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "configured_accounts": len(configured_accounts())}


@app.get("/api/accounts")
async def accounts() -> list[dict]:
    return await asyncio.to_thread(list_snapshots, DATABASE_PATH)


@app.post("/api/refresh")
async def refresh() -> list[AccountSnapshot]:
    return await refresh_all()


@app.post("/api/refresh/{account_id}")
async def refresh_one(account_id: str) -> AccountSnapshot:
    account = next((item for item in configured_accounts() if item.id == account_id), None)
    if account is None:
        raise HTTPException(status_code=404, detail="Unknown account")
    return await refresh_account(account)


@app.get("/api/accounts/{account_id}")
async def account_snapshot(account_id: str) -> dict:
    snapshot = await asyncio.to_thread(get_snapshot, DATABASE_PATH, account_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No snapshot available")
    return snapshot
