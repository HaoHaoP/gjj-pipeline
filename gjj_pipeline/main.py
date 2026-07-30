#!/usr/bin/env python3
"""南宁公积金 — 数据管线微服务 (FastAPI)"""
import logging, os, uuid, sys, asyncio, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn

from gjj_pipeline.crawler import parse_list_page, _crawl_one
from gjj_pipeline.extractor import _extract_one
from gjj_pipeline.config import (HOST, PORT as DEFAULT_PORT, CRAWL_CONCURRENCY, EXTRACT_CONCURRENCY)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

app = FastAPI(title="南宁公积金数据管线", version="1.0")
tasks: dict[str, dict] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pipeline/sync")
def start_sync(bg: BackgroundTasks):
    tid = str(uuid.uuid4())[:8]
    tasks[tid] = {"status": "running", "stage": "crawl+extract", "progress": 0, "error": None}

    async def _sync():
        try:
            articles = parse_list_page()
            total = len(articles)
            logger.info("tid=%s parsed %d articles", tid, total)

            def sync_all():
                crawled = 0
                extracted = 0

                logger.info("tid=%s pipeline start %d crawl tasks", tid, total)
                tasks[tid]["stage"] = "crawl"
                with ThreadPoolExecutor(max_workers=CRAWL_CONCURRENCY) as crawl_pool, \
                     ThreadPoolExecutor(max_workers=EXTRACT_CONCURRENCY) as extract_pool:

                    crawl_fs = {crawl_pool.submit(_crawl_one, a): a for a in articles}
                    extract_fs = {}



                    # Phase 1: crawl — 爬完一篇立刻提交提取
                    for f in as_completed(crawl_fs):
                        a = crawl_fs[f]
                        crawled += 1
                        tasks[tid]["progress"] = int(crawled * 10 / total) if total > 0 else 0
                        if a.get("raw_text"):
                            ef = extract_pool.submit(_extract_one, a)
                            extract_fs[ef] = a

                    # Phase 2: extract+ingest (API calls are slow) — progress 10-95%
                    extract_total = len(extract_fs)
                    tasks[tid]["stage"] = "extract"
                    base = 10

                    tasks[tid]["progress"] = base
                    logger.info("tid=%s crawl done %d/%d articles → extract (base=%d%%)",
                                tid, extract_total, total, base)

                    if extract_total > 0:
                        for f in as_completed(extract_fs):
                            result = f.result() or 0
                            if result > 0:
                                extracted += 1
                            pct = base + int(extracted * 85 / extract_total)
                            tasks[tid]["progress"] = min(pct, 95)

                tasks[tid] = {"status": "done", "stage": "ingest", "progress": 100, "error": None,
                              "articles": [
                                  {"doc_id": a.get("doc_id"), "title": a["title"],
                                   "minio_path": a.get("minio_path"),
                                   "crawl_status": a.get("crawl_status", "unknown")}
                                  for a in articles
                              ]}


            await asyncio.to_thread(sync_all)
            done = len([a for a in articles if a.get("minio_path")])
            logger.info("tid=%s pipeline done %d articles ingested", tid, done)
        except Exception as e:
            logger.error("tid=%s pipeline failed: %s", tid, e)
            tasks[tid] = {"status": "failed", "progress": tasks[tid].get("progress", 0), "error": str(e)[:200]}

    bg.add_task(_sync)
    logger.info("task created tid=%s", tid)
    return {"taskId": tid}

@app.get("/pipeline/sync/{tid}")
def get_status(tid: str):
    t = tasks.get(tid)
    if not t:
        raise HTTPException(404)
    return t

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    uvicorn.run(app, host=HOST, port=port)
