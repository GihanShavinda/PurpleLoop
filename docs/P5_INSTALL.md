# P5 Installation — No Docker (Windows host + VMware)

## Safeguard existing P4

Keep Ubuntu and Windows VM collectors untouched. P5 operates on already-ingested telemetry and existing P4 detection findings.
Before any update, stop the FastAPI and Angular development servers. Back up the application repository and PostgreSQL database.
Do NOT overwrite `.env`, secrets, `backend/telemetry`, `backend/detections`, or collector files.

## Windows PowerShell — commands run individually from the project root

```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
git status
New-Item -ItemType Directory -Force ".\backup-p5"
Copy-Item ".\backend\main.py" ".\backup-p5\main.py"
Copy-Item ".\backend\models.py" ".\backup-p5\models.py"
Copy-Item ".\frontend\src\main.ts" ".\backup-p5\main.ts"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p5.dump" purpleforge
```

Keep backup-p5 and dumps OUT of version control.

Extract the downloaded ZIP into a staging folder and review the changes before copying:
```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\purpleforge-ai-p5-validation-no-docker.zip" -DestinationPath ".\p5-staging" -Force
Get-ChildItem ".\p5-staging" -Recurse -File
```

The replacement main.py/models.py/main.ts were generated from the earlier P4 delivery in this conversation; if you made *subsequent edits*, manually reconcile them before overwriting.

```powershell
Copy-Item ".\p5-staging\backend\models.py" ".\backend\models.py" -Force
Copy-Item ".\p5-staging\backend\main.py" ".\backend\main.py" -Force
Copy-Item ".\p5-staging\backend\validation" ".\backend\validation" -Recurse -Force
Copy-Item ".\p5-staging\backend\migrations\versions\0004_p5_validation.py" ".\backend\migrations\versions\0004_p5_validation.py" -Force
Copy-Item ".\p5-staging\frontend\src\p5-validation.component.ts" ".\frontend\src\p5-validation.component.ts" -Force
Copy-Item ".\p5-staging\frontend\src\main.ts" ".\frontend\src\main.ts" -Force
Copy-Item ".\p5-staging\tests\test_p5_coverage.py" ".\tests\test_p5_coverage.py" -Force
```

Database migration:
```powershell
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
```
Expected `0004_p5_validation (head)`. Inspect tables:
```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -d purpleforge -c "\dt validation_*"
```

Tests:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p5_coverage.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
```

Terminal 1: backend:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop"
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2: frontend:
```powershell
cd "F:\My_Projects\PurpleLoop\PurpleLoop\frontend"
npm run build
npm start
```

Browser: http://localhost:4200, login, select **Validation**. API Swagger: http://127.0.0.1:8000/docs.

## Manual P5 validation — safe VMware workflow

1. From the P4 Detections UI, confirm the Ubuntu test rule or Windows PowerShell test rule exists and is enabled.
2. In P5 Validation, create a scenario tied to the **matching rule**, **correct VM asset**, and a technique *reference*.
3. Start the scenario. Note its start time.
4. On Ubuntu VM (192.168.37.20), generate a benign journal marker matching your P4 rule using `logger -t purpleforge-p5 "P4 detection validation test"`. If you use Windows instead, on the Windows 10 VM (192.168.37.128) run `powershell.exe -NoProfile -Command "Write-Output 'PurpleForge validation'"` for Sysmon Event ID 1.
5. Wait for the matching event to arrive in Angular Telemetry. In Angular Detections, press **Evaluate latest 500 events**. If high-volume Suricata events crowd out the marker, pause *only* the shipper temporarily: `sudo systemctl stop purpleforge-suricata-shipper` on Ubuntu; generate the marker, evaluate immediately, and restart with `sudo systemctl start purpleforge-suricata-shipper`.
6. Return to Validation, click **Finish test** and verify status `passed` with evidence count >=1. Click **Evidence** for linked event IDs. If no matching P4 finding, expect `failed`, not an invented pass.
7. Repeat with an intentionally unmatched rule to verify `failed`. Use **Inconclusive** if the test wasn't performed.

The technique ID records an analyst-chosen hypothesis, NOT proof of the technique; use only valid, justified mappings. The first release does NOT execute attacks, does NOT auto-evaluate P4 on ingestion, and does NOT claim whole-matrix coverage.

## Troubleshooting
- `422`: check technique ID (T#### or T####.###), rule and asset IDs, and required instructions.
- `404`: verify P5 router was included in backend/main.py.
- `401/403`: login again; mutations require Administrator / Purple Team Engineer / Detection Engineer.
- `0 findings`: validate event is ingested, event type/message matches selected P4 rule, use correct asset, run P4 evaluation *after the test event*, and finish only afterward.
- duplicate finish: returns HTTP 409. Existing evidence is preserved.
- Angular compile failure: check your `main.ts` matches the earlier P4 version before replacement and `p5-validation.component.ts` is present.

### Notes
- P5 does NOT require running VMs for database migrations or UI setup; Ubuntu/Windows 10 only for live verification.
- P5 evaluates runs from existing P4 findings and source telemetry timestamps. Clocks must be synchronized across Windows host and VMs.
- Existing P4 evaluation has a bounded 500-event default; a busy Suricata source can crowd out intended evidence.
- The coverage percentage is per configured P5 scenarios, not percentage of MITRE ATT&CK.
- This is a first-version integration package, not a production-validated system.
