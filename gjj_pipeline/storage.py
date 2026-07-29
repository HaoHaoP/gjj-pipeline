"""Storage — MinIO 主模式 / 本地文件系统调试模式（STORAGE_BACKEND=local）"""
import os, json
from io import BytesIO

BUCKET = "gjj-documents"
DATA_DIR = os.path.expanduser("~/Documents/nanning-gjj-rag/data/pipeline-storage")
BACKEND = os.environ.get("STORAGE_BACKEND", "minio")

_client = None

def _get_client():
    global _client
    if _client is None:
        if BACKEND == "local":
            _client = "local"
        else:
            from minio import Minio
            _client = Minio("localhost:9000", access_key="minioadmin",
                            secret_key="minioadmin", secure=False)
            if not _client.bucket_exists(BUCKET):
                _client.make_bucket(BUCKET)
    return _client


def _local_path(name):
    p = os.path.join(DATA_DIR, name.lstrip("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def exists(name):
    c = _get_client()
    if c == "local":
        return os.path.exists(_local_path(name))
    try:
        c.stat_object(BUCKET, name)
        return True
    except Exception:
        return False


def upload_md(doc_id, title, content):
    path = f"{doc_id}/{title}.md"
    c = _get_client()
    if c == "local":
        data = content.encode("utf-8")
        with open(_local_path(path), "wb") as f:
            f.write(data)
        return path
    data = content.encode("utf-8")
    c.put_object(BUCKET, path, BytesIO(data), len(data), content_type="text/markdown")
    return path

def download(path):
    c = _get_client()
    if c == "local":
        with open(_local_path(path), "r") as f:
            return f.read()
    resp = c.get_object(BUCKET, path)
    return resp.read().decode("utf-8")


def download_bytes(path):
    c = _get_client()
    if c == "local":
        with open(_local_path(path), "rb") as f:
            return f.read()
    resp = c.get_object(BUCKET, path)
    return resp.read()
