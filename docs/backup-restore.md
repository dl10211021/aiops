# OpsCore Backup And Restore

## What To Back Up

Back up these files/directories before upgrades and on a regular schedule:

- `opscore.db`
- `cron_jobs.sqlite`
- `.fernet.key`
- `providers.json`
- `safety_policy.json`
- `approval_requests.json`
- `inspection_runs.json`
- `inspection_templates.json`
- `memory/`
- `opscore_lancedb/`
- `knowledge_base/`
- `data/`

Do not expose backups publicly. They can contain encrypted credentials, model provider metadata, approval history, and operational evidence.

## Manual Backup

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$target = "backups/opscore_$stamp"
New-Item -ItemType Directory -Force $target
Copy-Item opscore.db,cron_jobs.sqlite,.fernet.key,providers.json,safety_policy.json,approval_requests.json,inspection_runs.json -Destination $target -ErrorAction SilentlyContinue
Copy-Item memory,opscore_lancedb,knowledge_base,data -Destination $target -Recurse -ErrorAction SilentlyContinue
Compress-Archive -Path $target -DestinationPath "$target.zip"
```

## Restore

1. Stop OpsCore.
2. Move the current state aside instead of deleting it.
3. Extract the backup archive.
4. Restore the files to the project root.
5. Start OpsCore.
6. Verify `GET /healthz`.
7. Verify assets, model provider config, approval center, and one read-only inspection.

## Rollback

If restore fails, stop OpsCore, move the restored state aside, move the previous state back, restart, then verify `/healthz`.

## Backup Frequency

- Before every release.
- Daily for production.
- Immediately after large asset imports or safety-policy changes.
