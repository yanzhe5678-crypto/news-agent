from __future__ import annotations

import logging
import re

from rapidfuzz import fuzz

from .models import NewsItem

log = logging.getLogger(__name__)

JUNK_PATTERNS = [
    r"红包", r"领券", r"优惠券", r"限时特惠", r"促销", r"抽奖", r"下载 App", r"下载客户端",
    r"关注公众号", r"扫码关注", r"领取资料包", r"直播预告", r"广告", r"荐股", r"加群",
    r"注册即送", r"满减", r"返现",
]

_JUNK_RE = re.compile("|".join(JUNK_PATTERNS))
_PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def normalize_title(title: str) -> str:
    return _PUNCT_RE.sub("", title.lower())


def is_junk(title: str) -> bool:
    return bool(_JUNK_RE.search(title))


def deduplicate(items: list[NewsItem], threshold: float = 0.86) -> list[NewsItem]:
    """
    去除重复新闻：标题相似度超过阈值的新闻合并为同一事件簇，
    保留簇内最早发布、来源更权威的代表条目，同时统计跨源覆盖次数（用于热点识别）。
    """
    sorted_items = sorted(
        [it for it in items if it.published],
        key=lambda it: it.published,
    )
    kept: list[NewsItem] = []
    norms: list[str] = []
    for item in sorted_items:
        norm = normalize_title(item.title)
        item.norm_title = norm
        if len(norm) < 1:
            continue
        if is_junk(item.title):
            log.debug("过滤低质/营销条：%s", item.title[:40])
            continue
        best = None
        best_score = 0.0
        for idx, k in enumerate(kept):
            score = fuzz.token_set_ratio(norm, norms[idx]) / 100.0
            if score > best_score:
                best = k
                best_score = score
        if best is not None and best_score >= threshold:
            best.cover_count += 1
            if not best.link and item.link:
                best.link = item.link
            # 同源多报合并：保留被合并标题作为补充摘要线索
            if item.summary and item.summary not in best.summary:
                best.summary = best.summary + " " + item.summary
        else:
            kept.append(item)
            norms.append(norm)
    kept.sort(key=lambda it: it.published)
    log.info("去重：%d 条 → %d 条", len(items), len(kept))
    return kept
