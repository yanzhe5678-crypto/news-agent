from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from .models import CATEGORIES, CATEGORY_ORDER, NewsItem

log = logging.getLogger(__name__)

# 八大分类关键词（中文 + 英文）；仅作初筛，LLM 开启时可进一步校准
KEYWORDS = {
    "科技新闻": [
        "AI", "人工智能", "大模型", "芯片", "半导体", "机器人", "人形机器人", "具身智能",
        "算法", "开源", "互联网", "数码", "智能手机", "软件", "云计算", "自动驾驶", "量子",
        "GPU", "硬件", "OpenAI", "谷歌", "微软", "苹果", "英伟达", "华为", "小米", "字节",
        "robot", "chip", "AI model", "startup", "tech", "software", "smartphone",
        "quantum", "semiconductor", "llm", "agent", "model", "data center", "cloud",
    ],
    "军事新闻": [
        "军队", "国防", "军演", "导弹", "战机", "舰艇", "航母", "武器", "军事", "防务",
        "北约", "核武", "部队", "演习", "无人机作战", "military", "defense", "missile",
        "drone strike", "navy", "army", "weapons", "tank", "fighter jet",
    ],
    "时政新闻": [
        "国务院", "政策", "部委", "立法", "两会", "政府工作报告", "官员", "外交部", "商务部",
        "发布会", "发改委", "监管", "新规", "条例", "选举", "内阁", "国会", "议会",
        "government", "policy", "law", "parliament", "minister", "regulation",
        "election", "legislation", "cabinet", "senate", "congress",
    ],
    "财经商业": [
        "股市", "A股", "港股", "美股", "股价", "财报", "营收", "净利润", "融资", "IPO",
        "上市", "并购", "收购", "投资", "基金", "央行", "降息", "加息", "通胀", "GDP",
        "贸易", "出口", "制造业", "消费", "企业", "营收", "profit", "earnings", "stock",
        "share price", "ipo", "merger", "investment", "fund", "inflation", "economy",
        "gdp", "trade", "market", "revenue", "bank", "interest rate",
    ],
    "国际局势": [
        "美国", "俄罗斯", "乌克兰", "中东", "欧盟", "联合国", "制裁", "冲突", "停火",
        "外交", "大使", "地缘", "峰会", "北约峰会", "白宫", "五角大楼", "克里姆林宫",
        "war", "conflict", "ceasefire", "sanctions", "diplomacy", "summit", "UN",
        "global", "international", "geopolitical", "border", "embassy",
    ],
    "社会民生": [
        "社会", "民生", "公共安全", "天气", "台风", "暴雨", "地震", "灾害", "养老金",
        "医保", "就业", "住房", "教育公平", "消费者", "交通", "火灾", "事故", "救援",
        "health", "weather", "disaster", "strike", "protest", "crime", "accident",
        "rescue", "housing", "healthcare", "pension",
    ],
    "教育科研": [
        "高校", "大学", "研究", "论文", "期刊", "竞赛", "学术", "录取", "招生", "科研",
        "院士", "诺贝尔", "实验室", "毕业生", "课程", "university", "research", "paper",
        "academic", "scholar", "science", "study", "researchers", "Nobel", "conference",
    ],
    "文娱体育": [
        "电影", "电视剧", "综艺", "音乐", "演唱会", "票房", "奥运", "世界杯", "联赛",
        "冠军", "决赛", "球员", "俱乐部", "游戏", "赛事", "好莱坞", "颁奖", "演唱会",
        "movie", "film", "tv", "music", "concert", "Oscar", "sports", "football",
        "basketball", "match", "champion", "tournament", "NBA", "FIFA", "league",
        "album", "actor",
    ],
}

PRIORITY_PATTERN = re.compile(
    r"AI|人工智能|机器人|人形机器人|具身智能|大模型|芯片|算法|开源|智能体|模型发布|GPT|Claude",
    re.IGNORECASE,
)
BREAKING_PATTERN = re.compile(
    r"突发|快讯|紧急|刚刚|最新|breaking|live|urgent|developing", re.IGNORECASE
)
HOT_PATTERN = re.compile(
    r"重大|重磅|官宣|重大突破|里程碑|首款|全球首|危机|冲突|爆炸|地震|袭击|发射|制裁|停产|发布",
    re.IGNORECASE,
)

_TITLE_WEIGHT = 3.0
_SUMMARY_WEIGHT = 1.0


def _compile(tokens):
    parts = []
    for token in tokens:
        if re.fullmatch(r"[A-Za-z0-9.+-]+", token):
            parts.append(r"\b" + re.escape(token) + r"\b")
        else:
            parts.append(re.escape(token))
    return re.compile("|".join(parts), re.IGNORECASE)


_CAT_RE = {cat: _compile(tokens) for cat, tokens in KEYWORDS.items()}


def classify_items(items: list[NewsItem]) -> None:
    for item in items:
        classify_item(item)


def classify_item(item: NewsItem) -> None:
    title = item.title or ""
    summary = (item.summary or "")[:800]
    scores = {cat: 0.0 for cat in CATEGORIES}
    for cat, regex in _CAT_RE.items():
        scores[cat] += len(regex.findall(title)) * _TITLE_WEIGHT
        scores[cat] += len(regex.findall(summary)) * _SUMMARY_WEIGHT

    best = max(CATEGORIES, key=lambda c: (scores[c], -CATEGORY_ORDER.index(c)))
    if scores[best] <= 0 and item.source:
        hint = _match_hint(item.source)
        if hint:
            best = hint
    if scores[best] <= 0:
        best = "国际局势"

    # 外文时政类新闻归入“国际局势”，军事保持独立
    if item.raw_lang == "en" and best == "时政新闻":
        best = "国际局势"

    item.category = best
    item.priority_boost = bool(PRIORITY_PATTERN.search(title))
    item.is_breaking = bool(BREAKING_PATTERN.search(title))
    hot_words = HOT_PATTERN.search(title)
    item.is_hot = bool(
        item.cover_count >= 3
        or (item.cover_count >= 2 and hot_words)
        or (item.is_breaking and hot_words)
    )
    item.score = _rank_score(item, scores[best])


def _match_hint(source_name: str) -> str:
    table = {
        "科技": "科技新闻",
        "IT之家": "科技新闻",
        "少数派": "科技新闻",
        "论文": "教育科研",
        "时政": "时政新闻",
        "财经": "财经商业",
        "文娱": "文娱体育",
        "影视": "文娱体育",
        "军事": "军事新闻",
        "民生": "社会民生",
    }
    for key, cat in table.items():
        if key in source_name:
            return cat
    return ""


def _rank_score(item: NewsItem, cat_score: float) -> float:
    score = 0.0
    score += min(3.0, item.cover_count) * 2.0      # 跨源覆盖越多越重要
    score += 3.0 if item.is_hot else 0.0
    score += 1.5 if item.is_breaking else 0.0
    score += 2.0 if item.priority_boost else 0.0   # 科技/AI/机器人/具身智能权重优先
    if item.published:
        age_hours = (datetime.now(timezone.utc) - item.published).total_seconds() / 3600
        score += 1.0 if age_hours <= 12 else 0.0   # 近 12 小时突发优先
    score += min(2.0, cat_score * 0.3)
    return round(score, 2)


def observed_categories(items: list[NewsItem]) -> dict[str, int]:
    counts = {cat: 0 for cat in CATEGORIES}
    for it in items:
        if it.category in counts:
            counts[it.category] += 1
    return counts
