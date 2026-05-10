# Research Team — Phase 6 (Standup UI) Plan

**Goal:** Pressing "Run standup" on a subject orchestrates Editor → Critic → Contrarian → Question-Generator in sequence, each writing an artifact of the appropriate kind. The subject detail page reorganizes into the design's three zones — briefing, agent cards, roundtable — and the user can post their own roundtable replies and broadcast instructions from the page.

**Architecture:** A `services/standup.py` orchestrator runs the four standup agents serially (so each can react to the previous). `execution.run_agent_once` accepts a `kind` parameter and an optional context-prefix so each call produces the right artifact type with a tailored instruction. The artifacts route already supports filter; we add a comma-separated `kind` param. A new `POST /subjects/{id}/artifacts` lets the user create instruction / roundtable_post artifacts. Frontend re-shapes the subject page into briefing/agents/roundtable.

**Tech additions:** none.

## File structure

```
backend/
  app/services/execution.py      MOD (kind param + standup-context support)
  app/services/standup.py        NEW (orchestrator)
  app/routes/standup.py          NEW (POST /subjects/{id}/standup)
  app/routes/artifacts.py        MOD (kind filter on GET; POST for user)
  app/main.py                    MOD (register standup router)
  tests/test_standup_service.py  NEW
  tests/test_standup_route.py    NEW

frontend/
  components/briefing-card.tsx          NEW
  components/roundtable.tsx             NEW
  components/run-standup-button.tsx     NEW
  app/subject/page.tsx                  MOD (three-zone layout)
  lib/api.ts                            (no change — generic enough)
```

## Tasks

### Task 1 — execution: kind + extra system context
Modify `run_agent_once` signature:

```python
async def run_agent_once(
    session, *, agent_id, user_id,
    user_instruction: str | None = None,
    artifact_kind: str = "note",
    extra_system_context: str | None = None,
    chat_fn: ChatFn | None = None,
) -> Artifact: ...
```

`extra_system_context`, when provided, is added as an additional system message between the agent's system prompt and the memory block. `artifact_kind` becomes the new artifact's `kind`.

Update Phase 3 callers (just the `/agents/{id}/execute` route; default `artifact_kind="note"`).

### Task 2 — standup service
`services/standup.py::run_standup(session, *, subject_id, user_id, chat_fn=None) -> list[Artifact]`:

Steps:
1. Fetch Editor, Critic, Contrarian, Question-Generator agents on the subject (skip any that aren't present)
2. Build a context blob from the most recent 30 artifacts on the subject and the most recent 10 corpus_items with summaries — this is the "standup packet" each agent reads
3. Editor: kind="briefing", instruction = "Write the morning briefing (~300 words). Lead with what's new, what disagrees, and what blocks the user's questions. Never info-dump."
4. Critic: kind="critique", extra_system_context includes the briefing text just written; instruction = "Read the briefing and the recent expert reactions. Surface 1-2 weak claims, methodological gaps, or unstated assumptions. Be specific."
5. Contrarian: kind="roundtable_post", extra context = briefing + critique; instruction = "Argue the strongest case against the briefing's central claim. ≤200 words. Lead with the counter-thesis."
6. Question-Generator: kind="open_question", extra context = briefing; instruction = "Propose 1–3 specific questions worth pulling next. Each: a one-sentence question, why it matters, what kind of source would answer it."
7. Return the list of artifacts (briefing first)

Each agent that's over budget is skipped (logged into the standup result via metadata).

### Task 3 — Standup route
`POST /api/v1/subjects/{id}/standup` — auth + ownership check; calls `run_standup`; returns list[ArtifactRead]. Errors:
- 404 if subject not found
- 502 on OpenRouter failure mid-standup (with whatever was produced so far if useful — keep it simple: surface the failure)

### Task 4 — Artifact extensions
- `GET /subjects/{id}/artifacts?kind=briefing,critique` — comma-separated whitelist
- `POST /subjects/{id}/artifacts` body `{ "kind": "instruction"|"roundtable_post", "body_md": str, "addressed_to": agent_id|null, "parent_id": artifact_id|null, "title": str }` — author_type="user", author_id=null

Tests cover both.

### Task 5 — Frontend: BriefingCard
Reads `/subjects/{id}/artifacts?kind=briefing&limit=1`. If empty, render placeholder "No briefing yet — run standup". If present, render with body_md as plain text + timestamp + Editor name.

### Task 6 — Frontend: Roundtable
Filter artifacts to kinds in `{critique, roundtable_post, open_question, instruction}`. Group by parent_id (top-level threads have parent=null; replies are children). Render each thread with replies indented. Include a "Reply" button per thread that opens a small inline form posting back via `POST /subjects/{id}/artifacts`.

### Task 7 — Frontend: RunStandupButton
Button at top of subject page near the title. POSTs `/subjects/{id}/standup`, shows pending state, then refreshes the parent.

### Task 8 — Subject page layout
Re-shape `/subject/?id=N` into:
- Header with title, brief, library link, and `<RunStandupButton>`
- `<BriefingCard>` directly below
- `<AgentGrid>` (existing)
- `<Roundtable>` at the bottom

Keep the existing artifact list as a fallback "All artifacts" toggle for debugging.

## Acceptance

- Backend tests pass for standup orchestrator + new artifact endpoints
- A real Run-Standup pass (with valid OPENROUTER_API_KEY) produces 4 artifacts of the expected kinds
- Subject page shows briefing → agents → roundtable
- Phase 6 merged
