# Research Team — Phase 2 (Domain Core) Plan

**Goal:** When a user creates a Subject, a default cross-disciplinary team of 8 agents is auto-spawned. The user can navigate to a subject detail page (`/subject/?id=N`), see all agents grouped by category in a grid, and click any agent to view/edit its settings (model, cycle, budget cap, system-prompt addendum). Memory and Artifact tables exist with pgvector ready, awaiting Phase 3 to populate.

**Architecture:** Adds five domain models — Role (template), Agent (instance), Artifact (schema only), AgentMemoryVector (pgvector), MemoryEntry (structured). One Alembic migration (0002) creates and seeds. Service layer extends with roles, agents, default-team spawner hooked into subject creation. Frontend gains a subject detail page using query-string routing (compatible with static export) plus an agent grid + settings side-panel.

## File structure

```
backend/
  alembic/versions/0002_roles_agents_memory_artifacts.py    NEW
  app/models/role.py, agent.py, artifact.py, memory.py      NEW
  app/models/__init__.py                                    MOD
  app/schemas/role.py, agent.py                             NEW
  app/services/roles.py, agents.py                          NEW
  app/services/subjects.py                                  MOD (spawn default team)
  app/routes/roles.py, agents.py                            NEW
  app/routes/subjects.py                                    MOD (add GET /{id})
  app/main.py                                               MOD (register routers)
  tests/test_roles_service.py, test_agents_service.py,
  tests/test_subject_routes.py (extend), tests/test_agent_routes.py  NEW/MOD

frontend/
  lib/types.ts                                              MOD (add Role, Agent)
  lib/models.ts                                             NEW (model dropdown options)
  app/subject/page.tsx                                      NEW (detail view)
  components/subject-list.tsx                               MOD (links)
  components/agent-grid.tsx, agent-card.tsx, agent-settings-panel.tsx  NEW
```

## Default role seeds

Seed 8 rows into `roles` in the migration. System prompts kept tight (~80–120 words each); user can edit per-agent later.

| slug | category | tier | cycle |
|---|---|---|---|
| librarian | admin | cheap | daily |
| editor | admin | premium | on_demand |
| critic | admin | premium | on_demand |
| contrarian | admin | premium | on_demand |
| question_generator | admin | mid | on_demand |
| empiricist | expert | mid | daily |
| theorist | expert | mid | daily |
| historian | expert | mid | daily |

## Tasks

### Task 1 — Migration 0002
Create migration adding `roles`, `agents`, `artifacts`, `memory_entries`, `agent_memory_vectors` tables. Use `pgvector.sqlalchemy.Vector(1536)` for embeddings. Add HNSW index on `agent_memory_vectors.embedding`. Seed 8 default roles with `op.bulk_insert`. FK cascade on agent→subject and agent→agent_memory_vectors.

### Task 2 — Models
SQLAlchemy mapped declarations matching the migration: `Role`, `Agent`, `Artifact`, `MemoryEntry`, `AgentMemoryVector`. Register in `models/__init__.py`.

### Task 3 — Roles service + tests
`list_roles(session)`, `get_role_by_slug(session, slug)`. Trivial.

### Task 4 — Agents service + tests
- `list_for_subject(session, subject_id) -> list[Agent]`
- `get_agent(session, agent_id, user_id) -> Agent` — raises LookupError if not found or subject not owned by user
- `update_agent_settings(session, agent_id, user_id, *, model=None, cycle=None, daily_budget_usd=None, system_prompt_addendum=None) -> Agent` — validates cycle in `{off,on_demand,hourly,every_4h,daily}`, budget ≥ 0; addendum is appended to role's `default_system_prompt` when stored as effective `system_prompt`
- `spawn_default_team(session, subject_id) -> list[Agent]` — for each role, create an Agent with role's defaults; `display_name = role.display_name`; `system_prompt = role.default_system_prompt` (no addendum yet)

Tests: spawn produces 8 agents in correct order; update validates invalid cycle; ownership check rejects mismatched subject.

### Task 5 — Hook spawn into subject creation
`services/subjects.py::create_subject` calls `spawn_default_team(session, subject.id)` after the subject is committed. Test that creating a subject yields 8 agents.

### Task 6 — Backend routes
- `GET /api/v1/roles` — list roles
- `GET /api/v1/subjects/{subject_id}` — single subject (auth-gated)
- `GET /api/v1/subjects/{subject_id}/agents` — list agents on subject
- `GET /api/v1/agents/{agent_id}` — single agent
- `PATCH /api/v1/agents/{agent_id}` — partial update of model/cycle/budget/addendum

Schemas in `schemas/agent.py`:
- `RoleEmbed { id, slug, display_name, category }`
- `AgentRead { id, subject_id, role: RoleEmbed, display_name, system_prompt, model, cycle, daily_budget_usd, spent_today_usd, last_run_at, created_at }`
- `AgentUpdate { model?, cycle?, daily_budget_usd?, system_prompt_addendum? }` (all optional)

Tests: route auth, shape correctness, PATCH applies fields and returns updated agent.

### Task 7 — Frontend types + model dropdown
`lib/types.ts` adds `Role` and `Agent`. `lib/models.ts` exports a static array of OpenRouter model identifiers with display names (Opus 4.7, Sonnet 4.6, Haiku 4.5, GPT-4o, GPT-4o-mini, Gemini 2.5 Flash). Phase 4+ may make this dynamic.

### Task 8 — Subject detail page
`frontend/app/subject/page.tsx` — Suspense-wrapped client component reading `?id=` via `useSearchParams`. Fetches subject + agents in parallel. Renders subject title, brief, and `<AgentGrid />`.

### Task 9 — Agent UI components
- `<AgentCard agent onOpen>` — name, role badge, model badge, cycle badge, last-run indicator
- `<AgentGrid agents />` — sections grouped by category (admin first, then expert), responsive 2/3-col layout, click opens panel
- `<AgentSettingsPanel agent open onClose onSaved>` — side drawer (right, fixed) with form: model select, cycle select, daily-budget number input, system-prompt-addendum textarea. Save → PATCH → refresh.

### Task 10 — Link subjects → detail
Each row title in `<SubjectList>` becomes a Next.js `<Link href="/subject/?id={id}">`.

### Task 11 — Smoke test
Bring up docker compose, login, create subject, GET `/subjects/{id}/agents` shows 8 rows. Manually open the detail page in the browser to verify rendering (this is a visual check; backend test covers the data).

## Acceptance

- All tests pass
- Creating a subject auto-spawns 8 agents
- Subject detail page lists them grouped by category
- Settings panel can update model/cycle/budget/addendum and the change persists
- Memory and Artifact tables exist (verified by `\dt`) with pgvector index on `agent_memory_vectors.embedding`
- Phase 2 merged to main
