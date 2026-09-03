from __future__ import annotations

import datetime as dt
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import feedparser
import requests

from .models import NewsItem

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 NewsAgent/0.1"
)

_TAG_RE = re.compile(r"<[^>]+>")


def fetch_all(cfg: dict) -> list[NewsItem]:
    """并发抓取全部信源，单个信源失败不影响整体流程。"""
    sources = cfg.get("sources", [])
    timeout = cfg.get("fetch_timeout", 12)
    with ThreadPoolExecutor(max_workers=min(12, max(1, len(sources)))) as pool:
        futures = {pool.submit(fetch_feed, cfg, s): s for s in sources}
        results: list[NewsItem] = []
        for fut, src in futures.items():
            try:
                items = fut.result()
                log.info("%s 收录 %d 条", src.get("name"), len(items))
                results.extend(items)
            except Exception:
                log.exception("信源异常：%s", src.get("name"))
    return results


def fetch_feed(cfg: dict, source: dict) -> list[NewsItem]:
    url = source["url"]
    try:
        resp = requests.get(url, timeout=cfg.get("fetch_timeout", 12), headers={"User-Agent": UA})
        resp.raise_for_status()
    except Exception as exc:
        log.warning("抓取失败 [%s] %s：%s", source.get("name"), url, exc)
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        log.warning("解析失败 [%s]：%s", source.get("name"), exc)
        return []
    items: list[NewsItem] = []
    for entry in parsed.entries[: int(cfg.get("per_source_limit", 40))]:
        item = entry_to_item(entry, source)
        if item is not None:
            items.append(item)
    return items


def entry_to_item(entry, source) -> NewsItem | None:
    raw_title = entry.get("title", "") or ""
    title = clean_text(raw_title).strip()
    if not title:
        return None
    link = entry.get("link", "") or ""
    published = parse_pubdate(entry.get("published_parsed") or entry.get("updated_parsed"))
    summary_parts = []
    for key in ("summary", "description", "content"):
        value = entry.get(key)
        if value is None:
            continue
        if isinstance(value, list) and value:
            value = " ".join(v.get("value", "") for v in value if isinstance(v, dict))
        summary_parts.append(clean_text(str(value)))
    summary = " ".join(p for p in summary_parts if p).strip()
    raw_lang = detect_lang(source, title, summary)
    return NewsItem(
        title=title,
        source=source.get("name", "未知来源"),
        link=link,
        published=published,
        summary=summary,
        raw_lang=raw_lang,
    )


def clean_text(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_pubdate(struct) -> dt.datetime | None:
    if not struct:
        return None
    try:
        return dt.datetime(*struct[:6], tzinfo=dt.timezone.utc)
    except Exception:
        return None


def detect_lang(source: dict, title: str, summary: str) -> str:
    region = source.get("region", "cn")
    sample = (title + " " + summary)[:500]
    cjk = sum(1 for ch in sample if "\u4e00" <= ch <= "\u9fff")
    ratio = cjk / max(1, len(sample.strip()))
    if region == "intl" and ratio < 0.15:
        return "en"
    return "zh"
