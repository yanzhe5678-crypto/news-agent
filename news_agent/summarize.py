from __future__ import annotations

import json
import logging
import os
import re

import requests

from .config import llm_enabled
from .models import CATEGORIES, NewsItem

log = logging.getLogger(__name__)

_SENT_RE = re.compile(r"[^。！？!?.;\n]+[。！？!?.;]?\s*")


def summarize_items(items: list[NewsItem], cfg: dict) -> None:
    use_llm = llm_enabled(cfg)
    for item in items:
        if use_llm:
            try:
                llm_fill(item, cfg)
                continue
            except Exception:
                log.warning("LLM 摘要失败，回退本地抽取：%s", item.title[:40], exc_info=True)
        local_fill(item, cfg)


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.findall(text) if s.strip()]


def local_fill(item: NewsItem, cfg: dict) -> None:
    max_points = int(cfg.get("max_key_points", 6))
    source_text = item.summary or item.title
    sentences = split_sentences(source_text)
    if not sentences:
        sentences = [item.title]

    one_line = _clip(sentences[0], 90)
    points: list[str] = []
    for s in sentences[1:]:
        if len(points) >= max_points:
            break
        cleaned = _clip(s, 120)
        if cleaned and cleaned != one_line and cleaned not in points:
            points.append(cleaned)
    if not points:
        points = [_clip(s, 80) for s in sentences[: max_points]]

    lang_note = ""
    if item.raw_lang == "en":
        lang_note = "（外电原文，未配置 AI 模型时保留原文摘要）"
    item.one_line = one_line + lang_note
    item.key_points = points
    item.impact = f"【{item.category or '综合'}】相关动态，短期影响有待观察，建议持续关注后续进展。"


def llm_fill(item: NewsItem, cfg: dict) -> None:
    llm_cfg = cfg.get("llm") or {}
    base_url = (llm_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    if not base_url:
        base_url = "https://api.openai.com/v1"
    model = llm_cfg.get("model") or os.environ.get("NEWS_AGENT_MODEL") or "gpt-4o-mini"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY")

    need_chinese = item.raw_lang == "en"
    language_rule = "如原文为外文，请将摘要、要点、影响统一整理为通顺中文。" if need_chinese else "请使用中文输出。"

    system = (
        "你是一名严谨、中立、客观的新闻编辑。请基于给定新闻输出结构化摘要，"
        "要求：摘要高度浓缩、不评论、不带主观倾向；要点 3-6 条；影响解读简短客观中立；"
        "分类必须且只能从以下八个中选择一个：" + "、".join(CATEGORIES) + "。"
        + language_rule
        + "只返回 JSON，不要输出其他文字。JSON 字段：{"
        '"summary": "...", "key_points": ["..."], "impact": "...", "category": "..."}'
    )
    user = (
        f"标题：{item.title}\n"
        f"来源：{item.source}\n"
        f"发布时间：{item.date_str()}\n"
        f"正文摘要：{(item.summary or '')[:1500]}\n"
        f"疑似分类：{item.category or '未定'}"
    )

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        },
        timeout=int((llm_cfg.get("timeout") or 40)),
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    data = _parse_json(content)

    item.one_line = _clip(str(data.get("summary", "")), 160) or _clip(item.title, 90)
    points = data.get("key_points") or []
    item.key_points = [_clip(str(p), 140) for p in points if str(p).strip()][: int(cfg.get("max_key_points", 6))]
    if not item.key_points:
        item.key_points = [_clip(item.one_line, 120)]
    item.impact = _clip(str(data.get("impact", "")), 200) or item.impact
    cat = str(data.get("category", "")).strip()
    if cat:
        item.category = _normalize_category(cat)


def _normalize_category(cat: str) -> str:
    for valid in CATEGORIES:
        if valid == cat or valid in cat or cat in valid:
            return valid
    return "综合" if cat else "国际局势"


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError("LLM 返回内容无法解析为 JSON")


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
