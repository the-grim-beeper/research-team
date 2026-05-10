# Research Team — Phase 3 (OpenRouter Execution + Artifacts) Plan

**Goal:** A user can hit "Run now" on any agent, optionally pass a one-shot instruction, and the agent makes a real LLM call via OpenRouter with its system prompt + recent private memory, returns the output, and the output is persisted as an `Artifact` on the subject. The agent's spent_today_usd is updated. A second small LLM call extracts one memory_entry summarizing what the agent learned, persisting cognitive state for the next run.

**Architecture:** Pure backend execution loop in `services/execution.py`. OpenRouter chat-completions client in `services/openrouter.py` (httpx async). `services/memory.py` handles read-recent and append-entry. `services/artifacts.py` handles create/list. Token-based cost estimation via a static pricing table — accurate enough for v1 budgets. Daily budget reset is lazy: each run checks `last_run_at`'s date and zeros `spent_today_usd` if it's yesterday or older. No cron yet (Phase 5).

**Tech additions:** `httpx` (already a transitive dep of FastAPI's testclient — add explicit), OpenRouter API key (env var).

## File structure

```
backend/app/
  config.py                              MOD (add openrouter_api_key, base_url)
  pricing.py                             NEW (cost-per-million-tokens table)
  services/openrouter.py                 NEW (chat() async client)
  services/memory.py                     NEW (recent_entries, append_entry)
  services/artifacts.py                  NEW (create, list_for_subject, get)
  services/execution.py                  NEW (run_agent_once)
  schemas/artifact.py                    NEW
  schemas/execution.py                   NEW (ExecuteNowRequest, ExecuteNowResponse)
  routes/artifacts.py                    NEW
  routes/execution.py                    NEW (POST /agents/{id}/execute)
  main.py                                MOD (register routers, explicit httpx dep)
backend/tests/
  test_openrouter_client.py              NEW (mocked transport)
  test_memory_service.py                 NEW
  test_artifacts_service.py              NEW
  test_execution_service.py              NEW (mocks openrouter.chat)
  test_execution_route.py                NEW

frontend/
  lib/types.ts                           MOD (Artifact, ExecuteNowResponse)
  components/agent-settings-panel.tsx    MOD (Run-now button + result display)
  components/artifact-list.tsx           NEW (basic recent-artifacts list)
  app/subject/page.tsx                   MOD (mount ArtifactList below AgentGrid)
```

## Tasks

### Task 1 — Pricing table + cost estimation
`app/pricing.py` exports `PRICING: dict[model_slug, {"input_per_m": float, "output_per_m": float}]` with entries for the 6 default models (Haiku 4.5, Sonnet 4.6, Opus 4.7, GPT-4o, GPT-4o-mini, Gemini 2.5 Flash). Function `estimate_cost(model, prompt_tokens, completion_tokens) -> Decimal`. Unknown model falls back to a flat $5/M defensively.

### Task 2 — OpenRouter client
`services/openrouter.py::chat(messages, model, max_tokens, api_key, base_url) -> ChatResult` where ChatResult has `text: str, prompt_tokens: int, completion_tokens: int, raw: dict`. Uses httpx AsyncClient, posts to `{base_url}/chat/completions`, includes `HTTP-Referer` and `X-Title` headers. Tests use httpx MockTransport.

### Task 3 — Memory service
`services/memory.py`:
- `recent_entries(session, agent_id, limit=20) -> list[MemoryEntry]` — most recent first
- `append_entry(session, agent_id, kind, content, importance=3) -> MemoryEntry`
Tests trivial.

### Task 4 — Artifact service + routes
`services/artifacts.py`:
- `create(session, *, subject_id, kind, author_type, author_id, body_md, title="", parent_id=None, addressed_to=None, metadata=None) -> Artifact`
- `list_for_subject(session, subject_id, limit=50) -> list[Artifact]` — newest first
- `get(session, artifact_id) -> Artifact | None`

`routes/artifacts.py`:
- `GET /api/v1/subjects/{subject_id}/artifacts` — list (auth-gated, ownership-checked via subject)

Schema `ArtifactRead` mirrors fields. Tests cover ownership and shape.

### Task 5 — Execution service
`services/execution.py::run_agent_once(session, *, agent_id, user_id, user_instruction: str | None) -> Artifact`:

1. Owner-check agent (reuse get_agent service)
2. Lazy budget reset: if `last_run_at` is None or its date < today (UTC), set `spent_today_usd = 0`
3. If `spent_today_usd >= daily_budget_usd`: raise `BudgetExceeded`
4. Read agent.system_prompt + recent_entries → assemble messages:
   - system: agent.system_prompt
   - system: "Your private memory (most recent first):\n" + concatenated recent entries (or "(no prior memory)")
   - user: user_instruction or "Run your normal cycle responsibilities. Produce one short note (≤400 words) on the most useful thing you can do right now given your role and prior memory."
5. Call openrouter.chat(...). Compute cost, increment spent_today_usd, set last_run_at = now
6. Persist Artifact (kind="note", author_type="agent", author_id=agent.id, body_md=text)
7. Append a memory_entry: do a tiny second call ("In ≤30 words, summarize the most important thing to remember from your last response: …") with cheap model (gpt-4o-mini fallback), append as kind="note" entry
8. Return the Artifact

Tests: mock openrouter.chat to return canned responses; assert artifact created, budget incremented, memory entry appended, BudgetExceeded raised when capped.

### Task 6 — Execute-now route
`routes/execution.py`:
- `POST /api/v1/agents/{agent_id}/execute` body `{ "instruction": str | null }` → returns the new ArtifactRead

Tests cover success path and 402 on budget exceeded.

### Task 7 — Frontend wiring
- `lib/types.ts` adds `Artifact` interface
- `agent-settings-panel.tsx` gains a "Run now" section above the form: textarea for instruction, "Run now" button, displays the returned artifact body in a scrollable preview
- `artifact-list.tsx` renders recent artifacts as cards (timestamp, author display name, body excerpt) — NEW component
- `app/subject/page.tsx` adds an "Artifacts" section below the agent grid that polls `/subjects/{id}/artifacts` and renders `<ArtifactList>`

### Task 8 — Smoke test
- Set `OPENROUTER_API_KEY` env var in `.env`
- Bring up docker compose
- Login, create subject, list agents, hit `POST /agents/{id}/execute` with `instruction="Hello, please introduce your role and how you'd contribute to a research subject called 'AI governance'."`
- Verify response has body_md text and ≤2 memory_entries appended

## Acceptance

- All backend tests pass (mocked OpenRouter)
- One real call against OpenRouter completes end-to-end (manual, requires API key)
- Budget tracking visible in agent settings panel
- An artifact appears in the subject's artifact list

## Key constants

- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1` (configurable)
- `MAX_TOKENS_DEFAULT=1000` per call (override per agent later)
- `MEMORY_RECENT_LIMIT=20`
