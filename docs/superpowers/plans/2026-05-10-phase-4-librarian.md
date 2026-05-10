# Research Team — Phase 4 (Librarian Ingestion) Plan

**Goal:** A subject can have ingestion sources registered (RSS feed, arXiv query, single URL, or direct text/notes). On manual trigger (or default-team Librarian execution), the Librarian fetches new items, parses them to plain text, deduplicates, summarizes via the Librarian agent's LLM call, tags by domain, assigns importance 1–5, and creates a bibliography entry per subject. The user can browse a "Library" view per subject showing sources, recent corpus items with summaries, and the running commented bibliography.

**Architecture:** Three new tables (Source, CorpusItem, BibliographyEntry). Ingestion pipeline is a set of pure async functions that fetch and parse → produce candidate CorpusItem dicts. A Librarian processing pass invokes the existing OpenRouter client to generate summary/tags/importance for each new item, then writes the bibliography entry. v1 ships RSS, arXiv, URL, and text — Tavily search and YouTube captions land in Phase 4.5 follow-up.

**Tech additions:** `feedparser`, `trafilatura`, `httpx` (already added in Phase 3).

## File structure

```
backend/
  alembic/versions/0003_sources_corpus_bibliography.py        NEW
  app/models/source.py, corpus.py, bibliography.py            NEW
  app/services/sources.py                                     NEW
  app/services/ingestion.py                                   NEW (rss/arxiv/url/text fetchers)
  app/services/librarian.py                                   NEW (process new items)
  app/services/corpus.py                                      NEW (list, get)
  app/services/bibliography.py                                NEW (list, append_comment)
  app/schemas/source.py, corpus.py, bibliography.py           NEW
  app/routes/library.py                                       NEW (sources + corpus + bibliography under one tag)
  app/main.py                                                 MOD (register router)
  pyproject.toml                                              MOD (feedparser, trafilatura)
  tests/test_ingestion_*, test_librarian_*, test_library_routes.py  NEW

frontend/
  lib/types.ts                                                MOD (Source, CorpusItem, BibliographyEntry)
  app/subject/library/page.tsx                                NEW (or extend /subject)
  components/library-view.tsx                                 NEW
  components/add-source-form.tsx                              NEW
  app/subject/page.tsx                                        MOD (link to library)
```

## Tasks

### Task 1 — Migration 0003
Tables:
- `sources` — id, subject_id (FK cascade), kind ("rss" | "arxiv" | "url" | "notes"), config_json (e.g. `{"url": ...}` or `{"query": ...}`), display_name, created_at
- `corpus_items` — id, subject_id (FK cascade), source_id (FK nullable — direct user notes have null), external_id (string, used for dedup with subject), title, authors_json (jsonb list), published_at (nullable), url (nullable), text (full extracted plain text), summary (nullable, populated by Librarian), tags_json (jsonb list), importance (nullable int 1-5), created_at; unique (subject_id, source_id, external_id) where external_id is non-null
- `bibliography_entries` — id, corpus_item_id (FK unique), subject_id (FK cascade for query convenience), comments (text, markdown), created_at, updated_at

### Task 2 — Models
SQLAlchemy mapped classes for the three new tables. Register in `models/__init__.py`.

### Task 3 — Ingestion service
`services/ingestion.py` exports four async functions, each returning `list[dict]` of candidate items with keys `external_id, title, authors, published_at, url, text`:

- `fetch_rss(url, transport=None)` — uses feedparser; external_id = entry.id or entry.link
- `fetch_arxiv(query, max_results=20, transport=None)` — hits `http://export.arxiv.org/api/query?search_query=…`, parses Atom; external_id = arxiv id
- `fetch_url(url, transport=None)` — httpx GET, Trafilatura `extract()` for body text; external_id = url; title from extracted metadata
- `make_text_item(text, title="")` — wrap a user note; external_id = sha256(text)[:16]; no fetch

All four are pure (no DB writes). The persistence step is in Task 4.

Tests use httpx MockTransport for the network ones; feedparser parses test fixtures from strings.

### Task 4 — Sources service + persist-new
`services/sources.py`:
- `register(session, subject_id, kind, config, display_name) -> Source`
- `list_for_subject`, `get`, `delete`
- `persist_new_items(session, *, subject_id, source_id, items: list[dict]) -> list[CorpusItem]` — for each candidate, dedup against existing (subject_id, external_id), insert new ones; commit; return only the new rows

Tests: dedup behaviour, basic CRUD.

### Task 5 — Librarian processing
`services/librarian.py::process_corpus_item(session, *, corpus_item, librarian_agent, chat_fn) -> BibliographyEntry`:

1. Build a prompt: "Read the following source. Write: (1) a ≤500-token summary, (2) up to 5 domain tags as JSON list, (3) an importance score 1–5. Reply as JSON `{\"summary\": str, \"tags\": [str], \"importance\": int}`."
2. Call chat_fn with the librarian_agent's model; parse JSON from response; tolerate extra prose by extracting first JSON block
3. Update the corpus_item with summary/tags/importance
4. Create a bibliography entry: comments = "First seen {date}. {summary first sentence}"
5. Update librarian_agent.spent_today_usd

`process_new_for_subject(session, subject_id, max_items=20)` is the convenience entry point: looks up the librarian agent on the subject, finds corpus_items with `summary IS NULL`, processes up to N. Returns the bibliography entries created.

Tests: stub chat_fn returning canned JSON; verify summary/tags written and bibliography created.

### Task 6 — Corpus + bibliography services + routes
`services/corpus.py::list_for_subject(session, subject_id, limit) -> list[CorpusItem]` (newest first)

`services/bibliography.py`:
- `list_for_subject(session, subject_id) -> list[(BibliographyEntry, CorpusItem)]` (joined)
- `append_comment(session, entry_id, user_id, comment) -> BibliographyEntry` (auth via subject ownership check)

`routes/library.py` (single router under `/api/v1`):
- `POST /subjects/{sid}/sources` — register (body: kind, config, display_name)
- `GET /subjects/{sid}/sources`
- `DELETE /sources/{source_id}`
- `POST /subjects/{sid}/sources/{source_id}/ingest` — fetch + persist + librarian-process; returns list[BibliographyEntry]
- `POST /subjects/{sid}/notes` — body `{title, text}`; persists as text-source item, librarian-process inline
- `POST /subjects/{sid}/url` — body `{url}`; fetches via Trafilatura, persists, processes
- `GET /subjects/{sid}/corpus`
- `GET /subjects/{sid}/bibliography`
- `POST /bibliography/{entry_id}/comment` — append a user comment

Tests cover auth, dedup, librarian invocation (chat stubbed).

### Task 7 — Frontend Library tab
`/subject/library/?id=N` page:
- Add-source form (kind dropdown: rss/arxiv/url/notes, then a contextual config field)
- Sources list with "Ingest" button per source and "Delete"
- Bibliography list (corpus_item title, link, summary excerpt, importance, tags, comments)
- Free-form "Add a quick note" + "Fetch a URL" inline forms

`AddSourceForm`, `SourceList`, `BibliographyView` components. Static-export-compatible via query params (same pattern as detail page).

Add a "Library" link from the subject detail page header.

### Task 8 — Smoke test
Compose up, register an RSS source (e.g. `https://hnrss.org/frontpage`), trigger ingest, see ≥5 corpus items, verify Librarian populated summaries (requires real OPENROUTER_API_KEY for the live test).

## Acceptance

- All backend tests pass with mocked HTTP and chat
- Sources can be registered, listed, deleted via API
- Manual ingest creates corpus items and bibliography entries
- Library page renders sources + bibliography
- Phase 4 merged to main
