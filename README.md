# PurpleForge AI — P1 No-Docker Platform Foundation

FastAPI, Angular 18, native PostgreSQL, Redis, Neo4j and VMware-compatible lab inventory. No container runtimes. **P1 only**; no attack execution or telemetry ingestion.

## Prerequisites
- Windows 10/11 and PowerShell
- Python **3.12** (`py -3.12 --version`), Node.js compatible with Angular 18, npm
- PostgreSQL installed as a native service
- Redis running as a native service or on a dedicated VMware Linux guest
- Neo4j Community Edition as a native service or on VMware guest

## Setup
In PowerShell from this repository root:

```powershell
Copy-Item .env.example .env
notepad .env
.\scripts\setup\setup-backend.ps1
```

Set `DATABASE_URL`, `REDIS_URL`, `NEO4J_*`, `JWT_SECRET` (cryptographically random >=32 characters), `ADMIN_EMAIL`, `ADMIN_PASSWORD` (>=12 characters) and `CORS_ORIGINS`. Use the actual host/VM IP and ports. Do not commit `.env`.

Generate a JWT secret locally:

```powershell
$bytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

Create PostgreSQL role/database using `psql` connected as database superuser (the `psql` binary may require the full PostgreSQL installation path):

```powershell
psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE ROLE purpleforge_user LOGIN PASSWORD 'REPLACE_WITH_STRONG_DB_PASSWORD';"
psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE purpleforge OWNER purpleforge_user;"
```

Use the same DB password in `.env` (URL encode reserved characters). On installations using port 5433, update `.env` accordingly. `psql` may prompt for your `postgres` password.

```powershell
.\scripts\database\migrate.ps1
.\scripts\database\seed.ps1
.\scripts\startup\check-services.ps1
.\scripts\startup\start-backend.ps1
```

In a second terminal:

```powershell
.\scripts\startup\start-frontend.ps1
```

Endpoints: API `http://127.0.0.1:8000`, Swagger `http://127.0.0.1:8000/docs`, Angular `http://localhost:4200`.

## Tests
```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

External service integration checks require PostgreSQL/Redis/Neo4j running and correct `.env`. They do not require containers.

## Key API routes
- `GET /health` (liveness)
- `GET /health/services` (admin; service connectivity)
- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- `GET /users`, `GET /users/{id}`, `PATCH /users/{id}/role`
- `GET /labs`, `POST /labs`, `GET /labs/{id}`, `DELETE /labs/{id}`
- `GET /assets`, `POST /assets`, `GET /assets/{id}`, `PATCH /assets/{id}`, `DELETE /assets/{id}`

Roles: Administrator, Purple Team Engineer, SOC Analyst, Detection Engineer, Viewer. Public registration produces Viewer accounts; administrator is seeded locally. JWT access tokens are short lived; refresh tokens are hashed in PostgreSQL and single-use. Frontend stores tokens in application memory only (lost on page reload). `HTTPBearer` Swagger authorization supports access tokens.

## Test scope & future improvements
The API provides core inventory and role boundaries, but P1 is **not production hardened**: implement login throttling, account recovery, structured audit coverage, stricter schema validation for role updates, improved token transport, fine-grained lab tenancy, complete lifecycle CRUD for interfaces and telemetry sources, and managed secrets before production. Redis and Neo4j are connectivity placeholders, not yet used for telemetry or graph workloads.

See `docs/P1_VERIFICATION.md` for manual workflow.
