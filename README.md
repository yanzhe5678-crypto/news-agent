# News-Agent 全球新闻智能体

全天候全自动全球新闻智能体开源工程：由 AI Agent 无人值守，每日自动抓取、整理、分类、归档全球权威新闻，覆盖科技、军事、时政、财经、国际局势、社会、教育、文娱全领域。

## 特点

- 全自动每日更新：定时任务每天自动运行，无需人工干预
- 全领域结构化分类：严格按八大分类归档，每条新闻只归入唯一大类
- 权威信源、去重降噪：只收录权威媒体 RSS，自动去重、滤除营销低质内容
- 永久开源、每日归档：日 / 月结构化归档，可回溯查阅
- 中立客观、纯资讯汇总：不造谣、不传谣、无主观评价

## 八大分类

科技新闻 · 军事新闻 · 时政新闻 · 财经商业 · 国际局势 · 社会民生 · 教育科研 · 文娱体育

每条新闻统一输出：标题、来源、发布时间、一句话摘要、3-6 条关键要点、影响解读、分类标签。

## 运行逻辑

1. 每日定时启动爬虫 + AI 整理流水线
2. 抓取当日全球权威新闻池
3. AI 智能分类、清洗、摘要、结构化
4. 生成当日完整新闻文档
5. 同步更新分类总归档文件
6. 自动 Commit & Push 开源仓库

## 技术栈

- Python 自动化爬虫（RSS 并发抓取）
- LLM 内容清洗、分类、摘要（可选，未配置时自动降级为本地抽取式摘要）
- GitHub Actions 每日定时任务
- Markdown 结构化自动排版
- 自动去重算法（模糊标题相似度 + 同源多报合并 + 跨源覆盖统计）

## 目录结构

```
News-Agent/
├── news_agent/                 # 核心代码
│   ├── config.py               # 配置加载
│   ├── fetch.py                # 并发抓取与 RSS 解析
│   ├── dedup.py                # 去重、低质过滤、同源合并
│   ├── classify.py             # 八大分类 + 热点/突发/权重识别
│   ├── summarize.py            # 摘要与要点（LLM / 本地抽取）
│   ├── render.py               # Markdown 日报与分类归档排版
│   └── pipeline.py             # 总调度入口
├── config.yaml                 # 信源与参数配置
├── DailyNews/YYYY-MM/          # 按月份归档的每日汇总
├── Category/                   # 八大分类的历史归档
├── .github/workflows/daily.yml # 每日自动运行与自动推送
└── README.md
```

## 本地运行

```bash
pip install -r requirements.txt

# 直接跑（默认今天的新闻）
python -m news_agent.pipeline

# 指定日期 / 限制条数 / 强制本地摘要
python -m news_agent.pipeline --date 2026-09-03 --limit 80 --no-llm

# 查看详细日志
python -m news_agent.pipeline --verbose
```

## 使用 LLM 增强（可选，推荐）

未配置 LLM 时使用本地抽取式摘要（保留原文句式）；配置后会自动生成更通顺的中文一句话摘要、要点、影响解读，并把外文新闻整理为中文通顺版本。

支持 OpenAI 格式的兼容端点（OpenAI / DeepSeek / 智谱 / Kimi 等），通过环境变量配置：

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"   # 可选，默认 OpenAI
export NEWS_AGENT_MODEL="deepseek-chat"                 # 可选，默认 gpt-4o-mini
```

GitHub Actions 中在仓库 Settings → Secrets 配置 `OPENAI_API_KEY`（可选 `OPENAI_BASE_URL`），Variables 配置 `NEWS_AGENT_MODEL` 即可。

## 自动更新（GitHub Actions）

`.github/workflows/daily.yml` 每天 01:30 UTC（北京时间 09:30）自动运行：

1. 抓取当日全球新闻
2. 去重、分类、摘要、排版
3. 更新 `DailyNews/` 日报与 `Category/` 分类归档
4. 自动提交并推送（无变更时自动跳过提交）

将本仓库推到 GitHub 即可启用，无需服务器；如需调整运行时间，修改 workflow 中的 `cron` 表达式。

## 信源维护

所有信源都在 `config.yaml` 的 `sources` 段。单个信源失败会被自动跳过，不影响整体流程；可在不同网络环境下按需增删（部分国际源在国内网络下可能超时，GitHub 官方服务器上通常正常）。

## 免责声明

本项目仅做权威媒体公开信息的自动化汇总与档案整理，立场中立、无主观评价，不构成新闻发布或投资建议。内容版权归原信源所有，如涉侵权请联系仓库维护者删除。涉及的内容以源站为准，请勿将本项目用于传播不实信息。
