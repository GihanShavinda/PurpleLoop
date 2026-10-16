# P12 no-Docker installation and verification

## Scope
P12 creates an explicitly simulation-only rehearsal of a previously approved and simulated P11 proposal. A rollback is **only a recorded change in rehearsal state**. It never reverts a firewall, VM or endpoint. No native response connectors are included.

## Windows PowerShell — from project root

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
# stop Angular and FastAPI using Ctrl+C before replacing files
Copy-Item backend/models.py backend/models.py.pre-p12 -Force
Copy-Item backend/main.py backend/main.py.pre-p12 -Force
Copy-Item frontend/src/main.ts frontend/src/main.ts.pre-p12 -Force
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p12.dump" purpleforge
Expand-Archive "$env:USERPROFILE\Downloads\purpleforge-ai-p12-no-docker.zip" .\p12-staging -Force
# inspect the three replacements first, especially if you edited P11 after installing it
Copy-Item .\p12-staging\backend\main.py .\backend\main.py -Force
Copy-Item .\p12-staging\backend\models.py .\backend\models.py -Force
Copy-Item .\p12-staging\backend\response .\backend\response -Recurse -Force
Copy-Item .\p12-staging\backend\migrations\versions\0011_p12_response.py .\backend\migrations\versions\ -Force
Copy-Item .\p12-staging\frontend\src\main.ts .\frontend\src\main.ts -Force
Copy-Item .\p12-staging\frontend\src\p12-response.component.ts .\frontend\src\ -Force
Copy-Item .\p12-staging\tests\test_p12_planner.py .\tests\ -Force
.\backend\.venv\Scripts\python.exe -c "import backend.models; import backend.main; print('imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
# Expect 0010_p11_soar before upgrade
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
# Expect 0011_p12_response
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p12_planner.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

## Start servers (separate PowerShell windows)

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

## Manual test (no VMs required)
1. On SOAR, use a P11 proposal with status `simulated`, previously approved by a distinct account.
2. Navigate to Response Lab and choose that proposal; select **Create rehearsal**.
3. Confirm `SIMULATION_ONLY`, zero external actions and zero VM changes.
4. Enter a closure note of at least ten characters; click **Close simulation**.
5. Confirm status `rolled_back_simulation`. Inspect GET `/response/rehearsals/{id}/audit` using an authorized session.
6. Confirm a second rollback fails with 409. Review existing P1–P11 pages and run Angular build.

Do not run any real VM isolation commands for P12. This package does not support actual reversible infrastructure execution.
