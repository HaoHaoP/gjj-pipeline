"""pipeline 集中配置"""

import os

# ── Server ──
HOST = os.environ.get("PIPELINE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PIPELINE_PORT", "8001"))

# ── MinIO / Storage ──
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "gjj-documents")

# ── Crawler ──
CRAWL_BASE_URL = os.environ.get(
    "CRAWL_BASE_URL", "https://gjj.nanning.gov.cn/xxgk/zcwjcx/"
)
CRAWL_CONCURRENCY = int(os.environ.get("CRAWL_CONCURRENCY", "8"))

# ── Extractor ──
EXTRACT_CONCURRENCY = int(os.environ.get("EXTRACT_CONCURRENCY", "6"))
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
)
