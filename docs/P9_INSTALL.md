# PurpleForge P9 — Windows + VMware installation (native, no Docker)

Scope: user-triggered same-asset correlation of P4 detection findings and P8 IOC matches within a bounded UTC window. Risk scores are transparent heuristics. This does not confirm an attack chain or create incidents automatically.

## Windows host, PowerShell, project root
1. Stop FastAPI and Angular with Ctrl+C. Keep PostgreSQL running. Ensure P8 is committed and `git status` is clean.
2. `cd "F:\My_Projects\PurpleLoop\PurpleLoop"`
3. `git status`
4. `Copy-Item .\backend\models.py .\backend\models.py.pre-p9`
5. `Copy-Item .\backend\main.py .\backend\main.py.pre-p9`
6. `Copy-Item .\frontend\src\main.ts .\frontend\src\main.ts.pre-p9`
7. `& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U purpleforge_user -h 127.0.0.1 -p 5433 -Fc -f "$env:USERPROFILE\Desktop\purpleforge-pre-p9.dump" purpleforge`
8. Download ZIP to Downloads; extract into staging:
   `Expand-Archive "$env:USERPROFILE\Downloads\purpleforge-ai-p9-no-docker.zip" .\p9-staging -Force`
9. Inspect diffs before overwriting:
   `git diff --no-index .\backend\models.py .\p9-staging\backend\models.py`
   `git diff --no-index .\frontend\src\main.ts .\p9-staging\frontend\src\main.ts`
   (exit status 1 is normal for a diff). If your P8 source differs from the provided baseline, merge rather than overwrite.
10. `Copy-Item .\p9-staging\backend\models.py .\backend\models.py -Force`
11. `Copy-Item .\p9-staging\backend\main.py .\backend\main.py -Force`
12. `Copy-Item .\p9-staging\backend\correlation .\backend\correlation -Recurse -Force`
13. `Copy-Item .\p9-staging\backend\migrations\versions\0008_p9_correlation.py .\backend\migrations\versions\ -Force`
14. `Copy-Item .\p9-staging\frontend\src\main.ts .\frontend\src\main.ts -Force`
15. `Copy-Item .\p9-staging\frontend\src\p9-correlation.component.ts .\frontend\src\ -Force`
16. `Copy-Item .\p9-staging\tests\test_p9_scoring.py .\tests\ -Force`
17. ` .\backend\.venv\Scripts\python.exe -c "import backend.models; import backend.main; print('P9 imports OK')"`
18. ` .\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current` (expect 0007)
19. ` .\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head`
20. ` .\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current` (expect 0008)
21. ` .\backend\.venv\Scripts\python.exe -m pytest tests\test_p9_scoring.py -v`
22. ` .\backend\.venv\Scripts\python.exe -m pytest tests -v`
23. Terminal 1: ` .\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
24. Terminal 2: `cd frontend`, `npm run build`, `npm start`.
25. Open http://localhost:4200, navigate Correlation. Select an asset with P4/P8 evidence in recent 60 mins, Evaluate, inspect timeline, Review. An empty result is legitimate if no eligible evidence exists.
26. Verify all older P1-P8 menus work. Commit only changed source/migration/test files, not .env, backup dumps or collector keys.

## Optional live lab test
Power on Ubuntu 24.04 (VMnet1, 192.168.37.20). Check:
`sudo systemctl is-active purpleforge-journal`
`sudo systemctl is-active suricata`
`sudo systemctl is-active purpleforge-suricata-shipper`
Generate a benign marker: `logger -t purpleforge-p9 "PurpleForge P9 correlation validation"`
Refresh Telemetry to verify receipt. Create a P4 rule matching the marker and explicitly evaluate P4; then run P9 correlation for ubuntu2404. Simply generating a journal event is insufficient to create P9 evidence without a P4 finding or P8 match.
Windows 10 optional: check Scheduled Tasks for Sysmon and Security Event collectors and generate normal process events only. No Kali, vulnerable targets or exploitation is required.

## Troubleshooting
422: check asset ID, max evidence (2-200) and minutes (5-240). 404: ensure router is loaded. Empty result: window lacks detections or IOC matches; inspect P4 findings and P8 matches. 500: check FastAPI logs and migration current. Never reset the database to repair P9. Correlation is manual and does not automatically produce P6 incidents.
