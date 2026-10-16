# P1 implementation notes

- DB migrations must be run from repository root using the provided script.
- Service paths/IP addresses are adjustable via `.env`. PostgreSQL may already run on 5433 on the host; use its actual port.
- Configure Redis and Neo4j on dedicated Linux guests if not available on Windows. Restrict access to host-only lab network and firewall; do not expose their ports publicly.
- The Angular frontend only includes initial login and read-only lab/asset overview; use Swagger for create/update/delete in P1.
- Refresh-session persistence is PostgreSQL-based. Redis and Neo4j are intentionally optional for server start but `/health/services` reports outages.
- Database and authentication endpoint integration tests need a disposable Postgres test database and seeded roles. Included tests are preliminary unit/API smoke tests, not a full RBAC/CRUD regression suite.
- All lab attack tooling should remain in isolated, authorized VMware guests. No exploit automation exists in P1.

## Git
```
git init
git add .
git commit -m "feat(p1): bootstrap no-Docker PurpleForge AI platform foundation"
```
