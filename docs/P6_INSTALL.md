# PurpleForge AI P6 — Native Incident Triage

P6 is additive to the tested P5 installation. Do not overwrite P5's validation component or the existing P3 collectors.

## Windows PowerShell — safe installation
1. Stop Angular and FastAPI with Ctrl+C. Leave PostgreSQL running.
2. Open a NEW PowerShell window and run each command separately.

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
```

Back up current working files:

```powershell
New-Item -ItemType Directory -Path ".\p6-backup" -Force
Copy-Item ".\backend\models.py" ".\p6-backup\models.py" -Force
Copy-Item ".\backend\main.py" ".\p6-backup\main.py" -Force
Copy-Item ".\frontend\src\main.ts" ".\p6-backup\main.ts" -Force
```

Back up the DB outside the repository, keeping it private:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p6.dump" purpleforge
```

Unzip to a staging directory, NOT directly over the project:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p6-no-docker.zip" -DestinationPath ".\p6-staging" -Force
```

**Important:** Compare three replacement files before copying. This package is based on the most recently shared working P5 files. If you edited them since, merge those changes first.

```powershell
git diff --no-index ".\backend\main.py" ".\p6-staging\backend\main.py"
git diff --no-index ".\frontend\src\main.ts" ".\p6-staging\frontend\src\main.ts"
```

Copy source files:

```powershell
Copy-Item ".\p6-staging\backend\main.py" ".\backend\main.py" -Force
Copy-Item ".\p6-staging\backend\models.py" ".\backend\models.py" -Force
Copy-Item ".\p6-staging\backend\incidents" ".\backend\incidents" -Recurse -Force
Copy-Item ".\p6-staging\backend\migrations\versions\0005_p6_incidents.py" ".\backend\migrations\versions\0005_p6_incidents.py" -Force
Copy-Item ".\p6-staging\frontend\src\main.ts" ".\frontend\src\main.ts" -Force
Copy-Item ".\p6-staging\frontend\src\p6-incidents.component.ts" ".\frontend\src\p6-incidents.component.ts" -Force
Copy-Item ".\p6-staging\tests\test_p6_incidents.py" ".\tests\test_p6_incidents.py" -Force
```

Inspect schema status, then migrate:

```powershell
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
```

Expected: `0005_p6_incidents (head)`. Never stamp or reset your database to force it through.

Verify tables:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -d purpleforge -c "\dt incident_*"
```

Run tests:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p6_incidents.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

PowerShell terminal 1, run backend without reload to reduce watch overhead:

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

PowerShell terminal 2, Angular:

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

Swagger: http://127.0.0.1:8000/docs . Angular: http://localhost:4200 .

## Manual test, no VMs required
1. Log in as admin. Visit **Incidents**.
2. Choose a P4 finding from the drop-down. Give it a meaningful title, select Create incident.
3. Open the case. Change status Open -> Investigating; add a note.
4. Click Find related evidence (60 min). This links up to 25 additional *unlinked* findings for the same asset during the case's 60-minute lookback through current time. The linking does not infer compromise.
5. Verify linked findings. Only then move to Resolved or False Positive with an analyst decision.
6. Open Telemetry, Detections, Validation and verify P1–P5 still load.
7. Verify opening Incidents does not trigger a repeated request loop: Chrome F12 > Network > Fetch/XHR. One bounded 3-request read batch should occur per entry/refresh.

## Optional live VMware check
Turn on Ubuntu (192.168.37.20) and Windows 10 (192.168.37.128). Confirm existing Journald, Suricata, Sysmon, Security collectors are receiving. Generate harmless marker telemetry and manually evaluate the P4 detection rule. Return to P6 and create or correlate the resulting finding. No new collector, agent, exploits or scans are required.

Ubuntu:
```bash
sudo systemctl is-active purpleforge-journal
sudo systemctl is-active suricata
sudo systemctl is-active purpleforge-suricata-shipper
logger -t purpleforge-p6 'P4 detection validation test'
```

Windows 10 PowerShell:
```powershell
Get-ScheduledTask | Where-Object TaskName -like "PurpleForge*" | Select-Object TaskName,State
powershell.exe -NoProfile -Command "Write-Output 'PurpleForge P6 test'"
```

## Reliability and limitations
This is an analyst-initiated case workflow. It does not automatically evaluate telemetry, infer attack chains, deduplicate incidents across multiple correlated entities, create tickets, or contain hosts. Correlation is same-asset/time-window only. Review evidence manually. The service uses the existing auth/RBAC dependency and audit log. Request lists and correlation are capped to avoid large queries on your machine. Keep backups and never commit `.env` or database dumps.

## Git commit (after tests/build)
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git add backend/main.py backend/models.py backend/incidents backend/migrations/versions/0005_p6_incidents.py frontend/src/main.ts frontend/src/p6-incidents.component.ts tests/test_p6_incidents.py
git commit -m "feat(p6): add incident triage and evidence-linked case management"
```
