---
name: windows-admin
description: Provides a robust toolkit for managing remote Windows servers via WinRM.
---
# Windows Admin Skill

## Description
This skill provides a robust toolkit for managing remote Windows servers via WinRM (pywinrm). 
It is designed to handle common administrative tasks like inspecting services, reading logs, querying installed software, and managing processes, all while overcoming common WinRM limitations (like shell escaping and JSON parsing).

## Features
- **Robust Execution:** Uses Base64 encoded commands to bypass PowerShell shell escaping issues.
- **Auto-Fallback:** Automatically retries with Raw Mode (Legacy) if Base64 execution fails (common on servers with restrictive execution policies or older PS versions).
- **Structured Output:** Returns clean JSON data for easier parsing by the agent.
- **Script Bank:** Contains pre-validated PowerShell scripts for common tasks (Software inventory, Log auditing, Resource monitoring).

## Safety Protocol (CRITICAL)
**The Agent MUST explicitly ask for user confirmation before executing any of the following "State-Changing" actions:**
1.  **Service Control:** Stopping, Starting, Restarting, Pausing, or Changing Startup Type of any service.
2.  **Process Control:** Killing or terminating any process (`taskkill`, `Stop-Process`).
3.  **System Power:** Rebooting or Shutting down the server (`Restart-Computer`, `Stop-Computer`).
4.  **File System:** Deleting files, formatting drives, or modifying permissions.
5.  **Registry:** modifying or deleting registry keys.

**Correct Workflow for High-Risk Actions:**
1.  **Analyze:** Identify the necessary action (e.g., "The service is stuck, needs a kill").
2.  **Propose:** Tell the user: "I recommend stopping service X on server Y. This will interrupt feature Z. Shall I proceed?"
3.  **Wait:** Do NOT call the tool until the user replies "Yes" or "Proceed".

## Usage

### 1. Script Location
`scripts/run_winrm.py`

### 2. Basic Command Syntax
```bash
python .claude/skills/windows-admin/scripts/run_winrm.py --target <IP> --user <USER> --password <PASS> --action <ACTION> [options]
```

### 3. Available Actions
| Action | Description | Options |
| :--- | :--- | :--- |
| `inventory` | Get OS version, LastBootTime, CPU Load, Memory, Disk usage. | None |
| `software` | List installed software (Search Registry Uninstall keys). | None |
| `logs` | Fetch recent System/Application Errors and Security Audit Failures. | None |
| `services` | List services with status and start type. | `--filter <string>` (e.g., `*Veeam*`) |
| `stop-service` | **[REQUIRES CONFIRMATION]** Stop a service. | `--service-name <name>` |
| `defender` | Check Windows Defender status (RealTime Protection, Tamper Protection). | None |
| `av` | Detect common 3rd-party Antivirus services (Cortex, 360, McAfee, Trellix, etc). | None |
| `process` | List top 15 processes by CPU usage (includes file path). | None |
| `security-audit` | Comprehensive security check (Users, Admins, Open Ports). | None |
| `veeam-status` | **NEW!** Check Veeam Backup services and SQL instance status. | None |
| `disk-health` | **NEW!** Check Logical (Size/Free) and Physical (Model/Status) disk info. | None |
| `folder-size` | **NEW!** List size of top-level folders in a path (Top 20). | `--path <path>` (Default: `C:\`) |

### 4. Custom Commands
For tasks not covered by actions, use `--command`. **Always prefer `--action` if available.**
```bash
python .claude/skills/windows-admin/scripts/run_winrm.py ... --command "Get-Process | Sort CPU -Descending | Select -First 5"
```

## Troubleshooting
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `Connection refused` (10061) | WinRM service not running or blocked. | Run `winrm quickconfig` on target. Check Firewall 5985. |
| `Access is denied` (401) | Bad credentials or non-Admin user. | Verify username (domain\user) and password. |
| `variable '$' cannot be retrieved` | Shell escaping issue (Legacy mode). | **FIXED:** The new script uses Base64 encoding. |
| `DisableRealtimeMonitoring` ignored | **Tamper Protection** is enabled. | You cannot disable Defender remotely if Tamper Protection is on. Must be disabled in GUI first. |
| Empty output on success | Target doesn't support Base64/EncodedCommand. | **FIXED:** Auto-Fallback mechanism will automatically retry with Raw Mode. You can also force `--no-base64`. |
| `The string is missing the terminator` | Complex quoting in Raw mode. | Use Base64 mode (default) or simplify quotes. |
