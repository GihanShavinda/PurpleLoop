# PurpleForge AI P4 — step-by-step native Windows installation

P4 is an additive, advisory-only detection engine. It does **not** ingest Sigma YAML, execute YARA scans, or automatically apply Suricata rules. Instead, `rule_kind` records provenance and a safe, allowlisted predicate matches ingested P3 event fields. Production-compatible Sigma/YARA compilers and streaming evaluation are future work.

## 0 — Back up your project and DB (Windows host, PowerShell)

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h 127.0.0.1 -p 5433 -U purpleforge_user -Fc -f "$env:USERPROFILE\Desktop\purpleforge-before-p4.dump" purpleforge
```

Do not share this dump; it may include telemetry. Never overwrite your `.env` or remove your collectors.

## 1 — Apply the update

Extract the ZIP to `F:\My_Projects\PurpleLoop\PurpleLoop` **preserving directory structure**. Existing updated files are complete replacements: `backend/models.py`, `backend/main.py`, `frontend/src/main.ts`. All others are new.

## 2 — Migrate (Windows host, PowerShell)

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
```

Expected `0003_p4_detections (head)`. Migration creates two new tables; it does not clear existing telemetry.

## 3 — Test

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests/test_p4_engine.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

## 4 — Start FastAPI (host terminal 1)

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## 5 — Start Angular (host terminal 2)

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm install
npm run build
npm start
```

Open `http://localhost:4200` and sign in as your administrator. Choose **Detections** in the left sidebar.

## 6 — First P4 rule: safe Windows process-creation smoke test

- Name: `P4 Lab PowerShell Process Evidence`
- Kind: `Sigma-style`
- Severity: `medium`
- Event type: leave blank (the collector event names may differ)
- Field: `message`
- Operator: `contains`
- Expected: `powershell`

Click **Create rule**, then **Evaluate latest 500 events**. A finding appears only if recent stored telemetry has `powershell` in its message. If no finding, inspect **Telemetry → Events** and choose a value that actually exists. `event_type`, `message`, and allowlisted nested payload fields are supported.

Suricata example: `payload.alert.signature` contains `test` (only works for alert-type payloads with that structure). Rules are metadata predicates; they are *not* a full Suricata rule parser.

## 7 — Verify API via Swagger

`http://127.0.0.1:8000/docs`: login to obtain JWT, click Authorize; then inspect `GET /detections/rules`, `POST /detections/evaluate`, `GET /detections/findings`, and `GET /detections/summary`.

P4 requires explicit human evaluation; it does not run automatically for each new event. Findings are unique by rule + event and re-evaluation should add 0 findings for previously evaluated matches. Evaluation is bounded to a maximum of 2,000 most recently received events. RBAC allows administrators / detection engineers / purple team engineers to write rules or run evaluation; other authenticated roles can read.

## 8 — Git

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
git add backend/models.py backend/main.py backend/detections backend/migrations/versions/0003_p4_detections.py frontend/src/main.ts tests/test_p4_engine.py docs/P4_INSTALL.md
git commit -m "feat(p4): add native telemetry detection rules and evidence findings"
```

## Troubleshooting

- `No module named ...`: run from project root as shown.
- `relation detection_rules does not exist`: migration did not apply to the configured database.
- `422`: rule must use an allowlisted field and supported operator.
- No findings: source event fields may differ; inspect real telemetry payloads; evaluator only checks latest N events.
- Angular build failure: capture `npm run build` output before modifying files.
- If running a custom P3 build not matching the provided P3 ZIP, compare replacement files before applying.
