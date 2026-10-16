# PurpleForge AI — P7 Threat Hunting, Windows PowerShell, No Docker

The package is based on the supplied P6 release. It is an additive P7 migration; keep your existing P5/P6 components unchanged.

## 0. Prerequisites
- P6 committed and functional; migration `0005_p6_incidents` installed.
- PostgreSQL 18 on port 5433, Python .venv, Angular/npm installed.
- VMware VMs optional. Stored PostgreSQL telemetry is sufficient for the initial tests.

## 1. Stop backend and Angular in their terminals (Ctrl+C).

## 2. Windows host PowerShell commands, from the project root
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
New-Item -ItemType Directory -Force .\p7-backup
Copy-Item .\backend\main.py .\p7-backup\main.py
Copy-Item .\backend\models.py .\p7-backup\models.py
Copy-Item .\frontend\src\main.ts .\p7-backup\main.ts
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p7.dump" purpleforge
```

## 3. Extract and compare before replacing (do not overwrite customized source blindly)
```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p7-no-docker.zip" -DestinationPath .\p7-staging -Force
git diff --no-index .\backend\main.py .\p7-staging\backend\main.py
git diff --no-index .\frontend\src\main.ts .\p7-staging\frontend\src\main.ts
```
Note: `git diff --no-index` returns exit code 1 when files differ, which is normal.

## 4. Apply replacement files after reviewing differences
```powershell
Copy-Item .\p7-staging\backend\main.py .\backend\main.py -Force
Copy-Item .\p7-staging\backend\models.py .\backend\models.py -Force
Copy-Item .\p7-staging\backend\hunting .\backend\hunting -Recurse -Force
Copy-Item .\p7-staging\backend\migrations\versions\0006_p7_hunting.py .\backend\migrations\versions\0006_p7_hunting.py -Force
Copy-Item .\p7-staging\frontend\src\main.ts .\frontend\src\main.ts -Force
Copy-Item .\p7-staging\frontend\src\p7-hunting.component.ts .\frontend\src\p7-hunting.component.ts -Force
Copy-Item .\p7-staging\tests\test_p7_query.py .\tests\test_p7_query.py -Force
```

## 5. Database and tests (Windows host, project root)
```powershell
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p7_query.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```
Expected migration `0006_p7_hunting (head)`. There are two new tables, `saved_hunts` and `hunt_evidence`.

## 6. Start server (terminal 1)
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 7. Start frontend (terminal 2)
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```
Visit http://localhost:4200 and http://127.0.0.1:8000/docs. P7 APIs: POST /hunting/search, POST /hunting/ioc, GET/POST /hunting/saved, DELETE /hunting/saved/{id}, POST/GET /hunting/incidents/{id}/evidence.

## 8. Manual verification
1. Open Threat Hunting. Select last hour or extend up to 7 days. Search without filters, max 100 records per page.
2. Filter asset to `ubuntu2404` and event type from the Telemetry page; search again.
3. Search message for an actually recorded journal string; verify results are limited to time range.
4. Save the hunt, reselect and Apply; verify saved filters load.
5. For IOC lookup use an IP observed in Suricata events; confirm this is metadata-only.
6. Create/open P6 case for the same asset; choose the case beside a matching event; click Link evidence. A different-asset case should be rejected by the server.
7. Check Incidents works, and P1–P6 pages still load without repeated request loops.
8. VMware is not needed for these stored-data tests. Optionally start Ubuntu and Windows 10 collectors, create a benign event, then hunt its exact message.

## 9. Git commit (only after successful tests)
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
git add backend/main.py backend/models.py backend/hunting backend/migrations/versions/0006_p7_hunting.py frontend/src/main.ts frontend/src/p7-hunting.component.ts tests/test_p7_query.py
git commit -m "feat(p7): add bounded threat hunting and incident evidence"
```
Do not commit DB dumps, .env, API keys, or staging/backups. Restore backed-up source files if build fails; never downgrade the database without a reviewed migration plan.
