# PurpleForge AI P10 — Native Evidence-grounded SOC Analyst

This milestone does **not** call an LLM. It builds explicit deterministic drafts from P9 evidence, with analyst review and audit logs. No Docker, no polling, no automated containment.

## Prerequisites
- Completed P9 migration 0008_p9_correlation and P9 correlation cases.
- Windows host Python virtual environment, PostgreSQL and Angular dependencies already installed.
- Git commit of P9. P10 assumes existing P1–P9 source files are present; this is not a standalone distribution.

## PowerShell commands — Windows host

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
# Stop backend/frontend servers with Ctrl+C before modifying files.
New-Item -ItemType Directory -Force .\p10-backup
Copy-Item .\backend\main.py .\p10-backup\main.py
Copy-Item .\backend\models.py .\p10-backup\models.py
Copy-Item .\frontend\src\main.ts .\p10-backup\main.ts
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p10.dump" purpleforge
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p10-no-docker.zip" -DestinationPath .\p10-staging -Force
# Review replacements before copying
 git diff --no-index .\backend\models.py .\p10-staging\backend\models.py
 git diff --no-index .\frontend\src\main.ts .\p10-staging\frontend\src\main.ts
Copy-Item .\p10-staging\backend\main.py .\backend\main.py -Force
Copy-Item .\p10-staging\backend\models.py .\backend\models.py -Force
Copy-Item .\p10-staging\backend\analyst .\backend\analyst -Recurse -Force
Copy-Item .\p10-staging\backend\migrations\versions\0009_p10_analyst.py .\backend\migrations\versions\ -Force
Copy-Item .\p10-staging\frontend\src\main.ts .\frontend\src\main.ts -Force
Copy-Item .\p10-staging\frontend\src\p10-analyst.component.ts .\frontend\src\ -Force
Copy-Item .\p10-staging\tests\test_p10_report.py .\tests\ -Force
.\backend\.venv\Scripts\python.exe -c "import backend.models; import backend.main; print('P10 imports OK')"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p10_report.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Expected revision: `0009_p10_analyst (head)`.

### Terminal 1 — backend
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2 — Angular
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

## Browser verification
1. Visit http://localhost:4200 and sign in.
2. Select **AI Analyst** on left navigation.
3. Select a P9 correlation case from `ubuntu2404` and click Generate evidence draft.
4. Inspect the summary, limitations, evidence timeline and recommendations.
5. Enter a review note and select Accept or Reject.
6. Refresh: decision and review note should persist.
7. Repeat creation: each explicit click creates a separate immutable report snapshot. Avoid repeated generation unless needed.

## Optional VMware validation
No VM is required when stored P9 correlation cases already exist. To create new evidence, start Ubuntu `192.168.37.20` and execute:
```bash
sudo systemctl is-active purpleforge-journal
logger -t purpleforge-p10 "PurpleForge P10 SOC analyst evidence validation"
journalctl -t purpleforge-p10 -n 5 --no-pager
```
Wait until the P3 event reaches Telemetry, create a matching P4 rule, evaluate it, then create a P9 correlation case. Finally select the P9 case in P10.

## Security boundaries
- No external model provider or network request beyond existing localhost API.
- P10 never automatically tags evidence with MITRE techniques, issues block actions, or asserts compromise.
- Inputs from telemetry are untrusted and displayed with Angular interpolation, not HTML insertion.
- One report may contain at most 50 linked evidence rows, each message at most 240 characters.
- Backups, raw telemetry and collector credentials must not be committed to Git.
