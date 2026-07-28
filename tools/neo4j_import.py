#!/usr/bin/env python3
"""Neo4j KG + Milvus 导入"""
import json, os, time, urllib.request, base64

NEO4J_URL = "http://localhost:7474"
NEO4J_AUTH = ("neo4j", "gjj123456")

def cypher(query):
    payload = json.dumps({"statements": [{"statement": query}]})
    cred = base64.b64encode(f"{NEO4J_AUTH[0]}:{NEO4J_AUTH[1]}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_URL + "/db/neo4j/tx/commit",
        data=payload.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Basic " + cred}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def milvus_ingest(title, text):
    payload = json.dumps({"title": title, "content": text}).encode()
    req = urllib.request.Request(
        "http://localhost:8080/api/documents/ingest",
        data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()[:200]
    except Exception as e:
        return "ERROR: " + str(e)[:100]

def escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

# === Neo4j ===
print("=== Neo4j 知识图谱导入 ===")
for i in range(30):
    try:
        cypher("RETURN 1")
        print("Neo4j connected")
        break
    except:
        time.sleep(2)
else:
    print("Neo4j timeout")
    exit(1)

cypher("CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE")
cypher("CREATE CONSTRAINT clause_id IF NOT EXISTS FOR (c:Clause) REQUIRE c.id IS UNIQUE")

clause_dir = os.path.expanduser("~/Documents/nanning-gjj-rag/data/clauses")
docs = {}

# Import policies and clauses
for fname in sorted(os.listdir(clause_dir)):
    if not fname.endswith('.json'): continue
    with open(os.path.join(clause_dir, fname)) as f:
        data = json.load(f)
    doc_id = data['doc_id']
    docs[doc_id] = data
    
    safe_title = escape(data['doc_title'])
    cypher(f'MERGE (p:Policy {{id: "{doc_id}"}}) SET p.title = "{safe_title}", p.date = "{data["doc_date"]}"')
    
    for c in data['clauses']:
        cid = doc_id + "_" + c['clause_number']
        safe_text = escape(c['text'])[:500]
        safe_num = escape(c['clause_number'])
        cypher(f'''
            MATCH (p:Policy {{id: "{doc_id}"}})
            MERGE (c:Clause {{id: "{cid}"}})
            SET c.number = "{safe_num}", c.text = "{safe_text}"
            MERGE (p)-[:CONTAINS]->(c)
        ''')

# Import relations
with open(os.path.expanduser("~/Documents/nanning-gjj-rag/data/kg_relations.json")) as f:
    kg = json.load(f)

rc = 0
for r in kg['relations']:
    from_cid = r['from_doc_id'] + "_" + r['from_clause']
    to_name = escape(r['to_document'])
    rel = r['relation']
    try:
        cypher(f'''
            MATCH (fc:Clause {{id: "{from_cid}"}})
            MERGE (tp:Policy {{title: "{to_name}"}})
            MERGE (fc)-[:{rel}]->(tp)
        ''')
        rc += 1
    except:
        pass

print(f"Imported: {len(docs)} policies, {rc} relations")

# === Milvus ===
print("\n=== Milvus 向量入库 ===")
# Check API
try:
    resp = urllib.request.urlopen("http://localhost:8080/api/documents", timeout=5)
    print("RAG API ready")
except:
    print("RAG API not running, skip")
    exit(0)

# Ingest clause by clause (batch would be faster but simpler to debug)
total = 0
for doc_id, data in docs.items():
    for c in data['clauses']:
        title = data['doc_title'][:80]
        text = c['text']
        result = milvus_ingest(title, escape(text))
        total += 1
        if total % 50 == 0:
            print(f"  {total} clauses ingested...")
    time.sleep(0.3)

print(f"Milvus: {total} clauses ingested")
print("\nDone!")
