# PurpleForge AI — P3.1: Native Ubuntu Journald Collector

## Purpose and what changed
P3 already has `/telemetry/ingest`, source creation, JWT management and Angular event explorer. This incremental update adds a native Ubuntu 24.04 journald collector and a **Windows-native HTTPS proxy example**. No new API route, Angular replacement or Alembic migration is needed. These are complete *new* files, not a replacement for your P3 ZIP.

The system does **not** yet collect Sysmon, Suricata, Zeek, or auditd data automatically. Journal event severity is mapped from syslog priority (not an incident severity judgment). There is no SOAR or attack execution in this phase.

## Files
- `collectors/linux/journal_shipper.py` — secure journald shipper, persisted checkpoint, retried submissions
- `collectors/linux/collector.env.example` — local collector settings template
- `collectors/linux/purpleforge-journal.service` — native Linux systemd service
- `infrastructure/windows/Caddyfile.example` — optional native Windows reverse proxy example, **ingest-only**
- `infrastructure/windows/check-p31.ps1` — PowerShell local health check
- `tests/test_p31_journal_shipper.py` — unit tests with no external dependencies
- `docs/P3_1_UBUNTU_NATIVE_COLLECTOR.md` — this guide

## 0. Prerequisites and risk boundary
- The five VMware assets already exist in PostgreSQL and P3 telemetry endpoints function (your API reported HTTP 201 for source creation, 202 for ingestion).
- Confirm Windows VMnet1 adapter is actually `192.168.37.1` and Ubuntu VM is `192.168.37.20` **now**. The addresses can change. Ubuntu can ping the host but ping alone is not enough to validate TLS.
- **Do not expose FastAPI's `8000` listener directly to the VM network.** Keep FastAPI listening on `127.0.0.1` and provide an authenticated TLS reverse proxy on `192.168.37.1:8443`. Restrict the Windows inbound firewall rule to the Ubuntu IP.
- Create a lab CA and server certificate with subjectAltName of `IP:192.168.37.1` using your preferred certificate tooling. Import the lab CA certificate into Ubuntu and set `PURPLEFORGE_CA_FILE`. Do not use `curl -k` / `verify=False` / insecure certificate shortcuts.
- Ensure the host has native Caddy installed, if using this example. Validate its Caddyfile with `caddy validate --config C:\purpleforge\Caddyfile`, then run `caddy run --config C:\purpleforge\Caddyfile` in a dedicated terminal or configure it as a Windows service with an approved service manager. This guide does not assume Caddy is already present.

## 1. Windows host: install the delta and configure HTTPS
Copy the contents of this ZIP into your existing PurpleLoop project root. No P1/P2/P3 existing source files are replaced.

Sample PowerShell commands (administrator for firewall modification):
```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.37.1'
# After installing Caddy and provisioning a trusted server cert and private key:
New-Item -ItemType Directory C:\purpleforge -Force
Copy-Item .\infrastructure\windows\Caddyfile.example C:\purpleforge\Caddyfile
# Edit certificate paths/IP to match your lab.
notepad C:\purpleforge\Caddyfile
caddy validate --config C:\purpleforge\Caddyfile
# Open inbound port only from the Ubuntu VM on VMnet1.
New-NetFirewallRule -DisplayName 'PurpleForge collector TLS from Ubuntu' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8443 -LocalAddress 192.168.37.1 -RemoteAddress 192.168.37.20
# In a dedicated shell: caddy run --config C:\purpleforge\Caddyfile
```

Keep backend process bound to localhost:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 2. Register an Ubuntu telemetry source
Open Angular → **Telemetry** → select asset `ubuntu2404` (192.168.37.20) → select type `linux_journal` → create. Save the key **once** in a protected local file on Ubuntu. Do not share it in chat or add it to GitHub. If already created, use that existing source/key; do not create duplicates.

## 3. Ubuntu VM native setup (commands are for Ubuntu bash, not Windows PowerShell)
Transfer the two `collectors/linux/` files and the certificate `lab-ca.crt` to Ubuntu securely (e.g. SSH/SCP after enabling SSH as appropriate). Example below assumes source files are present in the current directory on Ubuntu.

```bash
sudo useradd --system --user-group --home /var/lib/purpleforge-journal --shell /usr/sbin/nologin purpleforge-collector || true
sudo usermod -aG systemd-journal purpleforge-collector
sudo install -d -m 0750 -o purpleforge-collector -g purpleforge-collector /var/lib/purpleforge-journal
sudo install -d -m 0750 -o root -g purpleforge-collector /etc/purpleforge
sudo install -d -m 0755 /opt/purpleforge
sudo install -m 0755 journal_shipper.py /opt/purpleforge/journal_shipper.py
sudo install -m 0644 collector.env.example /etc/purpleforge/collector.env
sudo install -m 0644 lab-ca.crt /etc/purpleforge/lab-ca.crt
# Paste the key at this interactive prompt; it is not stored in shell history.
sudo bash -c 'umask 027; cat > /etc/purpleforge/collector.key'
# Enter the key, press Enter, then Ctrl+D; do not include extra whitespace.
sudo chown root:purpleforge-collector /etc/purpleforge/collector.key
sudo chmod 0640 /etc/purpleforge/collector.key
sudo install -m 0644 purpleforge-journal.service /etc/systemd/system/purpleforge-journal.service
sudo systemctl daemon-reload
```

The journal shipper uses Python's standard library, so a virtual environment is optional. For a strictly isolated Python runtime you may create one and edit the systemd `ExecStart` accordingly.

Check HTTPS trust before enabling the collector:
```bash
curl --cacert /etc/purpleforge/lab-ca.crt -I https://192.168.37.1:8443/telemetry/ingest
# A 404/405 from the proxy when using HEAD is acceptable; TLS must verify.
```

Start collector:
```bash
sudo systemctl enable --now purpleforge-journal
sudo systemctl status purpleforge-journal --no-pager
sudo journalctl -u purpleforge-journal -n 30 --no-pager
```

To generate a harmless log record:
```bash
logger -t purpleforge-smoke 'PurpleForge Ubuntu journal telemetry smoke test'
```

Return to Angular → Telemetry, refresh, and confirm `linux.journal` event appears, message contains `PurpleForge Ubuntu journal telemetry smoke test`, and the Ubuntu source is `receiving` (within ~10 minutes).

## 4. Windows verification and tests
```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
.\backend\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_p31_*.py' -v
.\infrastructure\windows\check-p31.ps1
```

## 5. Limitations / failure handling
- Collector persists journal cursor **only after** the P3 API confirms accepted event count. A network timeout after a successful server commit may resend records; P3 has no event-id deduplication, so duplicates are possible. Use later event fingerprinting if this matters.
- The initial first run reads only the last 10 minutes of records. Long offline gaps with log rotation may lose older events. Treat this as an initial low-volume lab collector, not a production-grade guaranteed-delivery pipeline.
- A source status of `receiving` only means events arrived recently, not that all journal messages have been collected.
- Keep collector credentials out of screenshots, console outputs, Git and chat. Revoke old source credentials by disabling the source if exposed.
- P3 currently has no global event retention and quota. Keep the lab volume modest and add retention, authentication rate limits and observability in future hardening work.
