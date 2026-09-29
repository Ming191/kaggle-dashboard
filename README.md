# Kaggle Quota Dashboard

Internal dashboard for monitoring Kaggle GPU/TPU accelerator quota across multiple authorized student accounts.

## What it does

- Reads one Kaggle credential directory per student/account.
- Runs `kaggle quota --format json` in an isolated process using `KAGGLE_CONFIG_DIR`.
- Aggregates GPU/TPU used, remaining, total, refresh time, and account health.
- Caches the latest snapshot in SQLite.
- Refreshes all accounts on demand or automatically on a configurable interval.
- Serves a small React/Vite dashboard backed by FastAPI.

Kaggle CLI 2.2.1 introduced the top-level `kaggle quota` command. This project pins a newer CLI release and treats its JSON output as rows with `resource`, `used`, `remaining`, `total`, and `refreshAt`.

## Quick start

1. Clone the repository.

```bash
git clone https://github.com/Ming191/kaggle-dashboard.git
cd kaggle-dashboard
```

2. Create one directory per account under `credentials/`.

```text
credentials/
├── alice/
│   └── kaggle.json
├── bob/
│   └── kaggle.json
└── charlie/
    └── kaggle.json
```

Legacy `kaggle.json` credentials work. Each directory is passed to the Kaggle CLI through `KAGGLE_CONFIG_DIR`, so accounts do not overwrite one another's auth state.

3. Optional: copy `accounts.example.json` to `accounts.json` if you want friendly student names.

```bash
cp accounts.example.json accounts.json
```

4. Run with Docker Compose.

```bash
docker compose up --build
```

Open:

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs

## Account configuration

If `accounts.json` exists, it is the source of account metadata:

```json
[
  {
    "id": "alice",
    "name": "Alice Nguyen",
    "config_dir": "/credentials/alice"
  }
]
```

If the file does not exist, the backend auto-discovers every child directory under `CREDENTIALS_DIR`.

## API

- `GET /api/accounts` — latest cached quota for all accounts.
- `POST /api/refresh` — refresh all accounts immediately.
- `POST /api/refresh/{account_id}` — refresh one account.
- `GET /api/health` — service health.

The background refresher uses `REFRESH_INTERVAL_SECONDS` (default: 600 seconds).

## Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CREDENTIALS_DIR=../credentials
export ACCOUNTS_FILE=../accounts.json
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Security

Do not commit student credentials. `credentials/`, `accounts.json`, `*.db`, and local environment files are ignored by Git.

This dashboard is intended for accounts you are authorized to administer. If it is exposed outside a trusted network, put authentication and TLS in front of it (for example, a reverse proxy or an identity-aware access layer).

## Tests

```bash
cd backend
pytest
```
