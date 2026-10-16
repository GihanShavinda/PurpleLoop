# PurpleForge AI — P8 Manual Threat Intelligence & IOC Enrichment (No Docker)

**Scope:** This is a proposed P8 extension based on P7, not a verified original P8 milestone specification. It does not access external threat feeds, run attacks, or block indicators. It performs bounded, explicit matching of manually reviewed indicators against stored telemetry. No VMware changes are necessary for initial tests.

## 1. Stop local application processes

Press Ctrl+C in the existing FastAPI and Angular terminal windows. Leave PostgreSQL running. No need to shut down native collectors.

## 2. Back up the project and database — Windows Host PowerShell

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
git status
New-Item -ItemType Directory -Path '.\p8-backup' -Force
Copy-Item '.\backend\main.py' '.\p8-backup\main.py' -Force
Copy-Item '.\backend\models.py' '.\p8-backup\models.py' -Force
Copy-Item '.\frontend\src\main.ts' '.\p8-backup\main.ts' -Force
& 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-before-p8.dump" purpleforge
```

Keep the backup private. Do not commit database dumps or secrets.

## 3. Extract to staging (not directly into the project)

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p8-no-docker.zip" -DestinationPath '.\p8-staging' -Force
Get-ChildItem '.\p8-staging' -Recurse -File
```

If you edited P7 since the last package, compare before replacing:

```powershell
git diff --no-index '.\backend\main.py' '.\p8-staging\backend\main.py'
git diff --no-index '.\frontend\src\main.ts' '.\p8-staging\frontend\src\main.ts'
```

Do not overwrite local custom changes without merging them. Diff exit code 1 means differences found.

## 4. Copy changed files

```powershell
Copy-Item '.\p8-staging\backend\main.py' '.\backend\main.py' -Force
Copy-Item '.\p8-staging\backend\models.py' '.\backend\models.py' -Force
Copy-Item '.\p8-staging\backend\intelligence' '.\backend\intelligence' -Recurse -Force
Copy-Item '.\p8-staging\backend\migrations\versions\0007_p8_intelligence.py' '.\backend\migrations\versions\0007_p8_intelligence.py' -Force
Copy-Item '.\p8-staging\frontend\src\main.ts' '.\frontend\src\main.ts' -Force
Copy-Item '.\p8-staging\frontend\src\p8-intelligence.component.ts' '.\frontend\src\p8-intelligence.component.ts' -Force
Copy-Item '.\p8-staging\tests\test_p8_matching.py' '.\tests\test_p8_matching.py' -Force
```

## 5. Migrate PostgreSQL

```powershell
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
```

Expected final revision: `0007_p8_intelligence (head)`. Previous revision should be `0006_p7_hunting`.

Verify the tables:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U purpleforge_user -h 127.0.0.1 -p 5433 -d purpleforge -c '\dt intelligence_*'
```

## 6. Unit and regression tests

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p8_matching.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

## 7. Start FastAPI — PowerShell Terminal 1

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/docs` for `/intelligence/indicators`, `/intelligence/enrich`, `/intelligence/matches`, `/intelligence/summary`.

## 8. Build and run Angular — PowerShell Terminal 2

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop\frontend'
npm run build
npm start
```

Visit `http://localhost:4200` and open **Threat Intelligence**. Build the app before opening the page; stop on any TypeScript or backend errors.

## 9. Initial P8 manual test — no VMs needed

1. Use a known benign test value from an event already stored in the past hour (e.g. process name `powershell.exe` or IP address seen in Suricata). Do not label the match as proof of compromise.
2. Register an indicator (type `process` for process name), enter source label `local-lab-validation`, confidence `50`, and an explanation.
3. Click **Enrich stored telemetry**. Set lookback 1–24 hours and max events <= 1000. If Suricata volumes are high, prefer a recent Windows/Sysmon event and a short window.
4. Check **Evidence matches**. If empty, verify your chosen indicator really exists in the matched message/allowlisted payload fields and that the event is in the checked latest event window.
5. Click Enrich a second time. Matching event/indicator pairs should not create duplicates.
6. Disable the test IOC and confirm new enrichment no longer matches it.

## 10. Optional live VMware test

Windows 10 VM: verify Sysmon task Running, then run a harmless PowerShell process:

```powershell
Get-ScheduledTask -TaskName 'PurpleForge Sysmon Collector' | Select-Object TaskName, State
powershell.exe -NoProfile -Command "Write-Output 'PurpleForge P8 test'"
Get-Content 'C:\PurpleForge\logs\sysmon-collector.log' -Tail 10
```

If recording a powershell process indicator, ensure the new event exists in Telemetry first. Run enrichment shortly afterward. No attacks, vulnerable VMs, or containers are required.

## 11. Commit only after verification

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
git status
git add backend/main.py backend/models.py backend/intelligence backend/migrations/versions/0007_p8_intelligence.py frontend/src/main.ts frontend/src/p8-intelligence.component.ts tests/test_p8_matching.py
git commit -m 'feat(p8): add manual threat intelligence enrichment'
```

### Limitations

This is deliberately a bounded lab-first IOC prototype. It does not include STIX/TAXII, automatic remote feeds, background matching, risk assessment, malware analysis, external reputation requests, or containment. A match is an observation, not evidence of maliciousness. One enrichment pass checks up to 100 indicators and 1,000 events, potentially ~100k comparisons; on slow PCs start with 100–200 events.
