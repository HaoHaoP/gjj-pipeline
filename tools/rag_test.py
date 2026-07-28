#!/usr/bin/env python3
import json, urllib.request, base64, os

MILVUS_API = "http://localhost:8080/api/rag/query"
NEO4J_URL = "http://localhost:7474"
NEO_U = "neo4j"
NEO_P = "gjj123456"
api_key = os.environ.get("DEEPSEEK_API_KEY")

def cypher(query):
    p = json.dumps({"statements": [{"statement": query}]})
    c = base64.b64encode(f"{NEO_U}:{NEO_P}".encode()).decode()
    r = urllib.request.Request(NEO4J_URL + "/db/neo4j/tx/commit", data=p.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Basic " + c})
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read())

test_qs = [
    "商转公贷款需要满足什么条件？",
    "2025年南宁公积金缴存基数上限是多少？",
    "高层次人才公积金贷款有什么优惠？",
]

for q in test_qs:
    print(f"\n{'='*50}\nQ: {q}")
    req = urllib.request.Request(MILVUS_API, data=json.dumps({"question": q}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    answer = result.get('answer', result.get('error', 'no answer'))
    print(f"A: {answer[:400]}")
    for s in result.get('sources', [])[:3]:
        t = s.get('title', '')[:30]
        try:
            r = cypher('MATCH (p:Policy) WHERE p.title CONTAINS "' + t + '" MATCH (p)-[:CONTAINS]->(c:Clause)-[r]->(tp) RETURN c.number, type(r), tp.title LIMIT 3')
            for d in r['results'][0].get('data', []):
                if d: print(f"  KG: {d[0]} --[{d[1]}]--> {d[2] if len(d)>2 else ''}")
        except: pass

print("\nDone!")
