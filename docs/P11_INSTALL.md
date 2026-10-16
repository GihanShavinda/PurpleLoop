# PurpleForge P11 — No-Docker SOAR dry-run installation

**Do not use this package as an automated response agent.** The three fixed playbooks only generate written plans; all response actions remain manual outside this release.

1. Stop FastAPI and Angular. Leave PostgreSQL running. From the project root (`F:\My_Projects\PurpleLoop\PurpleLoop`), run `git status` and back up the database with `pg_dump`.
2. Unzip this package into a **staging** folder. Review changes to `backend/main.py`, `backend/models.py`, and `frontend/src/main.ts` before replacing those three files. The package is based on the published P10 ZIP, not direct access to your modified local project.
3. Copy package paths to the equivalent paths under your project. Do not overwrite any other files.
4. Run `.\backend\.venv\Scripts\python.exe -c "import backend.models; import backend.main; print('imports OK')"` after correcting running this command from your project root.
5. `.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current` (expect P10 migration).
6. `.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head` (expect `0010_p11_soar`).
7. `.\backend\.venv\Scripts\python.exe -m pytest tests\test_p11_soar.py -v` and `.\backend\.venv\Scripts\python.exe -m pytest tests -v`.
8. Run FastAPI without reload and `npm run build` before `npm start` in Angular.
9. Open SOAR. Create an advisory proposal linked to an existing P6 incident or P9 correlation case. **Sign in as a distinct authorized approver** to approve it; self-approval is blocked. Run simulation and inspect the audit history.
10. Do not turn on VMware guests for this release. No Linux agent or Windows task changes required.

If the Angular screen cannot populate incident choices, inspect your existing P6 route at `http://127.0.0.1:8000/docs`; adjust only the `'/incidents'` request in the P11 component if your P6 endpoint differs.
