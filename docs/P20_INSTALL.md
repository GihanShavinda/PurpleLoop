# P20 — Final Evaluation & Portfolio Release (No Docker)

## What is and is not implemented
This update adds an **administrator-only**, read-only database evidence snapshot, an Angular Final Evaluation page, evaluation logic unit tests, an offline verification script, and templates for manual VMware demonstrations. No automatic attack, firewall, VM power or guest actions. No new migration: Alembic remains `0016_p17_vmware_range`.

## Install carefully
1. Stop Angular and FastAPI; ensure P19 is committed and back up database and `backend/main.py` and `frontend/src/main.ts`.
2. Extract the archive into `p20-staging` from the repository root.
3. Diff your local `main.py` and `main.ts` against staging and merge any post-P19 changes.
4. Copy staging `backend/main.py` to `backend/main.py`, `frontend/src/main.ts` to `frontend/src/main.ts`, staging `backend/release` to `backend/release`, `frontend/src/p20-release.component.ts` to `frontend/src/`, `tests/test_p20_evaluation.py` to `tests/`, and `scripts/p20_verify.ps1` to `scripts/`.
5. Run `./scripts/p20_verify.ps1` from PowerShell. It runs all available tests and the Angular build; reports are stored under `p20-local-evidence/` (do not commit raw artifacts).
6. Run FastAPI: `./backend/.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
7. Run Angular from `frontend`: `npm start` and open `http://localhost:4200`.
8. Login as Administrator and open **Final Evaluation**. Viewer / unauthenticated access to `/release/snapshot` must be denied (403 / 401).
9. Capture screenshots and fill in the evidence report template *using real results only*.

## Security and resource safeguards
- Single on-demand endpoint, no polling; 12-second Angular timeout.
- P18 bounded metric aggregation reused; no raw logs, certificates, tokens, network interfaces, or source-code secrets exported.
- No claims about malware, attack chain, full ATT&CK coverage or production security certification.
- Rehearsal, P13 journal test, P14 measured detection, P11 SOAR approval and rollback, P17 readiness, P19 Viewer 403 must be verified by a human.
- Save evidence files outside the public Git repository, or redact IPs/usernames and audit for private data before publishing.

## Suggested demonstration order
P3 Ubuntu collection -> P13 unique-marker verified -> P4 rule match -> P14 exact-evidence detection -> P6 case / P9 correlation -> P10/P16 analyst review -> P11 separate-person approval -> P12 simulated rollback -> P15 statistical outlier -> P17 reported readiness -> P18 dashboard -> P19 authorization tests -> P20 report.

## Rollback
Before database-independent frontend/backend changes, restore your backup copies of `backend/main.py` and `frontend/src/main.ts`, remove only new P20 modules, rerun unit tests. No schema downgrade is needed.
