#!/usr/bin/env python3
# AI情报推送 - 面向 LLM / Agent / Framework / 应用 / 硬件 / 开源

import json
import ssl
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

NEWSAPI_KEY = "5d55afcb7f0045e99f702286f4f3eec7"
TARGET = "1468126140404072584"
SAVE_DIR = Path("/Users/jappre/.openclaw/workspace/memory/ai_news")

QUERIES = [
    {
        "name": "模型",
        "query": '("LLM" OR "large language model" OR GPT OR Claude OR Gemini OR Kimi OR Qwen OR DeepSeek OR Mistral) AND (release OR launch OR API OR benchmark OR reasoning OR multimodal OR pricing)'
    },
    {
        "name": "框架/Agent",
        "query": '("agent framework" OR "AI agent" OR "tool use" OR MCP OR RAG OR LangChain OR LlamaIndex OR DSPy OR OpenHands OR OpenClaw OR browser automation OR coding agent)'
    },
    {
        "name": "应用",
        "query": '("AI app" OR "AI assistant" OR "voice agent" OR "personal AI" OR "AI workflow" OR "AI browser" OR "desktop agent")'
    },
    {
        "name": "硬件",
        "query": '("AI hardware" OR "AI device" OR "AI glasses" OR "AI earbuds" OR "AI phone" OR "on-device AI" OR "edge inference")'
    }
]

BLOCKLIST = [
    'stock', 'shares', 'market cap', 'etf', 'nasdaq', 'seeking alpha', 'motley fool',
    'price target', 'earnings call', 'advertisement', 'sponsored'
]

PREFERRED_SOURCES = [
    'TechCrunch', 'The Verge', 'Ars Technica', 'VentureBeat', 'GitHub Blog',
    'Hugging Face', 'OpenAI', 'Anthropic', 'Google', 'Meta', 'InfoQ'
]


def fetch_news(query, from_date, page_size=8):
    params = {
        'q': query,
        'from': from_date,
        'sortBy': 'publishedAt',
        'language': 'en',
        'pageSize': page_size,
        'apiKey': NEWSAPI_KEY,
    }
    url = 'https://newsapi.org/v2/everything?' + urllib.parse.urlencode(params)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def normalize_text(*parts):
    return ' '.join([(p or '') for p in parts]).lower()


def is_blocked(article):
    text = normalize_text(article.get('title'), article.get('description'), article.get('source', {}).get('name'))
    return any(word in text for word in BLOCKLIST)


def score_article(article, category_name):
    text = normalize_text(article.get('title'), article.get('description'))
    source = article.get('source', {}).get('name', '')
    score = 0

    if source in PREFERRED_SOURCES:
        score += 3
    if category_name == '框架/Agent' and any(k in text for k in ['openclaw', 'agent', 'mcp', 'tool use', 'browser automation', 'openhands', 'langchain', 'llamaindex', 'dspy']):
        score += 4
    if category_name == '模型' and any(k in text for k in ['claude', 'gpt', 'gemini', 'kimi', 'qwen', 'deepseek', 'mistral']):
        score += 4
    if category_name == '应用' and any(k in text for k in ['assistant', 'workflow', 'voice', 'browser', 'desktop agent']):
        score += 3
    if category_name == '硬件' and any(k in text for k in ['device', 'glasses', 'earbuds', 'phone', 'chip', 'edge']):
        score += 3
    if any(k in text for k in ['launch', 'release', 'announce', 'introduce', 'new', 'open source', 'github']):
        score += 2
    return score


def dedupe_articles(items):
    seen = set()
    result = []
    for item in items:
        title = (item.get('title') or '').strip().lower()
        if not title or title in seen:
            continue
        seen.add(title)
        result.append(item)
    return result


def pick_top_articles(raw_articles, category_name, limit=2):
    filtered = [a for a in raw_articles if not is_blocked(a)]
    filtered = dedupe_articles(filtered)
    ranked = sorted(filtered, key=lambda a: score_article(a, category_name), reverse=True)
    return ranked[:limit]


def format_bullet(article):
    title = article.get('title', '无标题').strip()
    source = article.get('source', {}).get('name', '未知来源')
    desc = (article.get('description') or '').strip()
    url = article.get('url', '')
    if len(desc) > 90:
        desc = desc[:90] + '...'
    lines = [f"- **{title}**", f"  来源: {source}"]
    if desc:
        lines.append(f"  摘要: {desc}")
    if url:
        lines.append(f"  链接: <{url}>")
    return '\n'.join(lines)


def build_message(collected, today, since_date):
    sections = [f"🤖 **AI 情报简报** ({today})", f"聚焦 {since_date} 以来值得看的 LLM / 框架 / 应用 / 硬件 / 开源信号\n"]
    for category_name, articles in collected:
        if not articles:
            continue
        sections.append(f"**{category_name}**")
        for article in articles:
            sections.append(format_bullet(article))
        sections.append("")
    sections.append("---\n⏰ 每天早晨8:30自动推送 | 小C 🤖")
    return '\n'.join(sections)


def save_markdown(collected, today, since_date):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    save_file = SAVE_DIR / f"{today}.md"
    parts = [
        f"# AI情报简报 - {today}\n",
        f"**日期**: {today}  ",
        f"**时间范围**: 自 {since_date} 起  ",
        f"**信号类型**: 模型 / Agent框架 / 应用 / 硬件\n",
        "---\n"
    ]
    for category_name, articles in collected:
        parts.append(f"## {category_name}\n")
        if not articles:
            parts.append("- 暂无高价值信号\n")
            continue
        for idx, article in enumerate(articles, 1):
            parts.append(f"### {idx}. {article.get('title', '无标题')}\n")
            parts.append(f"- **来源**: {article.get('source', {}).get('name', '未知来源')}\n")
            parts.append(f"- **发布时间**: {article.get('publishedAt', '')}\n")
            parts.append(f"- **链接**: {article.get('url', '')}\n")
            parts.append(f"- **摘要**: {article.get('description', '')}\n")
            parts.append("\n")
    parts.append(f"---\n*记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    save_file.write_text('\n'.join(parts), encoding='utf-8')


def send_message(message):
    subprocess.run([
        '/opt/homebrew/bin/openclaw', 'message', 'send',
        '-m', message,
        '--channel=discord',
        f'--target={TARGET}'
    ], check=False)


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    since_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

    collected = []
    for item in QUERIES:
        try:
            data = fetch_news(item['query'], since_date)
            articles = data.get('articles', []) if data.get('status') == 'ok' else []
            top_articles = pick_top_articles(articles, item['name'], limit=2)
            collected.append((item['name'], top_articles))
        except Exception as e:
            collected.append((item['name'], []))

    message = build_message(collected, today, since_date)
    save_markdown(collected, today, since_date)
    send_message(message)


if __name__ == '__main__':
    main()
