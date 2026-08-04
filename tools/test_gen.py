#!/usr/bin/env python3
import json, os, urllib.request

api_key = os.environ["DEEPSEEK_API_KEY"]
clause_dir = os.path.expanduser("~/Documents/nanning-gjj-rag/data/clauses")
titles = []
for f in sorted(os.listdir(clause_dir)):
    if f.endswith(".json"):
        with open(os.path.join(clause_dir, f)) as fp:
            d = json.load(fp)
        titles.append(d["doc_title"])

policy_list = "\n".join("- " + t[:80] for t in titles)

PROMPT = f"""你是南宁住房公积金政策专家。基于以下35篇政策文档的名称，生成28题测试集。

政策文档:
{policy_list}

要求:
1. 条件查询类 7题
2. 材料准备类 7题
3. 流程指引类 7题  
4. 金额计算类 7题
其中混入3道陷阱题(不存在的场景)，标记trap=true。
每题包含标准答案。

输出JSON: {{"questions":[{{"id":1,"category":"条件查询","trap":false,"question":"...","expected_answer":"..."}}]}}"""

payload = json.dumps({
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": PROMPT}],
    "temperature": 0.3, "max_tokens": 16384,
    "response_format": {"type": "json_object"}
}).encode()

req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions",
    data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})

with urllib.request.urlopen(req, timeout=180) as resp:
    content = json.loads(resp.read())["choices"][0]["message"]["content"]

out = os.path.expanduser("~/Documents/nanning-gjj-rag/data/test_set.json")
parsed = json.loads(content)
with open(out, "w") as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)

qs = parsed["questions"]
cats = {}
traps = 0
for q in qs:
    cats[q["category"]] = cats.get(q["category"], 0) + 1
    if q.get("trap"): traps += 1

print(f"Generated {len(qs)} questions ({traps} traps)")
for c, n in sorted(cats.items()):
    print(f"  {c}: {n}")
print(f"Saved: {out}")
for q in qs[:5]:
    tag = "[TRAP] " if q.get("trap") else ""
    print(f"  [{q['category']}] {tag}{q['question'][:60]}")
