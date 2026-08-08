"""存储层 — MinIO 连接层"""
from io import BytesIO
from gjj_pipeline.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET,
)

_client = None


def _get_client():
    global _client
    if _client is None:
        from minio import Minio
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        if not _client.bucket_exists(MINIO_BUCKET):
            _client.make_bucket(MINIO_BUCKET)
    return _client


def exists(name):
    try:
        _get_client().stat_object(MINIO_BUCKET, name)
        return True
    except Exception:
        return False


def upload_md(doc_id, title, content):
    path = f"{doc_id}/{title}.md"
    data = content.encode("utf-8")
    _get_client().put_object(MINIO_BUCKET, path, BytesIO(data), len(data), content_type="text/markdown")
    return path


def download(path):
    resp = _get_client().get_object(MINIO_BUCKET, path)
    return resp.read().decode("utf-8")


def download_bytes(path):
    resp = _get_client().get_object(MINIO_BUCKET, path)
    return resp.read()
