# Research Team — Phase 5 (Cycle Engine) Plan

**Goal:** Each agent's `cycle` setting actually drives runs. Hourly agents run on the hour, "every_4h" every 4 hours, "daily" at 03:00 UTC overnight (off-peak for the user). At 00:00 UTC, every agent's `spent_today_usd` is zeroed. Archived subjects' agents are removed from the schedule. Setting an agent to `off` removes its job; switching back to a cron cycle re-adds it.

**Architecture:** `apscheduler` AsyncIOScheduler running in-process inside the FastAPI lifespan. A single `services/scheduler.py` module owns the scheduler instance and exposes `start`, `shutdown`, `schedule_agent`, `unschedule_agent`, and `reload_all`. On startup the scheduler is started and `reload_all` syncs jobs against current DB state. Hooks in `agents` and `subjects` services keep the schedule in sync.

**Tech additions:** `apscheduler==3.10.4`.

## File structure

```
backend/
  pyproject.toml                         MOD (add apscheduler)
  app/services/scheduler.py              NEW
  app/services/agents.py                 MOD (call schedule_agent on settings change)
  app/services/subjects.py               MOD (unschedule agents on archive)
  app/services/execution.py              MOD (reset_daily_budget extracted as helper)
  app/main.py                            MOD (lifespan starts/stops scheduler)
  tests/test_scheduler.py                NEW
```

## Tasks

### Task 1 — Add APScheduler dep and config defaults
- pyproject.toml: `apscheduler==3.10.4`
- config.py: `daily_run_hour_utc: int = 3` (when "daily" agents run); other cycles aren't user-configurable

### Task 2 — Scheduler service
`services/scheduler.py`:
- Module-global `_scheduler: AsyncIOScheduler | None = None` and `_session_factory_provider: Callable[[], AsyncSession]`
- `start(session_factory_provider)` — initialize scheduler if not already; add the daily-reset job (cron 0 0); call `reload_all()`; start scheduler
- `shutdown()` — stop scheduler
- `_cron_for_cycle(cycle) -> CronTrigger | None` — maps cycle to a CronTrigger; off / on_demand → None
- `schedule_agent(agent)` — replaces job id `f"agent-{agent.id}"`; if cycle has no trigger, removes any existing job
- `unschedule_agent(agent_id)` — remove by id (silent if missing)
- `reload_all()` — fetch all agents whose subject is active and that have cron-eligible cycles; (re)register
- The job function `_tick(agent_id)` opens a session via the provider, fetches agent + subject, refuses if subject archived, calls `run_agent_once(session, agent_id=agent_id, user_id=subject.user_id, user_instruction=None)`. Errors are logged and swallowed (the next tick will retry).
- The daily-reset job zeros `spent_today_usd` for all agents.

### Task 3 — Hook scheduler into services
- `agents.update_agent_settings`: after committing, call `schedule_agent(agent)` (it will replace the job to match the new cycle/budget).
- `agents.spawn_default_team`: after each create, call `schedule_agent`.
- `subjects.archive_subject`: list agents on the subject, call `unschedule_agent(a.id)` for each.

These calls must be safe when the scheduler isn't started (during tests). The scheduler module checks `_scheduler is None` and no-ops in that case.

### Task 4 — Lifespan integration
In `app/main.py` lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_admin_user(...)
    await scheduler.start(lambda: SessionLocal())
    try:
        yield
    finally:
        await scheduler.shutdown()
```

### Task 5 — Tests
Tests do not actually start the scheduler (it would fight with the asyncio loop). Instead:

- `test_scheduler.py::test_cron_for_cycle` — pure mapping test (no scheduler instance)
- `test_scheduler.py::test_schedule_agent_no_op_without_start` — call schedule_agent before start, verify no exception
- `test_scheduler.py::test_reload_all_picks_active_agents_only` — spin up scheduler with MemoryJobStore in a controlled way, archive a subject, call reload_all, assert only active-subject agents have jobs

(Optional Phase 5+ improvement: persistence of jobs across restarts via a SQLAlchemy job store. Skipped here — restart re-syncs from DB anyway via reload_all.)

### Task 6 — Smoke verification
With docker compose up and an OpenRouter key:
1. Set Librarian cycle to `hourly`
2. Wait until next minute=0 (or for a faster test, edit `_cron_for_cycle` locally)
3. Confirm artifact appears

For now we verify only that the scheduler starts cleanly inside the container (no startup error) and `/api/v1/health` still responds. Real cron timing is verified manually by the user.

## Acceptance

- Backend tests pass (no scheduler instance leaked)
- Container starts; lifespan runs without error
- Setting cycle to `off` removes the agent from the schedule (no job by id)
- Archiving a subject removes all its agents from the schedule
- Phase 5 merged
