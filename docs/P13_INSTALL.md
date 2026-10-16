# PurpleForge AI P13 — Manual Lab Simulation (No Docker)

## Scope
Authorized synthetic Ubuntu journal event validation. No remote command execution, no exploit, no active scans, no VMware modification. P12 is unchanged.

## Installation (Windows PowerShell; project root F:\My_Projects\PurpleLoop\PurpleLoop)
Stop FastAPI and Angular first. Confirm P12 is committed. Back up database before migration.

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p13.dump" purpleforge
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p13-no-docker.zip" -DestinationPath ".\p13-staging" -Force
```

Inspect diffs before copying complete replacements:
```powershell
git diff --no-index .\backend\models.py .\p13-staging\backend\models.py
git diff --no-index .\frontend\src\main.ts .\p13-staging\frontend\src\main.ts
```

Only after reviewing diffs, copy:
```powershell
Copy-Item .\p13-staging\backend\models.py .\backend\models.py -Force
Copy-Item .\p13-staging\backend\main.py .\backend\main.py -Force
Copy-Item .\p13-staging\backend\simulation .\backend\simulation -Recurse -Force
Copy-Item .\p13-staging\backend\migrations\versions\0012_p13_simulation.py .\backend\migrations\versions\ -Force
Copy-Item .\p13-staging\frontend\src\main.ts .\frontend\src\main.ts -Force
Copy-Item .\p13-staging\frontend\src\p13-simulation.component.ts .\frontend\src\ -Force
Copy-Item .\p13-staging\tests\test_p13_scenarios.py .\tests\ -Force
```

Verify imports and migration:
```powershell
.\backend\.venv\Scripts\python.exe -c "import backend.models; import backend.main; print('P13 imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p13_scenarios.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Start backend (terminal 1):
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Start Angular (terminal 2):
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

## Live authorized validation
Power on Ubuntu 24.04 at 192.168.37.20, VMnet1. Run `sudo systemctl is-active purpleforge-journal` and check it is active.
Open Angular -> Lab Simulation; select `ubuntu2404`, click Start manual run. Copy the per-run `logger` command from the UI. Run it ONLY in the authorized Ubuntu VM terminal. Check `journalctl -t purpleforge-p13 -n 5 --no-pager`. Wait for journal ingestion, then click Verify evidence. Verified result includes exact telemetry event ID; before emission, Verify should return 409.

## Important security notes
- The API never executes guest commands or connects to guest SSH or VMware.
- Only Ubuntu assets with environment=lab are supported.
- Verify uses unique marker + same asset + received_at after run start.
- Runs expire after two hours if verified late.
- No automatic refresh, no background polling.
- No MITRE technique claim based solely on a marker.

## Git
```powershell
git status
git add backend/main.py backend/models.py backend/simulation backend/migrations/versions/0012_p13_simulation.py frontend/src/main.ts frontend/src/p13-simulation.component.ts tests/test_p13_scenarios.py docs/P13_INSTALL.md
git commit -m "feat(p13): add manual authorized lab simulation evidence verification"
```
