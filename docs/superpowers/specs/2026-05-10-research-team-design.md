# Research Team — Design Spec

**Date:** 2026-05-10
**Status:** Approved (v1 scope)
**Working name:** `research-team` (rename welcome)

## 1. Purpose

A personal research environment where the user runs up to three parallel
research subjects, each staffed by a configurable team of LLM agents. Each
agent has its own role, model (via OpenRouter), cycle frequency, and **siloed
private memory** so the team preserves epistemic diversity over time. Agents
do continuous low-cost work overnight; the user logs in to a single-page
"standup" per subject — briefing, agent cards, roundtable — and leads the
work by issuing instructions to specific agents or the whole team.

Two design principles drive everything:

1. **Cognitive friction is a feature.** Agents form independent views from
   shared sources. The Critic and Contrarian make tensions explicit. The
   user is the synthesizer.
2. **Protect the user's attention.** No info dumps. The Editor's job is to
   filter overnight output into a short briefing the user can absorb in a
   few minutes.

## 2. Goals & non-goals

### Goals (v1)
- Run up to 3 active research subjects in parallel
- Per-agent configurable role, system prompt, model, cycle, daily $ cap
- Siloed per-agent memory (vector + structured) per subject
- Daily loop: cheap overnight ingestion + premium standup synthesis
- Single-page standup UI with briefing, agent cards, roundtable
- Per-agent instruction (persistent or one-shot) and broadcast
- Multi-source ingestion: upload, paste, web search, RSS, arXiv, YouTube
  captions, free-text user notes
- Evolving commented bibliography per subject
- Single-user, JWT-authenticated, deployed on Railway
- Hard $10/day global budget cap with per-agent sub-caps
- **API-first internals** so v2 can expose a public API with minimal rework

### Non-goals (v1)
- Multi-user / team features
- Mobile UI
- Podcast ASR (use show notes or YouTube version)
- Free-form inter-agent debate beyond Critic/Contrarian-mediated friction
- Semantic Scholar / PubMed connectors (covered by arXiv + web search)
- BibTeX / Zotero export
- Public API surface (designed for, not yet exposed)

## 3. Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Postgres 16, pgvector,
  APScheduler (in-process cron), Alembic (migrations), Pydantic v2
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, shadcn/ui, Zustand
  (client state), Server-Sent Events for streaming agent output
- **External:** OpenRouter (LLM routing), Tavily (web search), yt-dlp
  (YouTube captions), feedparser (RSS), Trafilatura (web parse), arXiv API
- **Auth:** JWT, single-user (admin email/password), bcrypt
- **Deployment:** Single Docker container on Railway (FYSA pattern). Postgres
  as Railway plugin.

## 4. Domain model

```
User (single, admin)
  └── Subject (≤3 active)
        ├── Agent  (instances of a Role bound to this Subject)
        │     └── Memory (private to this Agent + Subject)
        ├── Source (RSS feeds, channels, uploaded docs, etc.)
        ├── Corpus item (parsed source, dedup'd)
        ├── Artifact (briefing, note, synthesis, critique, instruction, ...)
        └── Bibliography entry (one per Corpus item, with running comments)
```

### Subject
- `id`, `title`, `brief` (the user's framing of the project), `status`
  (`active` / `archived`), `created_at`
- Constraint: at most 3 with `status='active'` per user

### Role (template, not per-subject)
- `id`, `slug`, `display_name`, `category` (`admin` | `expert`),
  `default_system_prompt`, `default_model`, `default_cycle`, `default_tier`
  (`cheap` | `mid` | `premium`), `tools` (allowed tool list, e.g. `web_search`,
  `fetch_url`, `read_corpus`)
- Seed data: Librarian, Editor, Critic, Contrarian, Question-Generator
  (admin); Empiricist, Theorist, Historian (expert)

### Agent (instance)
- `id`, `subject_id`, `role_id`, `display_name`, `system_prompt` (effective,
  may include user persistent-instruction addendum), `model` (OpenRouter
  model id), `cycle` (`off` | `on_demand` | `hourly` | `every_4h` | `daily`),
  `daily_budget_usd`, `spent_today_usd`, `last_run_at`, `created_at`
- `cycle` semantics: `off` = paused entirely (no cycles, no on-demand).
  `on_demand` = no cron cycles, but user can invoke via "Execute now".
  Others = run on the named schedule and can also be invoked on demand.
- Each Agent has its own private Memory namespace and task queue

### Memory (per agent, per subject)
- **Vector store:** `agent_memory_vectors` table — `agent_id`, `chunk_text`,
  `embedding` (pgvector), `source_artifact_id` (nullable), `created_at`,
  `metadata` (JSONB: kind, importance, etc.)
- **Structured store:** `memory_entries` table — explicit positions,
  open questions, mind-changes, hypothesis register; agent-writable via tool
  calls
- Memory is read by the agent at the start of each task (top-k vector recall
  + recent structured entries)

### Artifact
- Single table `artifacts` for all the things humans and agents produce
- `id`, `subject_id`, `kind` (`briefing` | `note` | `synthesis` | `critique`
  | `roundtable_post` | `instruction` | `source_summary` | `bibliography_comment`),
  `author_type` (`agent` | `user`), `author_id`, `parent_id` (threading),
  `addressed_to` (nullable agent_id, null = broadcast), `title`, `body_md`,
  `metadata` (JSONB), `created_at`
- All agents on the subject can read all artifacts (the public record)
- Agents **cannot** read each other's Memory tables — that's the silo

### Source / Corpus item
- `sources` — registered ingestion endpoints (RSS URL, YouTube channel,
  uploaded file id, etc.), with type and per-source config
- `corpus_items` — one row per parsed piece of content; `source_id`,
  `external_id` (for dedup), `title`, `authors`, `published_at`, `url`,
  `text` (full extracted), `summary` (Librarian-generated, ≤500 tokens),
  `tags` (JSONB; Librarian-routed to expert domains), `importance` (1–5,
  Librarian-assigned), `created_at`

### Bibliography entry
- One per `corpus_item` per `subject` (a single source can be referenced in
  multiple subjects with different commentary)
- `corpus_item_id`, `subject_id`, `comments` (Librarian-maintained markdown,
  appended-to over time), `linked_artifacts` (artifacts that cite this item)

## 5. Roles — template roster

### Admin roles (always present, one per subject)

- **Librarian** — owns ingestion across all sources. Pulls, parses, dedups,
  summarizes to ≤500-token brief, tags by domain, assigns an importance
  score (1–5) per item to support downstream filtering, and maintains the
  running commented bibliography. Cheap-tier model by default.
- **Editor** — produces the morning briefing. Reads overnight artifacts and
  surfaces what matters. Filters aggressively. Premium-tier model.
- **Critic** — explicit devil's advocate. Reads expert reactions, identifies
  weak claims, methodological gaps, surface-level analysis. Posts critiques
  as roundtable threads. Mid/premium model.
- **Contrarian** — argues the opposite case. Where the Critic asks "is this
  reasoning sound?", the Contrarian asks "what if the opposite is true?"
  Distinct mandate: maintain a "minority view" position over time, push back
  even on settled-feeling consensus. Premium-tier model.
- **Question Generator** — proposes 1–3 new threads / open questions per
  standup. Reads the corpus and roundtable, looks for unexplored angles.
  Mid-tier model.

### Subject experts (default 3, swappable per subject)

- **Empiricist** — data, methods, what's measurable, replication
- **Theorist** — frameworks, models, conceptual clarity
- **Historian / Contextualist** — precedent, comparable cases, base rates

User can clone any role, edit prompts, change models, or add bespoke experts
(e.g. "Energy-policy expert" for one subject).

## 6. Daily loop

### Overnight cron (cheap models, target ≤$2/day across all subjects)
1. Librarian pulls every configured source, dedups against the corpus,
   parses to text, summarizes each new item to ≤500-token brief, tags by
   domain, updates bibliography with a one-line note.
2. Each subject expert receives domain-relevant briefs (Librarian-tagged)
   and may write a short reaction-note (private memory + public artifact).
   Rate-limited: max N items per agent per cycle.

### On standup login (premium models, target ~$3–5/standup)
3. Editor reads overnight artifacts, drafts the briefing.
4. Critic scans expert reactions, opens roundtable threads on tensions and
   weak claims.
5. Contrarian posts ≥1 "what if the opposite" thread per standup, drawing
   on its own running minority position.
6. Question Generator proposes 1–3 new threads.

### During the day
7. User issues instructions to specific agents or broadcast. Cycle agents
   queue instructions; on-demand agents fire immediately and stream output
   back via SSE.
8. Web-search-enabled agents fire searches when needed.

## 7. Standup UI

One page per subject. Top-level switcher among the user's ≤3 active
subjects. Layout:

- **Top — Briefing.** Editor's executive summary. ~300 words. Inline links to
  cited artifacts and corpus items. Timestamp + model badge.
- **Middle — Agent cards.** Grid of tiles, one per Agent on this subject.
  Each tile shows: name, role badge, model badge, cycle indicator, last
  output snippet (≤120 chars), status (idle / running / queued / over-budget).
  Click → side panel with full activity log + chat-style instruction box
  (one-shot vs. persistent toggle) + per-agent settings (model, cycle,
  budget cap, system prompt addendum).
- **Bottom — Roundtable.** Threaded artifact view. Critic flags, Contrarian
  posts, Question-Generator threads, expert reactions, user replies. User
  can reply addressed to one agent (`@empiricist`) or broadcast.

Plus a **Library tab** per subject: bibliography table with Librarian's
running comments, filterable by source type, tag, recency.

## 8. Leadership flow

- **Instructions are first-class artifacts** of kind `instruction`.
- Address: one agent (`addressed_to=agent_id`) or broadcast (`addressed_to=null`).
- Persistence:
  - **One-shot:** consumed by next task; logged in artifact stream
  - **Persistent:** appended to the agent's `system_prompt` addendum;
    visible and editable in the agent's settings panel
- Cycle agents: queued, consumed on next cycle
- On-demand agents: "Execute now" button runs in foreground, streams output
- Standup is when you give shape to the day; mid-day instructions are
  corrections / redirects

## 9. Cost discipline

- **Cheap tier:** Gemini 2.5 Flash, Haiku 4.5, GPT-4o-mini
- **Mid tier:** Sonnet 4.6, GPT-4o
- **Premium tier:** Opus 4.7, GPT-4o (premium calls)
- Default tier per role:
  - Librarian, Question-Generator (cycles): cheap
  - Subject experts (cycles): mid
  - Editor, Critic, Contrarian (standup): premium
- Per-agent `daily_budget_usd` with hard stop and UI warning at 80%
- Global $10/day backstop: when hit, all non-on-demand agents pause until
  next UTC midnight; user is notified
- Token accounting: log usage per OpenRouter call, attribute to agent

## 10. API-first design (v2 readiness)

v1 doesn't expose a public API, but is built so v2 can with minimal rework:

- All FastAPI routes are versioned under `/api/v1/...`
- Frontend talks to the backend exclusively via these HTTP endpoints
  (no direct DB access, no server-side template rendering of business data)
- All request/response bodies are typed Pydantic models in
  `backend/schemas/` — these become the public schema
- FastAPI auto-generates OpenAPI (`/api/v1/openapi.json`); served but
  unauthenticated-public access disabled in v1
- Domain logic lives in `backend/services/` (not in route handlers); routes
  are thin adapters
- Auth abstraction: a `current_principal` dependency that resolves either
  JWT (v1) or API key (v2 will add) without touching downstream code
- v2 path: add API-key model + rate limiter + scope enforcement + public
  OpenAPI docs; no domain or schema rewrites required

## 11. v1 scope summary

**In scope:**
- Subjects (≤3 active) with archive
- Template roster + per-agent edit/clone/add
- Librarian ingestion: upload+paste, web search (Tavily), RSS, arXiv API,
  YouTube captions (yt-dlp), free-text user notes
- Per-agent siloed memory (pgvector + structured)
- Daily loop with APScheduler cron
- Standup UI (briefing + cards + roundtable + library)
- Per-agent model + cycle + budget dials
- OpenRouter integration with token accounting
- Commented bibliography
- Single-user JWT auth
- Daily $ caps (per-agent + global)
- API-versioned internal HTTP layer

**Deferred to v2:**
- Public API surface (designed-for, not exposed)
- Podcast ASR
- Free inter-agent debate beyond Critic/Contrarian
- Semantic Scholar / PubMed connectors
- BibTeX / Zotero export
- Multi-user
- Mobile UI

## 12. Risks & open questions

- **Memory bloat:** pgvector grows unbounded. v1 mitigation: per-agent
  retention policy (e.g. summarize+evict entries older than 90 days unless
  marked important). Revisit when first subject hits 1000+ artifacts.
- **Standup cost variance:** premium-tier standup may exceed budget when
  there's lots of overnight material. v1 mitigation: Editor truncates input
  to top-N artifacts by Librarian-assigned importance.
- **Source coverage:** Tavily + RSS + arXiv covers most needs but may miss
  domain-specific journals. v2 connector framework planned.
- **Cognitive friction quality:** the value of Critic / Contrarian depends
  on prompt quality and model choice. The per-agent experimental harness
  (model + prompt dials) is itself the mitigation: tune empirically.
- **OpenRouter availability:** single point of failure. v1 mitigation: log
  failures, retry with exponential backoff; v2 may add direct provider
  fallbacks.
