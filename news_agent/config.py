from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

DEFAULT_SOURCES = [
    # 国内权威媒体
    {"name": "人民网（时政）", "url": "http://www.people.com.cn/rss/politics.xml", "region": "cn", "hint": "时政新闻"},
    {"name": "中国新闻网", "url": "https://www.chinanews.com.cn/rss/scroll-news.xml", "region": "cn", "hint": "时政新闻"},
    # 国内科技/数码
    {"name": "IT之家", "url": "https://www.ithome.com/rss/", "region": "cn", "hint": "科技新闻"},
    {"name": "少数派", "url": "https://sspai.com/feed", "region": "cn", "hint": "科技新闻"},
    # 国际权威媒体（自动整理为中文通顺版本；不同网络环境下部分源可能超时并被自动跳过）
    {"name": "中国日报（国际）", "url": "https://www.chinadaily.com.cn/rss/china_rss.xml", "region": "intl", "hint": "时政新闻"},
    {"name": "BBC 中文网", "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "region": "intl", "hint": "国际局势"},
    {"name": "BBC 全球", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "region": "intl", "hint": "国际局势"},
    {"name": "BBC 中国", "url": "https://feeds.bbci.co.uk/news/china/rss.xml", "region": "intl", "hint": "国际局势"},
    {"name": "BBC 科技", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "region": "intl", "hint": "科技新闻"},
    {"name": "卫报·全球", "url": "https://www.theguardian.com/world/rss", "region": "intl", "hint": "国际局势"},
    {"name": "卫报·科技", "url": "https://www.theguardian.com/technology/rss", "region": "intl", "hint": "科技新闻"},
    {"name": "半岛电视台", "url": "https://www.aljazeera.com/xml/rss/all.xml", "region": "intl", "hint": "国际局势"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "region": "intl", "hint": "科技新闻"},
    {"name": "NPR 新闻", "url": "https://feeds.npr.org/1001/rss.xml", "region": "intl", "hint": "社会民生"},
    {"name": "NPR 全球", "url": "https://feeds.npr.org/1002/rss.xml", "region": "intl", "hint": "国际局势"},
    {"name": "CNBC", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "region": "intl", "hint": "财经商业"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "region": "intl", "hint": "科技新闻"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "region": "intl", "hint": "科技新闻"},
    {"name": "MIT 科技评论", "url": "https://www.technologyreview.com/feed/", "region": "intl", "hint": "科技新闻"},
    {"name": "Slashdot", "url": "https://rss.slashdot.org/Slashdot/slashdotMain", "region": "intl", "hint": "科技新闻"},
    {"name": "Variety（影视文娱）", "url": "https://variety.com/feed/", "region": "intl", "hint": "文娱体育"},
    {"name": "arXiv AI（论文）", "url": "https://export.arxiv.org/rss/cs.AI", "region": "intl", "hint": "教育科研"},
    {"name": "Defense News（军工）", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "region": "intl", "hint": "军事新闻"},
    {"name": "Army Technology（军工）", "url": "https://www.army-technology.com/feed/", "region": "intl", "hint": "军事新闻"},
]

DEFAULT_CONFIG = {
    "timezone": "Asia/Shanghai",
    "max_items": 400,
    "per_source_limit": 40,
    "fetch_timeout": 12,
    "dedup_threshold": 0.86,
    "min_title_len": 10,
    "max_key_points": 6,
    "llm": {"provider": "auto", "base_url": "", "model": ""},
}


def load_config(path: str | Path | None = None) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if path is None:
        here = Path(__file__).resolve().parent.parent
        path = here / "config.yaml"
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        _deep_merge(cfg, user_cfg)
    else:
        log.info("未找到 config.yaml，使用内置默认配置")
    if not cfg.get("sources"):
        cfg["sources"] = DEFAULT_SOURCES
    return cfg


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def llm_enabled(cfg: dict) -> bool:
    provider = (cfg.get("llm") or {}).get("provider", "auto").lower()
    if provider == "none":
        return False
    if provider in ("auto", "openai") and os.environ.get("OPENAI_API_KEY"):
        return True
    return False
