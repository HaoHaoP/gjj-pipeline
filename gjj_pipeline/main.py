#!/usr/bin/env python3
"""南宁公积金 — 数据管线微服务 (FastAPI)"""
import os, uuid, sys, asyncio, time

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件

from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn

from gjj_pipeline.crawler import run_crawl, parse_list_page, _crawl_one, fetch, clean_html
from gjj_pipeline.extractor import run_extract, _extract_one
import json as json_mod
import threading
from pathlib import Path

app = FastAPI(title="南宁公积金数据管线", version="1.0")
tasks: dict[str, dict] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pipeline/sync")
def start_sync(bg: BackgroundTasks):
    tid = str(uuid.uuid4())[:8]
    tasks[tid] = {"status": "running", "stage": "crawl", "progress": 0, "error": None}
    
    async def _sync():
        try:
            tasks[tid]["stage"] = "crawl+extract"
            tasks[tid]["progress"] = 0
            
            articles = parse_list_page()
            total = len(articles)
            crawled = {"count": 0}
            extracted = {"count": 0}
            lock = threading.Lock()
            error = {"msg": None}
            
            def crawl_worker():
                for a in articles:
                    try:
                        _crawl_one(a)
                    except Exception as e:
                        error["msg"] = str(e)
                    with lock:
                        crawled["count"] += 1
            
            def extract_worker():
                BASE = os.path.join(os.path.expanduser("~/Documents/nanning-gjj-rag/data/policies"), "cleaned")
                done = set()
                while True:
                    if error["msg"]: return
                    with lock:
                        if crawled["count"] >= total:
                            time.sleep(0.5)
                            break
                    for a in articles:
                        fid = a["id"]
                        if fid in done: continue
                        if os.path.exists(os.path.join(BASE, f"{fid}.md")):
                            done.add(fid)
                            try:
                                _extract_one(a)
                            except Exception as e:
                                error["msg"] = str(e)
                            with lock:
                                extracted["count"] += 1
                    time.sleep(0.3)
                for a in articles:
                    fid = a["id"]
                    if fid in done: continue
                    if os.path.exists(os.path.join(BASE, f"{fid}.md")):
                        done.add(fid)
                        try: _extract_one(a)
                        except Exception as e: error["msg"] = str(e)
                        with lock:
                            extracted["count"] += 1
            
            def progress_loop():
                while True:
                    with lock:
                        cr = crawled["count"]
                        ex = extracted["count"]
                    pct = int((cr * 0.15 + ex * 0.85) / total * 100) if total > 0 else 0
                    tasks[tid]["progress"] = min(pct, 100)
                    if cr >= total and ex >= cr:
                        break
                    time.sleep(0.5)
            
            # Run everything in threads (NOT blocking the event loop)
            t1 = threading.Thread(target=crawl_worker, daemon=True)
            t2 = threading.Thread(target=extract_worker, daemon=True)
            t1.start(); t2.start()
            
            # Progress loop runs on the event loop via asyncio
            loop = asyncio.get_running_loop()
            
            async def check_done():
                while t1.is_alive() or t2.is_alive():
                    with lock:
                        cr = crawled["count"]
                        ex = extracted["count"]
                    pct = int((cr * 0.15 + ex * 0.85) / total * 100) if total > 0 else 0
                    tasks[tid]["progress"] = min(pct, 100)
                    if error["msg"]:
                        tasks[tid] = {"status": "failed", "stage": "crawl+extract", "progress": tasks[tid]["progress"], "error": error["msg"]}
                        return
                    await asyncio.sleep(0.5)
                tasks[tid] = {"status": "done", "stage": "ingest", "progress": 100, "error": None}
            
            await check_done()
        except Exception as e:
            tasks[tid] = {"status": "failed", "stage": tasks[tid]["stage"], "progress": tasks[tid]["progress"], "error": str(e)[:200]}
    
    bg.add_task(_sync)
    return {"taskId": tid}

@app.get("/pipeline/sync/{tid}")
def get_status(tid: str):
    t = tasks.get(tid)
    if not t:
        raise HTTPException(404)
    return t

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="0.0.0.0", port=port)
