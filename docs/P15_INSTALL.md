# PurpleForge AI — P15 installation (native Windows, no Docker)

This is a source update to P14, not a standalone project. **P15 is on-demand, offline historical statistical outlier detection.** IsolationForest analyzes volumes, warning/error counts and distinct event types in zero-filled time buckets. It is not a malware detector. There is no automatic polling, VM activity, or response.

## Before installing
- Stop FastAPI and Angular (`Ctrl+C`), leave PostgreSQL running.
- Check `git status`, commit P14, back up three replacement files and the PostgreSQL database.
- The ZIP comes from the P14 package; if you have local edits, compare and merge instead of overwriting.
- **Preserve your local P13 correction** for the `linux.journal` event type; this archive does not touch `backend/simulation/routes.py`.

## Windows PowerShell (project root)
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
New-Item -ItemType Directory -Path ".\p15-backup" -Force
Copy-Item ".\backend\main.py" ".\p15-backup\main.py"
Copy-Item ".\backend\models.py" ".\p15-backup\models.py"
Copy-Item ".\frontend\src\main.ts" ".\p15-backup\main.ts"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-before-p15.dump" purpleforge
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p15-no-docker.zip" -DestinationPath ".\p15-staging" -Force
# Compare with current files before overwriting. 1 from git diff means differences exist.
git diff --no-index ".\backend\models.py" ".\p15-staging\backend\models.py"
git diff --no-index ".\frontend\src\main.ts" ".\p15-staging\frontend\src\main.ts"
Copy-Item ".\p15-staging\backend\main.py" ".\backend\main.py" -Force
Copy-Item ".\p15-staging\backend\models.py" ".\backend\models.py" -Force
Copy-Item ".\p15-staging\backend\anomaly" ".\backend\anomaly" -Recurse -Force
Copy-Item ".\p15-staging\backend\migrations\versions\0014_p15_anomaly.py" ".\backend\migrations\versions\" -Force
Copy-Item ".\p15-staging\frontend\src\main.ts" ".\frontend\src\main.ts" -Force
Copy-Item ".\p15-staging\frontend\src\p15-anomaly.component.ts" ".\frontend\src\" -Force
Copy-Item ".\p15-staging\tests\test_p15_engine.py" ".\tests\" -Force
.\backend\.venv\Scripts\python.exe -m pip install "scikit-learn>=1.5,<2.0"
.\backend\.venv\Scripts\python.exe -c "import backend.models;import backend.main;import sklearn;print('P15 imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p15_engine.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```
Expected new migration head: `0014_p15_anomaly`.

## Start in separate PowerShell windows
Terminal 1, project root:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Terminal 2:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

## Test manually
1. Open `http://localhost:4200` → Anomaly Detection, choose `ubuntu2404` or the Windows 10 telemetry asset.
2. Choose 6-hour lookback, 15-minute buckets (24 buckets), 8% contamination.
3. Click Run analysis exactly once. Requires >=30 events and <=5000 events in that window.
4. Inspect recorded outlier buckets. Interpret outliers as statistical deviations, not confirmed attacks.
5. Open the same run again: results must persist in PostgreSQL.
6. Existing collectors and VMs can be off; historical telemetry must be inside the chosen last-N-hours window. Optional Ubuntu test: `logger -t purpleforge-p15 "PurpleForge P15 benign telemetry check"` creates a benign event, but one marker need not cause an outlier.
7. No background scheduler, automatic remedial action, or remote execution is included.

## Commit only after tests pass
```powershell
git add backend/main.py backend/models.py backend/anomaly backend/migrations/versions/0014_p15_anomaly.py frontend/src/main.ts frontend/src/p15-anomaly.component.ts tests/test_p15_engine.py requirements-p15.txt
git commit -m "feat(p15): add bounded explainable anomaly analysis"
```
