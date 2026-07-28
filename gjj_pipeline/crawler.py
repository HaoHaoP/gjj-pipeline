"""HTML爬虫 + BeautifulSoup清洗 + markdownify转MD"""
import subprocess, re, json, os, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE = "https://gjj.nanning.gov.cn/xxgk/zcwjcx/"
DATA_DIR = os.path.expanduser("~/Documents/nanning-gjj-rag/data/policies")
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")
os.makedirs(CLEANED_DIR, exist_ok=True)

def fetch(url):
    r = subprocess.run(['curl','-s','-L','--max-time','15',
        '-H','User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        url], capture_output=True, text=True)
    return r.stdout

def clean_html(html):
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.select('script,style,noscript,meta,header,footer,nav,img,iframe,'
                           '.header,.footer,.nav_side,.sj_side,.clear,.apph,.fj,.downfile'):
        tag.decompose()
    # 只移除 "相关政策解读" 文本链接，保留文件名链接
    for a in soup.select('a'):
        t = a.get_text(strip=True)
        if '政策解读' in t:
            a.decompose()
    content = (soup.select_one('.trs_editor_view') or soup.select_one('#UCAP-CONTENT') or
               soup.select_one('.article-content') or soup.select_one('.content'))
    if not content:
        content = soup.body or soup
    for p in content.find_all(['p','div']):
        if not p.get_text(strip=True): p.decompose()
    markdown = md(str(content), heading_style='ATX', strip=None)
    markdown = re.sub(r'\n{3,}', '\n\n', markdown).strip()
    # 兜底：如果结果太短，用整个 body
    if len(markdown) < 50 and soup.body:
        body_md = md(str(soup.body), heading_style='ATX', strip=None)
        markdown = re.sub(r'\n{3,}', '\n\n', body_md).strip()
    return markdown

def parse_list_page():
    html = fetch(BASE)
    pat = r'<a[^>]*href=["\'](?:\./|https://gjj\.nanning\.gov\.cn/xxgk/zcwjcx/)?(t\d+\.html)["\'][^>]*>([^<]+)</a>'
    matches = re.findall(pat, html)
    dates = re.findall(r'发布时间：(\d{4}-\d{2}-\d{2})', html)
    articles, seen = [], set()
    for i, (url_id, title) in enumerate(matches):
        if url_id in seen: continue
        seen.add(url_id)
        articles.append({"id": url_id.replace('.html',''), "url": BASE + url_id, "title": title.strip(), "date": dates[i] if i < len(dates) else ""})
    return articles

def _crawl_one(a):
    """Fetch + clean + save one document (runs in thread pool)"""
    try:
        raw = fetch(a['url'])
        text = clean_html(raw)
        with open(os.path.join(DATA_DIR, f"{a['id']}.md"), 'w') as f: f.write(text)
        with open(os.path.join(CLEANED_DIR, f"{a['id']}.md"), 'w') as f: f.write(text)
        a['text_length'] = len(text)
        return len(text)
    except Exception as e:
        return 0

def run_crawl(progress_callback=None):
    articles = parse_list_page()
    print(f"找到 {len(articles)} 篇\n")
    total = len(articles)
    completed = 0
    
    def _on_done(fut):
        nonlocal completed
        completed += 1
        if progress_callback:
            progress_callback(completed * 100 // total)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures_map = {}
        for a in articles:
            f = executor.submit(_crawl_one, a)
            futures_map[f] = a
            f.add_done_callback(_on_done)
        
        for future in as_completed(futures_map):
            a = futures_map[future]
            chars = future.result()
            print(f"  [{completed}/{total}] {a['id']} ... {'OK' if chars else 'FAIL'} ({chars} 字)")
    
    with open(os.path.join(DATA_DIR, "metadata.json"), 'w') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    total_chars = sum(a.get('text_length', 0) for a in articles)
    print(f"\n完成: {total} 篇, {total_chars} 字")
    return {"success": True, "count": total, "total_chars": total_chars}

if __name__ == "__main__":
    run_crawl()
