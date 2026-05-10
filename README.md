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
