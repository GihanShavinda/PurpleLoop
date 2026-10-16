# P19 — Security Assurance / No Docker

## Scope
The P19 package is a baseline source update built from the P18 release package. Review differences with your locally customized files before copying replacements. It adds a conservative HTTP header middleware, admin-only read-only posture summary, static security tests, and a standalone Angular Security Assurance page. It does **not** claim to establish production security compliance or test every previous module. No migration is necessary; Alembic remains `0016_p17_vmware_range`.

## Installation — Windows PowerShell
Run from `F:\My_Projects\PurpleLoop\PurpleLoop` after stopping FastAPI/Angular; PostgreSQL remains on:

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
git status
Copy-Item backend/main.py backend/main.py.pre-p19 -Force
Copy-Item frontend/src/main.ts frontend/src/main.ts.pre-p19 -Force
Expand-Archive "$env:USERPROFILE\Downloads\purpleforge-ai-p19-no-docker.zip" .\p19-staging -Force
git diff --no-index backend/main.py p19-staging/backend/main.py
git diff --no-index frontend/src/main.ts p19-staging/frontend/src/main.ts
# Inspect changes and merge any local customizations BEFORE overwriting.
Copy-Item p19-staging/backend/main.py backend/main.py -Force
Copy-Item p19-staging/backend/assurance backend/assurance -Recurse -Force
Copy-Item p19-staging/frontend/src/main.ts frontend/src/main.ts -Force
Copy-Item p19-staging/frontend/src/p19-assurance.component.ts frontend/src/ -Force
Copy-Item p19-staging/tests/test_p19_assurance.py tests/ -Force
Copy-Item p19-staging/tests/test_p19_integration_static.py tests/ -Force
New-Item -ItemType Directory scripts -Force | Out-Null
Copy-Item p19-staging/scripts/p19_verify.ps1 scripts/ -Force
```

Run checks:
```powershell
.\backend\.venv\Scripts\python.exe -c 'import backend.main; print("P19 imported")'
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests\test_p19_assurance.py tests\test_p19_integration_static.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests -v
cd frontend
npm run build
```

Start from project root in two PowerShell terminals:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
```powershell
cd frontend
npm start
```

Visit `http://localhost:4200`, sign in as Administrator, and open **Security Assurance**. The dashboard loads only once per entry and then on click.

## Manual security validation
1. Viewer must receive HTTP 403 for `GET /assurance/posture`; administrator receives HTTP 200.
2. Unauthenticated call must receive 401 or 403, not data.
3. Validate that JSON API responses have `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`.
4. Verify HTTPS reverse proxy separately: TLS certificate, HSTS on HTTPS, proxy trust boundaries, CORS restrictions, and no HTTP plain-text exposure outside loopback.
5. Exercise P11 proposer/approver separation with two distinct test accounts.
6. Run full pytest and Angular build; investigate failures before committing.
7. Do not stage `.env`, keys, certificate private keys, telemetry exports, or database dumps.

## Security limitations
The configuration endpoint intentionally tests a small known subset. It cannot validate password hashing, token lifetime, input authorization across all P1–P18 routes, rate limiting, account-lockout, database least privilege, or security of a reverse proxy. Its passing state is not a penetration-test result. For deployment, perform independent OWASP ASVS tests and manual threat modeling.
