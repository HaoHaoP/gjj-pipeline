#!/usr/bin/env python3
"""Phase 1.5: 条款文本向量化并存入Milvus"""
import json, os, sys, time, urllib.request

BGE_URL = "http://localhost:8002/encode"
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
COLLECTION = "rag_documents"
DATA_DIR = os.path.expanduser("~/Documents/nanning-gjj-rag/data/clauses")

def check_services():
    """检查BGE-M3和Milvus是否可用"""
    # Check BGE
    try:
        req = urllib.request.Request(BGE_URL, 
            data=json.dumps({"sentences": ["test"]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            dim = len(data["encodings"][0])
            print(f"BGE-M3 OK (dim={dim})")
    except Exception as e:
        print(f"BGE-M3 FAIL: {e}")
        return False
    
    # Check Milvus
    try:
        req = urllib.request.Request(f"http://{MILVUS_HOST}:9091/healthz")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"Milvus OK: {resp.read().decode()}")
    except Exception as e:
        print(f"Milvus FAIL: {e}")
        return False
    
    return True

def encode_batch(texts):
    """批量编码文本"""
    req = urllib.request.Request(BGE_URL,
        data=json.dumps({"sentences": texts}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["encodings"]

def main():
    if not check_services():
        print("\n请先启动服务: ./rag-ctl.sh start")
        sys.exit(1)
    
    # 收集所有条款
    all_clauses = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'): continue
        with open(os.path.join(DATA_DIR, fname)) as f:
            data = json.load(f)
        doc_title = data.get('doc_title', '')
        doc_id = data.get('doc_id', '')
        for c in data.get('clauses', []):
            all_clauses.append({
                'doc_id': doc_id,
                'doc_title': doc_title,
                'clause_number': c.get('clause_number', ''),
                'text': c.get('text', ''),
                'parent_title': c.get('parent_title', ''),
            })
    
    print(f"\n共 {len(all_clauses)} 条待入库\n")
    
    # 预览前3条
    for c in all_clauses[:3]:
        print(f"  [{c['doc_title'][:40]}] {c['clause_number']}: {c['text'][:80]}...")
    
    print(f"\n开始编码（批次大小=10）...")
    
    batch_size = 10
    embeddings = []
    for i in range(0, len(all_clauses), batch_size):
        batch = all_clauses[i:i+batch_size]
        texts = [c['text'] for c in batch]
        vecs = encode_batch(texts)
        embeddings.extend(vecs)
        print(f"  [{i+1}-{min(i+batch_size, len(all_clauses))}/{len(all_clauses)}] OK")
    
    # 保存为完整的JSON（embedding + metadata）
    import pickle
    output = {
        'clauses': all_clauses,
        'embeddings': embeddings,
        'dim': len(embeddings[0]) if embeddings else 0
    }
    
    out_path = os.path.expanduser("~/Documents/nanning-gjj-rag/data/clauses_with_embeddings.json")
    with open(out_path, 'w') as f:
        json.dump([{**c, 'embedding': e} for c, e in zip(all_clauses, embeddings)], 
                  f, ensure_ascii=False)
    
    print(f"\n完成: {len(all_clauses)} 条条款已编码")
    print(f"输出: {out_path}")
    print(f"\n下一步: 通过RAG API的 /api/documents/ingest 接口入库，或直接用 pymilvus 插入")

if __name__ == '__main__':
    main()
