from __future__ import annotations

import logging
from pathlib import Path

from .models import CATEGORY_ORDER, NewsItem, CATEGORIES

log = logging.getLogger(__name__)

DISCLAIMER = (
    "本日报由 AI Agent 自动抓取、去重、分类、摘要、排版生成，仅作资讯汇总。"
    "内容来自权威媒体公开 RSS 信源，不代表本项目立场；部分内容为机器整理，请以源站为准。"
)


def render_daily(root: Path, date_str: str, items: list[NewsItem], stats: dict) -> Path:
    """生成 DailyNews/YYYY-MM/YYYY-MM-DD-全球新闻汇总.md"""
    month_dir = root / "DailyNews" / date_str[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    out = month_dir / f"{date_str}-全球新闻汇总.md"

    lines: list[str] = []
    lines.append(f"# 全球新闻汇总（{date_str}）")
    lines.append("")
    total = len(items)
    categories = sum(1 for c in CATEGORIES if stats.get("counts", {}).get(c))
    lines.append(
        f"> 共收录 {total} 条，覆盖 {categories} 个分类；来源 {stats.get('sources', 0)} 家权威媒体。"
    )
    lines.append("")

    hot = [it for it in items if it.is_hot]
    if hot:
        lines.append("## 热点速览（置顶）")
        lines.append("")
        for idx, it in enumerate(hot, 1):
            _append_item_block(lines, idx, it, prefix="【热点】")
        lines.append("")

    for cat in CATEGORY_ORDER:
        group = [it for it in items if it.category == cat]
        if not group:
            continue
        lines.append(f"## {cat}")
        lines.append("")
        ordered = sorted(
            group,
            key=lambda it: (
                it.is_hot,
                it.is_breaking,
                it.priority_boost,
                it.score,
                it.published is not None,
            ),
            reverse=True,
        )
        for idx, it in enumerate(ordered, 1):
            _append_item_block(lines, idx, it)
        lines.append("")

    lines.append("---")
    lines.append(f"> {DISCLAIMER}")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    log.info("已生成日报：%s", out)
    return out


def update_category_archives(root: Path, date_str: str, items: list[NewsItem]) -> list[Path]:
    """按分类把当日新闻追加到 Category/*归档.md（幂等：同一天不重复追加）。"""
    cat_dir = root / "Category"
    cat_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for cat in CATEGORIES:
        group = [it for it in items if it.category == cat]
        if not group:
            continue
        path = cat_dir / f"{cat}归档.md"
        if not path.exists():
            path.write_text(
                f"# {cat}归档\n\n"
                f"> 本文件由新闻智能体自动维护，每日追加更新。仅作资讯汇总，内容来自权威媒体公开 RSS。\n\n"
                f"---\n\n",
                encoding="utf-8",
            )
        existing = path.read_text(encoding="utf-8")
        if f"## {date_str}" in existing:
            log.debug("当日已归档：%s", path.name)
            continue
        block = [f"## {date_str}", ""]
        for it in group:
            link = f" [原文]({it.link})" if it.link else ""
            brief = (it.one_line or "")[:80]
            block.append(f"- **{it.title}**（{it.source}）{('— ' + brief) if brief else ''}{link}")
        block.append("")
        path.write_text(existing.rstrip("\n") + "\n\n" + "\n".join(block) + "\n", encoding="utf-8")
        written.append(path)
    log.info("已更新分类归档 %d 个文件", len(written))
    return written


def _append_item_block(lines: list[str], idx: int, it: NewsItem, prefix: str = "") -> None:
    flag = ""
    if it.is_hot:
        flag += " · 热点"
    if it.is_breaking:
        flag += " · 突发"
    if it.priority_boost:
        flag += " · 高权重"
    title = f"{prefix}{it.title}{flag}".rstrip(" ·")
    lines.append(f"### {idx}. {title}")
    lines.append("")
    source = it.source
    if it.link:
        source = f"[{source}]({it.link})"
    lines.append(f"**来源**：{source} ｜ **时间**：{it.date_str() or '—'}")
    lines.append("")
    lines.append(f"**摘要**：{it.one_line or '—'}")
    lines.append("")
    if it.key_points:
        lines.append("**要点**：")
        for n, pt in enumerate(it.key_points, 1):
            lines.append(f"{n}. {pt}")
        lines.append("")
    lines.append(f"**影响**：{it.impact or '—'}")
    lines.append("")
    lines.append(f"**分类**：{it.category}")
    lines.append("")
