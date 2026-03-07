#!/usr/bin/env python3
# AI圈情报流 - 聚焦 LLM / Agent / Framework / 应用 / 硬件 / 开源信号

import json
import re
import ssl
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWSAPI_KEY = "5d55afcb7f0045e99f702286f4f3eec7"
TARGET = "1468126140404072584"
SAVE_DIR = Path("/Users/jappre/.openclaw/workspace/memory/ai_news")

RSS_FEEDS = [
    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "kind": "rss"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "kind": "rss"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "kind": "rss"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "kind": "rss"},
    {"name": "InfoQ AI/ML", "url": "https://www.infoq.com/feed/ai-ml-data-eng/", "kind": "rss"},
    {"name": "HN agent", "url": "https://hnrss.org/frontpage?q=agent", "kind": "hn"},
    {"name": "HN Claude Code", "url": "https://hnrss.org/newest?q=Claude+Code", "kind": "hn"},
    {"name": "HN browser automation", "url": "https://hnrss.org/newest?q=browser+automation", "kind": "hn"},
    {"name": "HN AI hardware", "url": "https://hnrss.org/newest?q=AI+hardware", "kind": "hn"},
    {"name": "HN MCP", "url": "https://hnrss.org/newest?q=MCP", "kind": "hn"},
]

NEWSAPI_QUERIES = [
    {
        "source": "NewsAPI-models",
        "query": '("LLM" OR "large language model" OR GPT OR Claude OR Gemini OR Kimi OR Qwen OR DeepSeek OR Mistral) AND (release OR launch OR API OR benchmark OR reasoning OR multimodal OR pricing)'
    },
    {
        "source": "NewsAPI-frameworks",
        "query": '("agent framework" OR "AI agent" OR "tool use" OR MCP OR RAG OR LangChain OR LlamaIndex OR DSPy OR OpenHands OR OpenClaw OR browser automation OR coding agent)'
    },
    {
        "source": "NewsAPI-apps-hardware",
        "query": '("AI app" OR "AI assistant" OR "voice agent" OR "AI workflow" OR "desktop agent" OR "AI hardware" OR "AI device" OR "AI glasses" OR "AI earbuds" OR "AI phone")'
    }
]

CATEGORY_RULES = {
    "模型": ["llm", "large language model", "gpt", "claude", "gemini", "kimi", "qwen", "deepseek", "mistral", "reasoning model", "multimodal"],
    "框架/Agent": ["agent", "agent framework", "mcp", "tool use", "browser automation", "coding agent", "openclaw", "langchain", "llamaindex", "dspy", "openhands", "rag"],
    "应用": ["ai app", "assistant", "workflow", "voice agent", "personal ai", "desktop agent", "browser agent"],
    "硬件": ["ai hardware", "device", "glasses", "earbuds", "phone", "chip", "on-device", "edge inference", "wearable"],
}

BLOCKLIST = [
    'stock', 'shares', 'market cap', 'etf', 'nasdaq', 'seeking alpha', 'motley fool',
    'price target', 'earnings', 'sponsored', 'advertisement', 'buy rating'
]

PREFERRED_SOURCE_PATTERNS = [
    'github', 'hugging face', 'techcrunch', 'the verge', 'infoq', 'hacker news',
    'openai', 'anthropic', 'google', 'meta', 'mistral', 'moonshot'
]

HIGH_SIGNAL_TERMS = [
    'openclaw', 'mcp', 'claude code', 'browser automation', 'tool use', 'reasoning',
    'multimodal', 'open source', 'release', 'launch', 'benchmark', 'agent'
]


def fetch_url(url, timeout=20):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='ignore')


def parse_rss_datetime(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        cleaned = value.replace('Z', '+00:00')
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def clean_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_feed(feed_name, xml_text):
    items = []
    root = ET.fromstring(xml_text)

    channel_items = root.findall('.//channel/item')
    atom_entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')

    if channel_items:
        for item in channel_items:
            title = item.findtext('title') or ''
            link = item.findtext('link') or ''
            desc = item.findtext('description') or item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or ''
            published = item.findtext('pubDate') or ''
            items.append({
                'title': clean_html(title),
                'url': link.strip(),
                'description': clean_html(desc),
                'publishedAt': published.strip(),
                'source': feed_name,
            })
    elif atom_entries:
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in atom_entries:
            title = entry.findtext('atom:title', namespaces=ns) or ''
            link_el = entry.find('atom:link', ns)
            link = link_el.attrib.get('href', '') if link_el is not None else ''
            desc = entry.findtext('atom:summary', namespaces=ns) or entry.findtext('atom:content', namespaces=ns) or ''
            published = entry.findtext('atom:updated', namespaces=ns) or entry.findtext('atom:published', namespaces=ns) or ''
            items.append({
                'title': clean_html(title),
                'url': link.strip(),
                'description': clean_html(desc),
                'publishedAt': published.strip(),
                'source': feed_name,
            })
    return items


def fetch_newsapi(query, from_date):
    params = {
        'q': query,
        'from': from_date,
        'sortBy': 'publishedAt',
        'language': 'en',
        'pageSize': 8,
        'apiKey': NEWSAPI_KEY,
    }
    url = 'https://newsapi.org/v2/everything?' + urllib.parse.urlencode(params)
    raw = fetch_url(url, timeout=30)
    data = json.loads(raw)
    if data.get('status') != 'ok':
        return []
    result = []
    for article in data.get('articles', []):
        result.append({
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'description': article.get('description', ''),
            'publishedAt': article.get('publishedAt', ''),
            'source': article.get('source', {}).get('name', 'NewsAPI'),
        })
    return result


def normalize_text(*parts):
    return ' '.join((p or '') for p in parts).lower()


def is_blocked(article):
    text = normalize_text(article.get('title'), article.get('description'), article.get('source'))
    return any(word in text for word in BLOCKLIST)


def detect_category(article):
    text = normalize_text(article.get('title'), article.get('description'))
    best_category = '应用'
    best_score = -1
    for category, keywords in CATEGORY_RULES.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def score_article(article):
    text = normalize_text(article.get('title'), article.get('description'))
    source = (article.get('source') or '').lower()
    score = 0

    score += sum(4 for term in HIGH_SIGNAL_TERMS if term in text)
    score += sum(2 for pat in PREFERRED_SOURCE_PATTERNS if pat in source)

    if any(w in text for w in ['release', 'launch', 'announc', 'introduc', 'open source', 'github', 'benchmark', 'api']):
        score += 3
    if 'openclaw' in text:
        score += 8
    if 'claude code' in text or 'mcp' in text:
        score += 6
    if 'ai hardware' in text or 'earbuds' in text or 'glasses' in text:
        score += 4

    published = parse_rss_datetime(article.get('publishedAt', ''))
    if published:
        age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        if age_hours < 24:
            score += 3
        elif age_hours < 72:
            score += 1

    return score


def dedupe_articles(items):
    seen = set()
    result = []
    for item in items:
        title = (item.get('title') or '').strip().lower()
        url = (item.get('url') or '').strip().lower()
        key = title or url
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_all_articles(since_date):
    all_items = []

    for feed in RSS_FEEDS:
        try:
            xml_text = fetch_url(feed['url'])
            items = parse_feed(feed['name'], xml_text)
            all_items.extend(items)
        except Exception:
            continue

    for item in NEWSAPI_QUERIES:
        try:
            all_items.extend(fetch_newsapi(item['query'], since_date))
        except Exception:
            continue

    return dedupe_articles([a for a in all_items if not is_blocked(a)])


def group_articles(all_items):
    grouped = {k: [] for k in CATEGORY_RULES.keys()}
    for item in all_items:
        category = detect_category(item)
        grouped[category].append(item)

    for category in grouped:
        grouped[category] = sorted(grouped[category], key=score_article, reverse=True)[:3]
    return grouped


def build_message(grouped, today, since_date):
    lines = [
        f"🤖 **AI 圈情报流** ({today})",
        f"覆盖 {since_date} 以来的模型、框架、应用、硬件与开源信号",
        "不是泛新闻，尽量只留值得看的东西。",
        ""
    ]
    order = ['模型', '框架/Agent', '应用', '硬件']
    for category in order:
        articles = grouped.get(category, [])
        if not articles:
            continue
        lines.append(f"**{category}**")
        for article in articles:
            title = article.get('title', '无标题').strip()
            source = article.get('source', '未知来源')
            desc = (article.get('description') or '').strip()
            url = article.get('url', '')
            if len(desc) > 85:
                desc = desc[:85] + '...'
            lines.append(f"- **{title}**")
            lines.append(f"  来源: {source}")
            if desc:
                lines.append(f"  摘要: {desc}")
            if url:
                lines.append(f"  链接: <{url}>")
        lines.append("")
    lines.append("---")
    lines.append("⏰ 每天早晨8:30自动推送 | 小C 🤖")
    return '\n'.join(lines)


def save_markdown(grouped, today, since_date):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    save_file = SAVE_DIR / f"{today}.md"
    parts = [
        f"# AI圈情报流 - {today}\n",
        f"**日期**: {today}  ",
        f"**时间范围**: 自 {since_date} 起  ",
        f"**信号类型**: 模型 / 框架Agent / 应用 / 硬件 / 开源\n",
        "---\n"
    ]
    for category in ['模型', '框架/Agent', '应用', '硬件']:
        parts.append(f"## {category}\n")
        articles = grouped.get(category, [])
        if not articles:
            parts.append("- 暂无高价值信号\n")
            continue
        for idx, article in enumerate(articles, 1):
            parts.append(f"### {idx}. {article.get('title', '无标题')}\n")
            parts.append(f"- **来源**: {article.get('source', '未知来源')}\n")
            parts.append(f"- **发布时间**: {article.get('publishedAt', '')}\n")
            parts.append(f"- **链接**: {article.get('url', '')}\n")
            parts.append(f"- **摘要**: {article.get('description', '')}\n\n")
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
    all_items = collect_all_articles(since_date)
    grouped = group_articles(all_items)
    message = build_message(grouped, today, since_date)
    save_markdown(grouped, today, since_date)
    send_message(message)


if __name__ == '__main__':
    main()
