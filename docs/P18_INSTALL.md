# PurpleForge P18 - Read-only Operations Dashboard (No Docker)

## Source changes
- Updated: backend/main.py, frontend/src/main.ts
- New: backend/operations/__init__.py, backend/operations/metrics.py, backend/operations/routes.py, frontend/src/p18-operations.component.ts, tests/test_p18_metrics.py
- No Alembic migration. All database access is read-only.

## Commands (Windows PowerShell, from F:\My_Projects\PurpleLoop\PurpleLoop)
1. Stop Angular and FastAPI. Commit P17 and back up backend/main.py and frontend/src/main.ts.
2. Extract this ZIP to p18-staging; compare updated files with current project.
3. Copy p18-staging/backend/main.py to backend/main.py
4. Copy p18-staging/backend/operations directory to backend/operations
5. Copy p18-staging/frontend/src/main.ts to frontend/src/main.ts
6. Copy p18-staging/frontend/src/p18-operations.component.ts to frontend/src
7. Copy p18-staging/tests/test_p18_metrics.py to tests
8. .\backend\.venv\Scripts\python.exe -c "import backend.main; print('P18 imports OK')"
9. .\backend\.venv\Scripts\python.exe -m pytest tests\test_p18_metrics.py -v
10. .\backend\.venv\Scripts\python.exe -m pytest tests -v
11. In project root: .\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
12. In frontend folder: npm run build ; npm start
13. Open http://localhost:4200 -> Operations Center. Compare figures with source pages.

## Notes
- No VM needs to be on. Existing database has historic P1-P17 data.
- Requests are manual, no polling. Summary uses indexed timestamps where available.
- No action execution, no attack orchestration, no snapshot operations.
- Telemetry status is a recent receipt, not proof of a functioning sensor in all conditions.
- P14 detection rate covers only expressly assessed runs.
