from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

CATEGORIES = [
    "科技新闻",
    "军事新闻",
    "时政新闻",
    "财经商业",
    "国际局势",
    "社会民生",
    "教育科研",
    "文娱体育",
]

# 分类展示顺序：科技/AI 优先，符合“科技权重优先收录”的要求
CATEGORY_ORDER = [
    "科技新闻",
    "军事新闻",
    "时政新闻",
    "财经商业",
    "国际局势",
    "社会民生",
    "教育科研",
    "文娱体育",
]


@dataclass
class NewsItem:
    title: str
    source: str
    link: str = ""
    published: datetime | None = None
    summary: str = ""
    content: str = ""
    raw_lang: str = "zh"
    category: str = ""
    one_line: str = ""
    key_points: list = field(default_factory=list)
    impact: str = ""
    is_hot: bool = False
    is_breaking: bool = False
    priority_boost: bool = False
    score: float = 0.0
    cover_count: int = 1
    norm_title: str = ""

    def date_str(self) -> str:
        return self.published.strftime("%Y-%m-%d") if self.published else ""
