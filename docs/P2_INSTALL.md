# PurpleForge AI P2 — VMware-first Lab Management (No Docker)

## Apply to the existing working P1 checkout

1. **Back up your project** and commit your working P1 files.
2. Extract `purpleforge-ai-p2-update.zip` to a temporary folder.
3. Copy the extracted `backend`, `frontend`, `docs`, and `tests` files into your existing project root, merging folders and replacing only same-named files. **Do not delete existing folders.**
4. Keep your existing root `.env` and PostgreSQL data. This overlay contains no secrets and no database reset.
5. No new database columns are required. Your `0001_initial` migration remains unchanged. Existing assets keep their original `asset_type` values; edit records to use the new VMware-first categories.

## PowerShell setup

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
# Existing backend environment at backend\.venv; adjust only if your location differs
.\backend\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini current
.\backend\.venv\Scripts\python.exe -m pytest tests -v
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open a second PowerShell terminal:

```powershell
cd 'F:\My_Projects\PurpleLoop\PurpleLoop\frontend'
npm install
npm run build
npm start
```

## P2 features

- Angular dashboard with dark purple/cyan styling, persistent sidebar and inventory metrics.
- Native lab creation/rename/edit/delete (Administrator or Purple Team Engineer).
- Native asset creation/edit/delete using existing P1 RBAC; asset fields include host name, IP, MAC, OS, VMware network, VM name, monitoring flag, criticality, environment.
- Client-side inventory filters across the first 200 assets. Backend supports query-based filtering (`search`, `lab_id`, `asset_type`, `criticality`) with offset and limit.
- Topology **groups assets by stored VMware network labels**. It does not discover physical network connectivity, traffic flows, power states, or host health.
- `GET /inventory/summary` provides database totals, not discovered live VM counts.
- `PATCH /labs/{lab_id}` updates lab name/description.

## Access behavior

- All authenticated roles can see inventory and topology.
- Administrator and Purple Team Engineer can manage labs and delete assets.
- Administrator, Purple Team Engineer and Detection Engineer can create/update assets.
- The Viewer and SOC Analyst cannot mutate assets or labs through this UI.
- The API checks the permissions independently of the frontend.

## Verification

1. Sign in with your seeded administrator account.
2. Create a lab in **Labs**. Confirm dashboard count increases.
3. In **Inventory**, add a Kali VM with a valid IPv4 address, type `Attacker`, and network `VMnet2`.
4. Add an Ubuntu VM in the same lab with type `Monitoring Sensor` and network `VMnet3`.
5. Filter by lab and type, edit monitoring configuration, and open detail view.
6. Open **Network Topology** and verify each VM is grouped under its saved VMnet network.
7. Verify the same assets appear in Swagger at `http://127.0.0.1:8000/docs`.
8. Create a Viewer account and verify the frontend does not expose mutation controls; validate backend returns 403 for prohibited API mutations.

## Troubleshooting

- HTTP 401: sign in again; P2 does not persist access tokens across reloads.
- HTTP 422: inspect Network > Response for schema validation details (including IP / MAC validation).
- HTTP 409 deleting lab: delete its registered assets first.
- CORS: `.env` should contain `FRONTEND_URL=http://localhost:4200` and `CORS_ORIGINS=http://localhost:4200`.
- Postgres: your local environment previously used port `5433`; retain the working `.env` database URL.
- No Docker, Docker Compose, Kubernetes, Podman or container services are required.

## Known boundaries

- This P2 UI is focused on the first 200 assets; use API pagination for larger datasets.
- No background token refresh, VMware hypervisor API integration, live sensor checks, topology edges, automated attack execution, or real-time telemetry in P2.
- Redis and Neo4j are untouched by this overlay.
- No example secrets are supplied; keep your real credentials out of source control.
