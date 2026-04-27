# OpsCore Production Deployment

## Runtime Contract

- Health check: `GET /healthz`
- API prefix: `/api/v1`
- Static frontend: `static_react/`
- Required config file: `.env`, based on `.env.example`
- Release gate: `python scripts/preflight.py`

## Environment

1. Copy `.env.example` to `.env`.
2. Set `OPSCORE_API_TOKEN` to a long random value.
3. Set `OPSCORE_ALLOWED_ORIGINS` to the exact browser origins allowed to call the API.
4. Configure model provider values such as `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.

Never commit `.env`, `.fernet.key`, database files, or provider tokens.

## Build

```powershell
python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
python scripts/preflight.py
```

## Run Directly

```powershell
python main.py
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

## Run With Docker

```powershell
docker build -t opscore-aiops:latest .
docker run --name opscore-aiops -p 8000:8000 --env-file .env -v ${PWD}:/app/state opscore-aiops:latest
```

The Docker health check probes `/healthz`. Keep persistent state on a host volume in production.

## systemd Example

```ini
[Unit]
Description=OpsCore AIOps
After=network-online.target

[Service]
WorkingDirectory=/opt/opscore
EnvironmentFile=/opt/opscore/.env
ExecStart=/opt/opscore/.venv/bin/python /opt/opscore/main.py
Restart=always
RestartSec=5
User=opscore
Group=opscore

[Install]
WantedBy=multi-user.target
```

## Rollback

1. Stop the service.
2. Restore the previous code artifact.
3. Restore state from the latest known-good backup if schema or state files changed.
4. Start the service.
5. Verify `/healthz`, login, asset list, model config, and one read-only inspection.
