#!/usr/bin/env python3
"""南宁公积金 — 数据管线微服务 (FastAPI)"""
import os, uuid, sys

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件

from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn

from gjj_pipeline.crawler import run_crawl
from gjj_pipeline.extractor import run_extract

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
            tasks[tid]["stage"] = "crawl"
            tasks[tid]["progress"] = 0
            result = run_crawl(progress_callback=lambda p: tasks[tid].update(progress=int(5 + p * 15 / 100)))
            if not result.get("success"):
                tasks[tid] = {"status": "failed", "stage": "crawl", "progress": 0, "error": "爬取+清洗失败"}
                return
            
            tasks[tid]["stage"] = "extract"
            tasks[tid]["progress"] = 20
            result = run_extract(progress_callback=lambda p: tasks[tid].update(progress=int(20 + p * 70 / 100)))
            if not result.get("success"):
                tasks[tid] = {"status": "failed", "stage": "extract", "progress": 20, "error": "条款提取失败"}
                return
            
            tasks[tid] = {"status": "done", "stage": "ingest", "progress": 100, "error": None}
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
