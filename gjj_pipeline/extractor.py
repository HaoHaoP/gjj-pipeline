"""DeepSeek LLM 条款提取 + 保存 clauses JSON"""
import json, os, time, urllib.request

DATA_DIR = os.path.expanduser("~/Documents/nanning-gjj-rag/data")
POLICY_DIR = os.path.join(DATA_DIR, "policies")
CLAUSE_DIR = os.path.join(DATA_DIR, "clauses")
os.makedirs(CLAUSE_DIR, exist_ok=True)

def call_deepseek(prompt, max_tokens=8192):
    api_key = os.environ["DEEPSEEK_API_KEY"]
    data = json.dumps({"model":"deepseek-chat","messages":[{"role":"user","content":prompt}],
        "max_tokens":max_tokens,"temperature":0.2}).encode()
    req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions", data,
        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def extract_clauses(text, title):
    prompt = f"""你是政策文档解析专家。请将以下南宁住房公积金政策文档拆分为条款列表。
返回 JSON 格式: {{"clauses":[{{"clause_number":"第一条","text":"..."}},...]}}
只输出 JSON，不输出其他内容。

文档标题: {title}
文档内容:
{text}"""
    for attempt in range(3):
        try:
            result = call_deepseek(prompt)
            data = json.loads(result)
            if "clauses" in data: return data
        except Exception as e:
            if attempt == 2: raise
            time.sleep(2)
    return {"clauses": []}

def run_extract(progress_callback=None):
    metadata = json.load(open(os.path.join(POLICY_DIR, "metadata.json")))
    total = len(metadata)
    all_clauses = 0
    for i, a in enumerate(metadata):
        if progress_callback:
            progress_callback((i + 1) * 100 // total)
        doc_id = a["id"]
        print(f"  [{i+1}/{total}] {doc_id} ...", end=' ', flush=True)
        try:
            md_path = os.path.join(POLICY_DIR, f"{doc_id}.md")
            if not os.path.exists(md_path): continue
            text = open(md_path).read()
            if len(text) < 50: continue
            result = extract_clauses(text, a["title"])
            result["doc_title"] = a["title"]
            result["url"] = a.get("url", "")
            out_path = os.path.join(CLAUSE_DIR, f"{doc_id}.json")
            json.dump(result, open(out_path, 'w'), ensure_ascii=False, indent=2)
            count = len(result.get("clauses", []))
            all_clauses += count
            print(f"OK ({count} 条)")
        except Exception as e:
            print(f"FAIL: {e}")
        time.sleep(0.5)
    print(f"\n完成: {total} 篇, {all_clauses} 条条款")
    return {"success": True, "count": total, "total_clauses": all_clauses}

if __name__ == "__main__":
    run_extract()
