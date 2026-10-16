# PurpleForge P17 — Read-only VMware range readiness (no Docker)

This package was based on the P16 release. It adds a manually triggered readiness assessment for registered assets. It **does not execute VMware tools**, alter snapshots, power state, firewall, routes or guest services. Power state and network are explicitly marked operator-reported.

## Windows host: install (PowerShell, project root)

Stop FastAPI/Angular. Commit P16 and back up your database first.

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p17.dump" purpleforge
Expand-Archive "$env:USERPROFILE\Downloads\purpleforge-ai-p17-no-docker.zip" ".\p17-staging" -Force
# Review diffs before replacing. If you have newer local modifications, merge them.
git diff --no-index .\frontend\src\main.ts .\p17-staging\frontend\src\main.ts
Copy-Item .\p17-staging\backend\main.py .\backend\main.py -Force
Copy-Item .\p17-staging\backend\models.py .\backend\models.py -Force
Copy-Item .\p17-staging\backend\vmware_range .\backend\vmware_range -Recurse -Force
Copy-Item .\p17-staging\backend\migrations\versions\0016_p17_vmware_range.py .\backend\migrations\versions\ -Force
Copy-Item .\p17-staging\frontend\src\main.ts .\frontend\src\main.ts -Force
Copy-Item .\p17-staging\frontend\src\p17-vmware-range.component.ts .\frontend\src\ -Force
Copy-Item .\p17-staging\tests\test_p17_assessment.py .\tests\ -Force
.\backend\.venv\Scripts\python.exe -c "import backend.models;import backend.main;print('imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
# Expected current: 0015_p16_investigation
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
# Expected new head: 0016_p17_vmware_range
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p17_assessment.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Start backend:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell terminal:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

Open http://localhost:4200, then scroll sidebar to **VMware Range**.

## Optional VMware operator check (Windows host; no backend execution)

Use VMware Workstation UI to check VM power status and adapter mode. On the Windows host, check VMnet1:
```powershell
Get-NetIPAddress -InterfaceAlias '*VMnet1*' -AddressFamily IPv4
Test-NetConnection 192.168.37.20 -Port 22
```

On Ubuntu, if powered on:
```bash
ip -br addr
sudo systemctl is-active purpleforge-journal
```

In PurpleForge inventory, check the asset's expected `vmware_network` label (usually VMnet1). In **VMware Range** choose the asset, set reported power state and same network label, and record the check. Recent telemetry receipts are checked from PostgreSQL, independently of the operator's description. If no recent telemetry was received, readiness stays false.

Run only once per needed check. This module does not run tests in background.

## Git
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git add backend/main.py backend/models.py backend/vmware_range backend/migrations/versions/0016_p17_vmware_range.py frontend/src/main.ts frontend/src/p17-vmware-range.component.ts tests/test_p17_assessment.py
git commit -m "feat(p17): add read-only VMware range readiness checks"
```
