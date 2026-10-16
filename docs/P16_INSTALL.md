# PurpleForge AI P16 — Evidence-Grounded Investigation Assistant (No Docker)

Scope: Deterministic local analyst drafts over up to 25 existing P15 anomaly observations, optionally including one same-asset P9 correlation case. No LLM, execution, containment, prompt-instruction following, or automatic polling. Not a claim of malicious activity.

## Install from project root in Windows PowerShell

Stop existing Angular and FastAPI terminals with Ctrl+C first. Backup your Git commit and PostgreSQL with pg_dump. Extract ZIP to a temporary staging directory. Compare updated files with any newer changes before copying.

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
git status
& 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-before-p16.dump" purpleforge
Expand-Archive "$env:USERPROFILE\Downloads\purpleforge-ai-p16-no-docker.zip" '.\p16-staging' -Force
Copy-Item '.\p16-staging\backend\main.py' '.\backend\main.py' -Force
Copy-Item '.\p16-staging\backend\models.py' '.\backend\models.py' -Force
Copy-Item '.\p16-staging\backend\investigation' '.\backend\investigation' -Recurse -Force
Copy-Item '.\p16-staging\backend\migrations\versions\0015_p16_investigation.py' '.\backend\migrations\versions\' -Force
Copy-Item '.\p16-staging\frontend\src\main.ts' '.\frontend\src\main.ts' -Force
Copy-Item '.\p16-staging\frontend\src\p16-investigation.component.ts' '.\frontend\src\' -Force
Copy-Item '.\p16-staging\tests\test_p16_composer.py' '.\tests\' -Force
.\backend\.venv\Scripts\python.exe -c 'import backend.models; import backend.main; print("P16 imports OK")'
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p16_composer.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Before upgrade, expected revision: `0014_p15_anomaly`; after: `0015_p16_investigation`.

FastAPI Terminal 1:
```
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Angular Terminal 2:
```
cd 'F:\My_Projects\PurpleLoop\PurpleLoop\frontend'
npm run build
npm start
```

## Manual test

1. Open http://localhost:4200, sign in as an authorized analyst, select Investigation Assistant.
2. Select a completed P15 anomaly analysis for ubuntu2404 (or another asset with a completed run).
3. Optionally select a P9 correlation for the **same asset**. A different-asset selection is rejected.
4. Click Generate evidence draft. Check exact observation identifiers and risk metadata, verify uncertainty language.
5. Enter an evidence-based note of 10+ characters, Accept or Reject, refresh, and verify persisted status.
6. Verify P1–P15 screens still work. Existing VMware machines need not be powered on.

## Guardrails

- Drafts are immutable JSON snapshots; reviews change status/notes only.
- No external model/provider. Inputs such as journal text are never interpreted as instructions.
- At most 25 anomaly observations; no automatic browser polling.
- Proposal recommendations are advisory; no automatic SOAR actions.
- The matched asset must be the same across anomaly run and correlation case.

## Git commit
```
git add backend/main.py backend/models.py backend/investigation backend/migrations/versions/0015_p16_investigation.py frontend/src/main.ts frontend/src/p16-investigation.component.ts tests/test_p16_composer.py
git commit -m 'feat(p16): add bounded evidence-grounded investigation drafts and review'
```
