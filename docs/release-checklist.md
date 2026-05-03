# OpsCore Release Checklist

## Before Release

- Run `python scripts/preflight.py`.
- Build frontend with `npm run build` from `frontend/` and confirm `static_react/index.html` is generated locally or inside the Docker image.
- Confirm `static_react/` is not staged in Git unless an explicit built-asset exception has been approved.
- Confirm `GET /healthz` returns `status: ok` or only accepted warnings.
- Confirm `.env` is based on `.env.example`.
- Confirm no secrets are committed.
- Back up state files listed in `docs/backup-restore.md`.

## Smoke Test

- Open dashboard and verify asset totals.
- Open asset center and verify asset protocol/tool visibility.
- Run one Linux read-only inspection.
- Run protocol verification from asset center for at least one asset in each available class: Linux/SSH, Windows/WinRM, SQL DB, HTTP/API or Prometheus, SNMP/network.
- Confirm every non-SSH verification shows `协议原生探测` before `只读巡检`.
- Run one Windows or database read-only inspection if available and confirm the result uses managed asset credentials.
- Trigger or inspect one high-risk approval and confirm it appears in approval center.
- Verify model provider config loads without exposing API keys.

## Rollback

- Restore the previous artifact.
- Restore the latest known-good state backup if needed.
- Restart service.
- Verify `/healthz`.
- Verify login, dashboard, asset list, approval center, and one read-only inspection.

## Post Release

- Watch backend logs for errors.
- Watch approval queue for unexpected high-risk calls.
- Watch inspection run failure rate and dashboard trends.
