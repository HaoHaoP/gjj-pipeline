"""HTML爬虫 + BeautifulSoup清洗 — 输出清洗后 HTML 片段供 LLM 使用"""
import re, os, hashlib, logging
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from gjj_pipeline.storage import exists
from gjj_pipeline.config import CRAWL_BASE_URL

logger = logging.getLogger(__name__)

_session = requests.Session()
_retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=10, pool_maxsize=10)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)
_session.headers["User-Agent"] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")


def fetch(url):
    r = _session.get(url, timeout=15)
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def clean_html(html):
    """清洗 HTML，保留正文内容和表格，返回 HTML 片段字符串"""
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.select('script,style,noscript,meta,header,footer,nav,img,iframe,'
                           '.header,.footer,.nav_side,.sj_side,.clear,.apph,.fj,.downfile'):
        tag.decompose()
    for a in soup.select('a'):
        t = a.get_text(strip=True)
        if '政策解读' in t:
            a.decompose()
    content = (soup.select_one('.trs_editor_view') or soup.select_one('#UCAP-CONTENT') or
               soup.select_one('.article-content') or soup.select_one('.content'))
    if not content:
        content = soup.body or soup
    for p in content.find_all(['p', 'div']):
        if not p.get_text(strip=True):
            p.decompose()
    cleaned = str(content)
    # Replace all em/en space entity variants (named, hex, decimal) with regular space
    cleaned = re.sub(r'&emsp;|&#x2003;|&#8195;|&ensp;|&#x2002;|&#8194;', ' ', cleaned, flags=re.IGNORECASE)
    # Collapse multiple spaces into one (common in Chinese gov docs: &emsp;&emsp; for indent)
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    return cleaned


def parse_list_page():
    html = fetch(CRAWL_BASE_URL)
    pat = r'<a[^>]*href=["\'](?:\./|https://gjj\.nanning\.gov\.cn/xxgk/zcwjcx/)?(t\d+\.html)["\'][^>]*>([^<]+)</a>'
    matches = re.findall(pat, html)
    dates = re.findall(r'发布时间：(\d{4}-\d{2}-\d{2})', html)
    articles, seen = [], set()
    for i, (url_id, title) in enumerate(matches):
        if url_id in seen:
            continue
        seen.add(url_id)
        articles.append({
            "id": url_id.replace('.html', ''),
            "url": CRAWL_BASE_URL + url_id,
            "title": title.strip(),
            "date": dates[i] if i < len(dates) else "",
        })
    return articles


def _crawl_one(a):
    """Fetch + clean. Skip if structured MD already in MinIO. Text passed via a['raw_text']."""
    doc_id = hashlib.md5(a["title"].encode()).hexdigest()[:8]
    minio_path = f"{doc_id}/{a['title']}.md"
    if exists(minio_path):
        a['crawl_status'] = 'skipped'
        a['minio_path'] = minio_path
        a['doc_id'] = doc_id
        logger.info("crawl skip (already in MinIO) doc_id=%s title=%s", doc_id, a["title"][:40])
        return 0
    try:
        logger.info("crawl fetching doc_id=%s id=%s", doc_id, a["id"])
        raw = fetch(a['url'])
        text = clean_html(raw)
        if len(raw) >= 100:
            a['crawl_status'] = 'crawled'
            a['raw_text'] = text
            a['minio_path'] = minio_path
            a['doc_id'] = doc_id
            logger.info("crawl ok doc_id=%s raw=%d cleaned=%d bytes", doc_id, len(raw), len(text))
            return len(text)
        else:
            a['crawl_status'] = 'failed'
            logger.warning("crawl %s returned short content (%d bytes)", a['id'], len(raw))
            a['minio_path'] = minio_path
            a['doc_id'] = doc_id
            return 0
    except Exception as e:
        a['crawl_status'] = 'failed'
        logger.warning("crawl fail doc_id=%s id=%s: %s", doc_id, a['id'], e)
        return 0
