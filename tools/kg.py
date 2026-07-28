#!/usr/bin/env python3
"""Phase 2: 从767条条款中提取政策间引用关系"""
import json, os, time, urllib.request
from json import JSONDecoder

api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    print("ERROR: Set DEEPSEEK_API_KEY")
    exit(1)

CLAUSE_DIR = os.path.expanduser("~/Documents/nanning-gjj-rag/data/clauses")
OUT_FILE = os.path.expanduser("~/Documents/nanning-gjj-rag/data/kg_relations.json")

# 读取所有文档的条款，按文档分组
docs = {}
for fname in sorted(os.listdir(CLAUSE_DIR)):
    if not fname.endswith('.json'): continue
    with open(os.path.join(CLAUSE_DIR, fname)) as f:
        data = json.load(f)
    doc_id = data['doc_id']
    docs[doc_id] = {
        'title': data['doc_title'],
        'clauses': [{'num': c['clause_number'], 'text': c['text']} for c in data['clauses']]
    }

PROMPT = """你是法律政策文档分析专家。分析以下条款文本，找出其中的引用关系。

引用类型：
- REFERENCES: A条款引用了B政策/条款作为依据
- REVISES: A条款修改了B条款
- ABOLISHES: A条款废止了B条款

输出JSON格式（仅JSON）：
{
  "relations": [
    {
      "from_clause": "当前条款号",
      "from_text": "当前条款文本摘要",
      "relation": "REFERENCES|REVISES|ABOLISHES",
      "to_document": "被引用的政策文档名称",
      "to_clause": "被引用的条款号（如有，否则null）"
    }
  ]
}

只提取明确的引用关系，不要推测。如果条款文本中没有引用其他政策，返回空的relations数组。"""


def extract_relations(clauses, doc_title):
    """提取一个文档内所有条款的引用关系"""
    # Build context - show clause numbers and text
    context = f"文档: {doc_title}\n\n"
    for c in clauses:
        context += f"[{c['num']}] {c['text'][:500]}\n\n"
    
    # Truncate
    if len(context) > 20000:
        context = context[:20000]
    
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': PROMPT},
            {'role': 'user', 'content': context}
        ],
        'temperature': 0.1,
        'max_tokens': 8192,
        'response_format': {'type': 'json_object'}
    }).encode()
    
    req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions',
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'})
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                content = json.loads(resp.read())['choices'][0]['message']['content']
                try: return json.loads(content)
                except: 
                    data, _ = JSONDecoder().raw_decode(content)
                    return data
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"  FAIL: {e}")
                return {'relations': []}

# ═══ MAIN ═══
print(f"Phase 2: KG引用关系提取 - {len(docs)} 篇文档\n")

all_relations = []
for i, (doc_id, doc) in enumerate(docs.items()):
    print(f"[{i+1}/{len(docs)}] {doc['title'][:50]} ...", end=' ', flush=True)
    
    result = extract_relations(doc['clauses'], doc['title'])
    rels = result.get('relations', [])
    
    for r in rels:
        r['from_doc_id'] = doc_id
        r['from_doc_title'] = doc['title']
    
    all_relations.extend(rels)
    print(f"OK ({len(rels)} relations)")
    time.sleep(1)

# Save
with open(OUT_FILE, 'w') as f:
    json.dump({'relations': all_relations}, f, ensure_ascii=False, indent=2)

print(f"\n完成: {len(all_relations)} 条引用关系")
print(f"输出: {OUT_FILE}")
