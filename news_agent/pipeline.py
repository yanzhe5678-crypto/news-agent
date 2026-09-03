from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .classify import classify_items, observed_categories
from .config import load_config
from .dedup import deduplicate
from .fetch import fetch_all
from .models import NewsItem
from .render import render_daily, update_category_archives
from .summarize import summarize_items

log = logging.getLogger("news_agent")


def _to_local(item: NewsItem, tz: str) -> NewsItem:
    if item.published is not None and item.published.tzinfo is not None:
        item.published = item.published.astimezone(ZoneInfo(tz))
    return item


def run(
    date_str: str | None = None,
    limit: int | None = None,
    config_path: str | None = None,
    no_llm: bool = False,
    root: Path | None = None,
) -> dict:
    cfg = load_config(config_path)
    if no_llm:
        cfg.setdefault("llm", {})["provider"] = "none"

    tz = cfg.get("timezone", "Asia/Shanghai")
    now = datetime.now(ZoneInfo(tz))
    target = date_str or now.strftime("%Y-%m-%d")

    if root is None:
        root = Path(__file__).resolve().parent.parent

    log.info("开始抓取（目标日期 %s）", target)
    items = fetch_all(cfg)
    items = [_to_local(it, tz) for it in items]

    # 只保留目标日期的新闻；无发布时间的按目标日期计入
    daily_items = []
    for it in items:
        if it.published is None or it.date_str() == target:
            if it.published is None:
                it.published = datetime.strptime(target, "%Y-%m-%d").replace(tzinfo=ZoneInfo(tz))
            daily_items.append(it)

    log.info("原始条目 %d 条，目标日期匹配 %d 条", len(items), len(daily_items))
    daily_items = deduplicate(daily_items, cfg.get("dedup_threshold", 0.86))
    if limit:
        daily_items = daily_items[: limit]
    classify_items(daily_items)
    summarize_items(daily_items, cfg)

    def _rank_key(it):
        return (
            bool(it.is_hot),
            bool(it.is_breaking),
            bool(it.priority_boost),
            float(it.score or 0.0),
        )

    daily_items.sort(key=_rank_key, reverse=True)

    counts = observed_categories(daily_items)
    stats = {
        "date": target,
        "total": len(daily_items),
        "sources": len({it.source for it in daily_items}),
        "counts": counts,
    }

    daily_path = render_daily(root, target, daily_items, stats)
    archives = update_category_archives(root, target, daily_items)

    log.info(
        "完成：日报 %s，归档 %d 个文件，共 %d 条",
        daily_path.name,
        len(archives),
        len(daily_items),
    )
    return {"stats": stats, "daily": daily_path, "archives": archives}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="每日全自动全球新闻智能体")
    parser.add_argument("--date", help="目标日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--limit", type=int, default=None, help="最多收录条数")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--no-llm", action="store_true", help="强制使用本地抽取式摘要")
    parser.add_argument("--verbose", action="store_true", help="输出详细信息")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = run(
        date_str=args.date,
        limit=args.limit,
        config_path=args.config,
        no_llm=args.no_llm,
    )
    stats = result["stats"]
    print(
        f"\n日报已生成：{stats['date']}，共 {stats['total']} 条，"
        f"来源 {stats['sources']} 家，分类 {sum(1 for v in stats['counts'].values() if v)} 个。"
    )
    for cat, cnt in stats["counts"].items():
        if cnt:
            print(f"  {cat}: {cnt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
