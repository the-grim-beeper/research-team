import httpx

from app.services import ingestion


_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test feed</title>
    <item>
      <title>Hello world</title>
      <link>https://example.com/a</link>
      <guid>guid-a</guid>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
      <description><![CDATA[<p>Some <b>HTML</b> content</p>]]></description>
    </item>
    <item>
      <title>Second</title>
      <link>https://example.com/b</link>
      <guid>guid-b</guid>
      <description>Plain text</description>
    </item>
  </channel>
</rss>
"""

_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001</id>
    <title>Test paper one</title>
    <summary>Summary of paper one</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00002</id>
    <title>Test paper two</title>
    <summary>Summary of paper two</summary>
    <published>2024-01-02T00:00:00Z</published>
    <author><name>Charlie</name></author>
  </entry>
</feed>
"""


async def test_fetch_rss_parses_entries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_RSS_FEED)

    items = await ingestion.fetch_rss(
        "https://example.com/feed", transport=httpx.MockTransport(handler)
    )
    assert len(items) == 2
    assert items[0]["title"] == "Hello world"
    assert items[0]["external_id"] == "guid-a"
    assert "HTML content" in items[0]["text"]
    assert items[1]["title"] == "Second"


async def test_fetch_arxiv_parses_atom():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_ARXIV_FEED)

    items = await ingestion.fetch_arxiv(
        "test", transport=httpx.MockTransport(handler)
    )
    assert len(items) == 2
    assert items[0]["title"] == "Test paper one"
    assert "Alice" in items[0]["authors"]
    assert items[0]["external_id"].startswith("http://arxiv.org/abs/")


def test_make_text_item_dedups_by_content():
    a = ingestion.make_text_item("hello world")
    b = ingestion.make_text_item("hello world")
    c = ingestion.make_text_item("different")
    assert a["external_id"] == b["external_id"]
    assert a["external_id"] != c["external_id"]
    assert a["text"] == "hello world"
