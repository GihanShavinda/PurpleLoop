# PurpleForge P14 — No Docker Installation

This is a source update for an existing P13 installation. It does not ship the rest of P1–P13.
The P13 package baseline had a mistaken `linux_journal` equality check in `backend/simulation/routes.py`; retain your LOCAL fixed `linux.journal` version. P14 does NOT replace that file.

## Windows PowerShell: separate commands

Stop Angular and FastAPI with Ctrl+C.

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p14.dump" purpleforge
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p14-no-docker.zip" -DestinationPath ".\p14-staging" -Force
Copy-Item ".\backend\main.py" ".\backend\main.py.pre-p14"
Copy-Item ".\backend\models.py" ".\backend\models.py.pre-p14"
Copy-Item ".\frontend\src\main.ts" ".\frontend\src\main.ts.pre-p14"
# Compare updated source files before overwriting, especially local changes.
git diff --no-index ".\backend\main.py" ".\p14-staging\backend\main.py"
Copy-Item ".\p14-staging\backend\main.py" ".\backend\main.py" -Force
Copy-Item ".\p14-staging\backend\models.py" ".\backend\models.py" -Force
Copy-Item ".\p14-staging\backend\coverage" ".\backend\coverage" -Recurse -Force
Copy-Item ".\p14-staging\backend\migrations\versions\0013_p14_coverage.py" ".\backend\migrations\versions\" -Force
Copy-Item ".\p14-staging\frontend\src\main.ts" ".\frontend\src\main.ts" -Force
Copy-Item ".\p14-staging\frontend\src\p14-coverage.component.ts" ".\frontend\src\" -Force
Copy-Item ".\p14-staging\tests\test_p14_logic.py" ".\tests\" -Force
.\backend\.venv\Scripts\python.exe -c "import backend.models;import backend.main;print('P14 imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p14_logic.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Expected Alembic head: `0013_p14_coverage`.

Backend Terminal 1:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Angular Terminal 2:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

## Manual verification

1. P13: confirm a run is Verified and contains an evidence_event_id.
2. P4 Detections: ensure a finding exists for THAT exact evidence event (manual evaluate if recent).
3. P14 Detection Coverage: select the verified run and its intended P4 rule; click Assess exact evidence.
4. `detected` means linked P4 finding exists; `not_detected` means it does not. Results are immutable snapshots: to reassess after generating a finding, create a new P13 run and assess it.
5. Assessing the same pair twice reuses the assessment; scope is operator-selected exercises, not all MITRE ATT&CK techniques.
6. Ubuntu CLI is optional if using a previously verified run. For a new run, use the exact marker command displayed on the P13 page; don't invent one.
7. This module never starts attacks, scans, or makes VM changes.

Run `git status`, stage only the P14 files, and commit after tests.
