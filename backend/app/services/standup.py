"""Run-Standup orchestrator: Editor → Critic → Contrarian → Question-Generator.

Each agent runs in sequence so its prompt can include the prior agent's output
as context. Agents over budget are skipped (their entry is omitted from the
return list); other transport failures bubble up as OpenRouterError.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.artifact import Artifact
from app.models.corpus import CorpusItem
from app.models.role import Role
from app.services import artifacts as artifact_service
from app.services import openrouter
from app.services.execution import BudgetExceeded, run_agent_once

logger = logging.getLogger(__name__)


async def _build_packet(session: AsyncSession, subject_id: int) -> str:
    """Recent corpus summaries + recent artifacts, capped to keep tokens bounded."""
    items = await session.scalars(
        select(CorpusItem)
        .where(CorpusItem.subject_id == subject_id, CorpusItem.summary.is_not(None))
        .order_by(CorpusItem.created_at.desc())
        .limit(10)
    )
    item_lines = []
    for c in items.all():
        importance = c.importance or "?"
        item_lines.append(
            f"- [{importance}/5] {c.title} — {(c.summary or '').strip()[:300]}"
        )

    arts = await artifact_service.list_for_subject(session, subject_id, limit=20)
    art_lines = []
    for a in arts:
        author = a.author_type if a.author_type == "user" else f"agent#{a.author_id}"
        snippet = (a.body_md or "").strip().replace("\n", " ")[:200]
        art_lines.append(f"- [{a.kind} | {author}] {snippet}")

    parts = []
    if item_lines:
        parts.append("Recent corpus (Librarian summaries):\n" + "\n".join(item_lines))
    if art_lines:
        parts.append("Recent artifacts (newest first):\n" + "\n".join(art_lines))
    return "\n\n".join(parts) if parts else "(no recent activity)"


async def _agent_by_slug(session: AsyncSession, subject_id: int, slug: str) -> Agent | None:
    rows = await session.scalars(
        select(Agent)
        .join(Role, Role.id == Agent.role_id)
        .where(Agent.subject_id == subject_id, Role.slug == slug)
    )
    return rows.first()


_INSTRUCTIONS = {
    "editor": (
        "Write the morning briefing for your researcher. About 300 words. Lead with "
        "what's new, where the team disagrees, and what blocks any user-stated "
        "questions. Link claims to specific recent artifacts by their snippet "
        "where useful. Never info-dump."
    ),
    "critic": (
        "Read the new briefing and the recent expert reactions in the standup "
        "packet. Surface 1–2 weak claims, methodological gaps, or unstated "
        "assumptions. Be specific — quote or paraphrase the exact claim you're "
        "pushing back on. Sharp but not snide."
    ),
    "contrarian": (
        "Argue the strongest case against the central claim of the briefing. "
        "≤200 words. Lead with the counter-thesis as a one-sentence punch, then "
        "two or three reasons. Maintain consistency with prior contrarian "
        "positions in your private memory."
    ),
    "question_generator": (
        "Propose 1–3 specific questions worth pulling next. For each: a "
        "one-sentence question, why it matters now, and what kind of source "
        "would answer it. Ground each question in something the team is "
        "currently confused or split about — not generic."
    ),
}


_KINDS = {
    "editor": "briefing",
    "critic": "critique",
    "contrarian": "roundtable_post",
    "question_generator": "open_question",
}


async def run_standup(
    session: AsyncSession,
    *,
    subject_id: int,
    user_id: int,
    chat_fn=None,
) -> list[Artifact]:
    if chat_fn is None:
        chat_fn = openrouter.chat

    packet = await _build_packet(session, subject_id)
    produced: list[Artifact] = []
    running_context = packet

    for slug in ("editor", "critic", "contrarian", "question_generator"):
        agent = await _agent_by_slug(session, subject_id, slug)
        if agent is None:
            continue
        try:
            artifact = await run_agent_once(
                session,
                agent_id=agent.id,
                user_id=user_id,
                user_instruction=_INSTRUCTIONS[slug],
                artifact_kind=_KINDS[slug],
                extra_system_context=(
                    "Standup packet (shared context for all standup agents):\n\n"
                    + running_context
                ),
                chat_fn=chat_fn,
            )
        except BudgetExceeded:
            logger.info("Standup: %s over budget; skipping", slug)
            continue
        produced.append(artifact)
        # Append this agent's output to the running context so the next sees it.
        running_context = (
            running_context
            + f"\n\n[{slug} just produced — kind={_KINDS[slug]}]:\n"
            + (artifact.body_md or "(empty)")[:2000]
        )

    return produced
