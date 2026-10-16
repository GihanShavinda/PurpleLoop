# P3 — Native telemetry collection (P1/P2-compatible overlay)

## Scope and security
- No containers. This package contains **complete contents of every new or replaced file**; copy over your existing P2 repo.
- **Back up PostgreSQL and git commit your working P2 before upgrading.** This is an additive Alembic migration; it does not delete your existing five assets.
- Management endpoints require existing JWT role checks. Collectors use a **separate per-source random key** and can only submit events for the bound asset. Only the SHA-256 digest is stored.
- Never expose the FastAPI HTTP listener directly to an untrusted network. For communication from VMware VMs, put a **TLS reverse proxy** on Windows with a trusted lab CA certificate, restricted firewall ingress, and enforce TLS certificate verification. Do not put collector secrets into Git or command logs.
- Do not treat a VMware inventory flag as proof of monitoring. `receiving` means the source sent an event within the last 10 minutes; `stale` means older receipts. This is not a heartbeat check.
- P3 ingests normalized JSONL events. Native Sysmon/auditd/Suricata/Zeek adapters and secure agent packaging can be added next. No attack execution or automated SOAR actions.

## Windows host: install the update

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
git status
# Back up your project and database before overwriting files.
# Extract the ZIP and copy its contents into this project root, preserving directories.
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p3_contracts.py -v
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

A second PowerShell terminal:
```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop\frontend'
npm install
npm run build
npm start
```

## Register sources
1. Log in to Angular as an Administrator or Purple Team Engineer.
2. Select **Telemetry** in the sidebar. Choose one of the existing assets (e.g. Ubuntu `ubuntu2404`), source type `linux_journal`, and give it a meaningful name.
3. Click **Create source**. Save the displayed collector key in the collector VM's secret store or shell environment. It is not retrievable later.
4. For first-time **local-only** smoke testing, use `http://127.0.0.1:8000` from the Windows host. For remote VMs, configure an authenticated HTTPS reverse proxy first.

## Test event locally (PowerShell)
Paste your source key into a private prompt (do not put it into your shell history):

```powershell
$key = Read-Host 'Collector key'
$body = @{ events = @(@{
    event_time = [DateTimeOffset]::UtcNow.ToString('o')
    event_type = 'p3.smoke_test'
    severity = 'info'
    message = 'P3 connectivity validation event'
    payload = @{ test = $true; category = 'smoke' }
}) } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/telemetry/ingest' -ContentType 'application/json' -Headers @{ 'X-Collector-Key' = $key } -Body $body
Remove-Variable key
```

Expected: HTTP 202, `accepted: 1`. Refresh the Telemetry UI. The event should appear and the source should show `receiving`.

## Native file shipper (Windows or Linux)

The file shipper sends **complete newline-terminated JSON records**. Each line must include `event_time` with a UTC offset, `event_type`, `severity`, `message`, and an optional `payload` object.

Example `events.jsonl`:
```json
{"event_time":"2026-10-14T15:00:00+00:00","event_type":"demo.login","severity":"info","message":"Example logon event","payload":{"event_id":4624}}
```
Use real UTC timestamps for live ingestion; future timestamps beyond five minutes are rejected. Do not send Windows security log secrets or entire unredacted records.

Windows host smoke test:
```powershell
$env:PURPLEFORGE_API_URL='http://127.0.0.1:8000'
$env:PURPLEFORGE_COLLECTOR_KEY=Read-Host 'Collector key'
$env:PURPLEFORGE_LOG_FILE='C:\path\events.jsonl'
.\backend\.venv\Scripts\python.exe .\collectors\native_file_shipper.py
```
For Ubuntu/Kali VM, run it from a Python 3 virtual environment, export `PURPLEFORGE_API_URL=https://<host-ip>:8443`, configure verified lab CA trust, then run `python collectors/native_file_shipper.py`. The remote HTTP URL is rejected by design. Avoid placing tokens directly in long-lived bash history; use root-readable environment files or a systemd credential arrangement.

## Important limitations
- A source's `last_seen_at` updates only when ingestion succeeds; it is not a real agent health signal.
- The file shipper is an initial JSONL transport, not a full Sysmon/auditd/Suricata/Zeek adapter. Additional parsers and rotation-aware checkpointing are future work.
- There is no event retention job, deduplication, or ingestion rate limit yet. Use only inside a constrained lab at modest volumes and introduce reverse-proxy limits before broader exposure.
- The frontend initially shows 100 events; sources list is capped at 300.
- Redis/Neo4j remain configured for later phases but are **not in the P3 ingestion transaction path**.
- Do not stream lab attack activity to outside services or allow unrestricted connections from deliberately vulnerable VMs.
