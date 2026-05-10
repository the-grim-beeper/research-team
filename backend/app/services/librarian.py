"""Librarian processing: turn raw corpus items into summarized + tagged + scored
items with bibliography entries. The Librarian agent's model is used for this.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import Agent
from app.models.bibliography import BibliographyEntry
from app.models.corpus import CorpusItem
from app.models.role import Role
from app.pricing import estimate_cost
from app.services import bibliography as bibliography_service
from app.services import corpus as corpus_service
from app.services import openrouter

_PROMPT = (
    "Read the following source. Reply with a single JSON object exactly matching:\n"
    "{\"summary\": str, \"tags\": [str], \"importance\": int}\n"
    "summary: at most 500 tokens, focused on what's substantively new or specific\n"
    "tags: 1–5 short domain tags as lowercase strings\n"
    "importance: 1=trivial, 5=must-read for this subject. No prose outside JSON."
)


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> dict:
    match = _JSON_BLOCK_RE.search(text or "")
    if not match:
        raise ValueError(f"No JSON object found in response: {text!r}")
    return json.loads(match.group(0))


async def _librarian_for_subject(session: AsyncSession, subject_id: int) -> Agent | None:
    rows = await session.scalars(
        select(Agent)
        .join(Role, Role.id == Agent.role_id)
        .where(Agent.subject_id == subject_id, Role.slug == "librarian")
    )
    return rows.first()


async def process_corpus_item(
    session: AsyncSession,
    *,
    corpus_item: CorpusItem,
    librarian: Agent,
    chat_fn=None,
) -> BibliographyEntry:
    """Summarize, tag, score, and create the bibliography entry."""
    if chat_fn is None:
        chat_fn = openrouter.chat
    subject_block = corpus_item.text[:8000] or "(no text extracted)"
    messages = [
        {"role": "system", "content": librarian.system_prompt},
        {"role": "system", "content": _PROMPT},
        {
            "role": "user",
            "content": (
                f"Title: {corpus_item.title}\n"
                f"URL: {corpus_item.url or '(none)'}\n\n"
                f"Body:\n{subject_block}"
            ),
        },
    ]
    result = await chat_fn(
        messages, model=librarian.model, max_tokens=settings.max_tokens_default
    )
    cost = estimate_cost(librarian.model, result.prompt_tokens, result.completion_tokens)

    try:
        parsed = _extract_json(result.text or "")
    except (ValueError, json.JSONDecodeError) as e:
        # Fallback: store the raw response as the summary so the user sees something useful.
        corpus_item.summary = (result.text or f"(librarian-parse-failed: {e})")[:4000]
        corpus_item.tags_json = []
        corpus_item.importance = 3
    else:
        corpus_item.summary = str(parsed.get("summary", ""))[:4000]
        tags = parsed.get("tags") or []
        corpus_item.tags_json = [str(t).lower() for t in tags][:10]
        try:
            corpus_item.importance = max(1, min(5, int(parsed.get("importance", 3))))
        except (TypeError, ValueError):
            corpus_item.importance = 3

    librarian.spent_today_usd = (
        Decimal(str(librarian.spent_today_usd)) + cost
    ).quantize(Decimal("0.0001"))
    librarian.last_run_at = datetime.now(timezone.utc)
    await session.commit()

    summary_first_line = (corpus_item.summary or "").split("\n", 1)[0][:240]
    initial_comment = (
        f"First seen {datetime.now(timezone.utc).date().isoformat()}. "
        f"{summary_first_line}"
    )
    return await bibliography_service.upsert(
        session,
        subject_id=corpus_item.subject_id,
        corpus_item_id=corpus_item.id,
        initial_comment=initial_comment,
    )


async def process_new_for_subject(
    session: AsyncSession,
    *,
    subject_id: int,
    max_items: int = 20,
    chat_fn=None,
) -> list[BibliographyEntry]:
    if chat_fn is None:
        chat_fn = openrouter.chat
    librarian = await _librarian_for_subject(session, subject_id)
    if librarian is None:
        return []
    items = await corpus_service.list_unprocessed(session, subject_id, limit=max_items)
    entries = []
    for item in items:
        if librarian.spent_today_usd >= librarian.daily_budget_usd:
            break
        try:
            entry = await process_corpus_item(
                session, corpus_item=item, librarian=librarian, chat_fn=chat_fn
            )
            entries.append(entry)
        except openrouter.OpenRouterError:
            # Skip and let the user retry later.
            continue
    return entries
