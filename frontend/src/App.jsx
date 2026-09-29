import { useCallback, useEffect, useMemo, useState } from "react";

const LOW_GPU_HOURS = 5;

function hours(value) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(1)}h`;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function QuotaCell({ quota }) {
  if (!quota) return <span className="muted">—</span>;
  const percentage =
    quota.total_hours > 0 ? Math.max(0, Math.min(100, (quota.remaining_hours / quota.total_hours) * 100)) : 0;

  return (
    <div className="quota-cell">
      <div className="quota-numbers">
        <strong>{hours(quota.remaining_hours)}</strong>
        <span> / {hours(quota.total_hours)}</span>
      </div>
      <div className="bar" aria-label={`${percentage.toFixed(0)}% remaining`}>
        <div className="bar-fill" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/accounts");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setAccounts(await response.json());
      setError("");
    } catch (err) {
      setError(`Could not load dashboard: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function refreshAll() {
    setRefreshing(true);
    setError("");
    try {
      const response = await fetch("/api/refresh", { method: "POST" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await load();
    } catch (err) {
      setError(`Refresh failed: ${err.message}`);
    } finally {
      setRefreshing(false);
    }
  }

  const summary = useMemo(() => {
    const healthy = accounts.filter((account) => account.status === "ok").length;
    const gpuRemaining = accounts.reduce(
      (sum, account) => sum + (account.gpu?.remaining_hours || 0),
      0,
    );
    const low = accounts.filter(
      (account) => account.status === "ok" && account.gpu && account.gpu.remaining_hours < LOW_GPU_HOURS,
    ).length;
    return { healthy, gpuRemaining, low };
  }, [accounts]);

  return (
    <main className="shell">
      <header>
        <div>
          <p className="eyebrow">KAGGLE · ACCELERATOR MONITOR</p>
          <h1>Quota Dashboard</h1>
          <p className="subtitle">GPU and TPU allowance across authorized student accounts.</p>
        </div>
        <button onClick={refreshAll} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh now"}
        </button>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="cards">
        <article>
          <span>Accounts</span>
          <strong>{accounts.length}</strong>
        </article>
        <article>
          <span>Healthy</span>
          <strong>{summary.healthy}</strong>
        </article>
        <article>
          <span>GPU remaining</span>
          <strong>{hours(summary.gpuRemaining)}</strong>
        </article>
        <article>
          <span>Below {LOW_GPU_HOURS}h GPU</span>
          <strong>{summary.low}</strong>
        </article>
      </section>

      <section className="panel">
        <div className="panel-title">
          <h2>Accounts</h2>
          <span>Cached view · refreshes every 30s</span>
        </div>

        {loading ? (
          <div className="empty">Loading…</div>
        ) : accounts.length === 0 ? (
          <div className="empty">
            No snapshots yet. Add credential directories and press <b>Refresh now</b>.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Student / account</th>
                  <th>Status</th>
                  <th>GPU remaining</th>
                  <th>TPU remaining</th>
                  <th>Quota reset</th>
                  <th>Checked</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.account_id}>
                    <td>
                      <div className="account-name">{account.name}</div>
                      <code>{account.account_id}</code>
                    </td>
                    <td>
                      <span className={`status ${account.status}`}>
                        {account.status === "ok" ? "OK" : "ERROR"}
                      </span>
                      {account.error && <div className="row-error">{account.error}</div>}
                    </td>
                    <td>
                      <QuotaCell quota={account.gpu} />
                    </td>
                    <td>
                      <QuotaCell quota={account.tpu} />
                    </td>
                    <td>{formatDate(account.gpu?.refresh_at || account.tpu?.refresh_at)}</td>
                    <td>{formatDate(account.checked_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
