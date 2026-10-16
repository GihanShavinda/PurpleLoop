# P1 manual verification

All commands below run in PowerShell from repository root. Complete `.env` and run setup/migration/seed first.

```powershell
.\scripts\startup\check-services.ps1
Invoke-RestMethod http://127.0.0.1:8000/health
Start-Process http://127.0.0.1:8000/docs
```

1. Register a new account (`POST /auth/register`). Verify it has `Viewer` permissions only.
2. Log in as admin (`POST /auth/login`); copy access token into Swagger Authorize.
3. Create lab (`POST /labs`) and an asset (`POST /assets`).
4. Read, filter, update and delete the asset; verify results and the audit log SQL rows.
5. Verify Viewer can read but cannot create labs or assets (403).
6. Refresh tokens once, then retry the old refresh token and confirm 401.
7. Logout using refresh token and verify it cannot be refreshed.
8. Admin calls `/health/services` to inspect PostgreSQL, Redis and Neo4j connectivity.
9. Open Angular `http://localhost:4200`, sign in, and view lab/asset cards.
10. Run unit/integration tests and verify 5 service prerequisites independently.

Useful SQL:
```sql
SELECT id,email,role_id FROM users;
SELECT id,hostname,lab_id FROM assets;
SELECT actor_id,action,resource,created_at FROM audit_logs ORDER BY created_at DESC;
```

P1 does NOT ingest telemetry, run scans, execute exploits or ingest PCAPs.
