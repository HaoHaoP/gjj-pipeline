#!/usr/bin/env python3
"""运行测试集，评估RAG+KG系统"""
import json, os, time, urllib.request

API = "http://localhost:8080/api/rag/query"
TEST = os.path.expanduser("~/Documents/nanning-gjj-rag/data/test_set.json")

with open(TEST) as f:
    data = json.load(f)

questions = data['questions']
print(f"测试集: {len(questions)} 题\n")

results = []
correct = 0
total = 0

for i, q in enumerate(questions):
    cat = q['category']
    is_trap = q.get('trap', False)
    question = q['question']
    
    print(f"[{i+1}/{len(questions)}] {'🔴' if is_trap else '🟢'} [{cat}] {question[:60]}...")
    
    # Call RAG API
    try:
        payload = json.dumps({"question": question}).encode()
        req = urllib.request.Request(API, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        
        answer = result.get('answer', '')
        error = result.get('error', '')
        sources = result.get('sources', [])
        
        # For trap questions: if system says "未找到" or returns error, that's correct
        if is_trap:
            if '未找到' in answer or '不存在' in answer or error:
                score = 1.0
            else:
                score = 0.0
        else:
            # Placeholder - need manual evaluation for accuracy
            score = None  # To be manually evaluated
            
        results.append({
            'id': q['id'],
            'category': cat,
            'trap': is_trap,
            'question': question,
            'answer': answer[:500],
            'sources': [s.get('title', '')[:40] for s in sources[:3]],
            'score': score
        })
        
        if score is not None:
            total += 1
            correct += score
            print(f"  Score: {score}")
        else:
            print(f"  Answer: {answer[:100]}...")
    
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({'id': q['id'], 'question': question, 'error': str(e), 'score': 0.0})

    time.sleep(0.5)

# Save results
out = os.path.expanduser("~/Documents/nanning-gjj-rag/data/test_results.json")
with open(out, 'w') as f:
    json.dump({'results': results, 'summary': {
        'total': len(results),
        'traps': sum(1 for r in results if r.get('trap')),
        'trap_score': sum(r['score'] for r in results if r.get('trap') and r['score'] is not None),
        'evaluated': sum(1 for r in results if r['score'] is not None)
    }}, f, ensure_ascii=False, indent=2)

print(f"\n=== Results ===")
print(f"Total: {len(results)} questions")
traps = [r for r in results if r.get('trap')]
print(f"Traps: {len(traps)}, Score: {sum(r['score'] for r in traps if r['score'] is not None)}/{len(traps)}")
print(f"Saved: {out}")
