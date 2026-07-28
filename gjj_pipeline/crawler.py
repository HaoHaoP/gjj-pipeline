"""HTML爬虫 + BeautifulSoup清洗 + markdownify转MD"""
import subprocess, re, json, os, time
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
    for tag in soup.select('script,style,noscript,meta,header,footer,nav,img,iframe,.header,.footer,.nav_side,.sj_side,.clear,.apph,.fj,.downfile,.insertfileTag'):
        tag.decompose()
    for a in soup.select('a'):
        t = a.get_text(strip=True)
        if '政策解读' in t or (a.get('href','') or '').endswith('.pdf') or a.get('download'):
            a.decompose()
    content = (soup.select_one('.trs_editor_view') or soup.select_one('#UCAP-CONTENT') or
               soup.select_one('.article-content') or soup.select_one('.content'))
    if not content: return html
    for p in content.find_all(['p','div']):
        if not p.get_text(strip=True): p.decompose()
    markdown = md(str(content), heading_style='ATX', strip=None)
    return re.sub(r'\n{3,}', '\n\n', markdown).strip()

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

def run_crawl(progress_callback=None):
    articles = parse_list_page()
    print(f"找到 {len(articles)} 篇\n")
    for i, a in enumerate(articles):
        if progress_callback:
            progress_callback((i + 1) * 100 // len(articles))
        print(f"  [{i+1}/{len(articles)}] {a['id']} ...", end=' ', flush=True)
        try:
            raw = fetch(a['url'])
            text = clean_html(raw)
            with open(os.path.join(DATA_DIR, f"{a['id']}.md"), 'w') as f: f.write(text)
            with open(os.path.join(CLEANED_DIR, f"{a['id']}.md"), 'w') as f: f.write(text)
            a['text_length'] = len(text)
            print(f"OK ({len(text)} 字)")
        except Exception as e:
            print(f"FAIL: {e}")
            a['text_length'] = 0
        time.sleep(0.5)
    with open(os.path.join(DATA_DIR, "metadata.json"), 'w') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    total = sum(a.get('text_length',0) for a in articles)
    print(f"\n完成: {len(articles)} 篇, {total} 字")
    return {"success": True, "count": len(articles), "total_chars": total}

if __name__ == "__main__":
    run_crawl()
