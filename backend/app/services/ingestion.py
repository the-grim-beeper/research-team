"""Pure-async fetchers for the four v1 source kinds.

Each function returns a list of dicts shaped like:
    {"external_id": str, "title": str, "authors": list[str],
     "published_at": datetime|None, "url": str|None, "text": str}

These are candidate items — persistence and dedup happen in services/sources.py.
"""
from __future__ import annotations

import hashlib
import html as html_module
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
import trafilatura

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html_fragment(s: str) -> str:
    """Lightweight tag stripper for short HTML fragments (RSS descriptions).

    Trafilatura is tuned for full HTML documents; on naked fragments it returns
    an empty string. For RSS bodies we just want readable text fast.
    """
    if not s:
        return ""
    no_tags = _TAG_RE.sub(" ", s)
    return html_module.unescape(re.sub(r"\s+", " ", no_tags)).strip()


def _entry_to_item(entry: Any) -> dict[str, Any]:
    """Convert a feedparser entry into our common shape."""
    external_id = (
        getattr(entry, "id", None)
        or getattr(entry, "guid", None)
        or getattr(entry, "link", None)
        or hashlib.sha256(str(entry).encode()).hexdigest()[:32]
    )
    summary = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
    body = ""
    if hasattr(entry, "content") and entry.content:
        body = entry.content[0].get("value", "")
    text = _strip_html_fragment(body) if body else _strip_html_fragment(summary)
    authors = []
    if hasattr(entry, "authors"):
        authors = [a.get("name") for a in entry.authors if a.get("name")]
    elif hasattr(entry, "author"):
        authors = [entry.author]

    pub: datetime | None = None
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        try:
            pub = datetime(*parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pub = None

    return {
        "external_id": str(external_id)[:512],
        "title": (getattr(entry, "title", "") or "")[:512],
        "authors": authors,
        "published_at": pub,
        "url": getattr(entry, "link", None),
        "text": (text or "").strip(),
    }


async def fetch_rss(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(transport=transport, timeout=30.0, follow_redirects=True) as cx:
        resp = await cx.get(url)
        resp.raise_for_status()
        body = resp.text
    parsed = feedparser.parse(body)
    return [_entry_to_item(e) for e in parsed.entries]


_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


async def fetch_arxiv(
    query: str,
    *,
    max_results: int = 20,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, Any]]:
    api = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as cx:
        resp = await cx.get(api, params=params)
        resp.raise_for_status()
        body = resp.text

    root = ET.fromstring(body)
    items = []
    for entry in root.findall("a:entry", _ATOM_NS):
        arxiv_id = entry.findtext("a:id", default="", namespaces=_ATOM_NS).strip()
        title = (entry.findtext("a:title", default="", namespaces=_ATOM_NS) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=_ATOM_NS) or "").strip()
        link = arxiv_id  # arxiv id is itself a URL
        published = entry.findtext("a:published", default=None, namespaces=_ATOM_NS)
        try:
            pub = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
        except (AttributeError, ValueError):
            pub = None
        authors = [
            a.findtext("a:name", default="", namespaces=_ATOM_NS) or ""
            for a in entry.findall("a:author", _ATOM_NS)
        ]
        items.append(
            {
                "external_id": arxiv_id[:512],
                "title": title[:512],
                "authors": [a for a in authors if a],
                "published_at": pub,
                "url": link or None,
                "text": summary,
            }
        )
    return items


async def fetch_url(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        transport=transport, timeout=30.0, follow_redirects=True
    ) as cx:
        resp = await cx.get(url, headers={"User-Agent": "research-team/0.1"})
        resp.raise_for_status()
        body = resp.text

    text = trafilatura.extract(body, include_comments=False, include_tables=False) or ""
    metadata = trafilatura.extract_metadata(body)
    title = metadata.title if metadata and metadata.title else url
    authors = []
    if metadata and metadata.author:
        authors = [a.strip() for a in metadata.author.split(";") if a.strip()]
    pub: datetime | None = None
    if metadata and metadata.date:
        try:
            pub = datetime.fromisoformat(metadata.date)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pub = None

    return [
        {
            "external_id": url[:512],
            "title": (title or "")[:512],
            "authors": authors,
            "published_at": pub,
            "url": url,
            "text": text.strip(),
        }
    ]


def make_text_item(text: str, title: str = "") -> dict[str, Any]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    return {
        "external_id": f"text:{digest}",
        "title": (title or text[:80] or "Untitled note")[:512],
        "authors": [],
        "published_at": datetime.now(timezone.utc),
        "url": None,
        "text": text.strip(),
    }
