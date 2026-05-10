# Research Team

Personal multi-agent research environment. See `docs/superpowers/specs/2026-05-10-research-team-design.md` for the full design.

## Local development

```bash
cp .env.example .env
docker-compose up --build
```

Backend: http://localhost:8000
Frontend (dev): http://localhost:3000
Frontend (prod build, served by backend): http://localhost:8000

## Phase status

- **Phase 1 (current):** Foundations — auth, subjects CRUD, deployable skeleton.
- **Phase 2+:** see `docs/superpowers/plans/`.

## Deploying to Railway

1. Create a new Railway project from this repo.
2. Add the **Postgres** plugin. Railway will provision `DATABASE_URL` for you.
3. **Important:** the Railway-provided `DATABASE_URL` uses the `postgres://` scheme.
   Override it for the web service to start with `postgresql+asyncpg://` so SQLAlchemy uses the async driver. Example:
   ```
   DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
   ```
4. Set the remaining env vars: `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
5. Deploy. Migrations run on container start; admin user is created on first boot.
