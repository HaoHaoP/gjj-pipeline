"""DeepSeek LLM — 全文一次调用，输出结构化 Markdown"""
import os, time, hashlib, logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from gjj_pipeline.config import API_BASE_URL

logger = logging.getLogger(__name__)

_session = requests.Session()
_retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=10, pool_maxsize=10)
_session.mount("https://", _adapter)

MD_PROMPT = """你是政策文档解析专家。请将以下南宁住房公积金政策文档整理为结构清晰、标题层级明确的 Markdown。

要求：
- 文档大标题使用 "# " 开头（一级标题）
- 各章标题使用 "## " 开头（二级标题），如 "## 第一章 总则"
- 条款使用加粗格式 "**第X条**" 标记（不是标题）
- 子项保留原文编号如（一）（二）或 1. 2.
- 表格用 Markdown 表格格式保留
- 保留全部正文内容不删减
- 只输出 Markdown，不包含任何解释或额外内容"""


def call_deepseek(prompt: str, max_tokens: int = 16384) -> str:
    """调 DeepSeek API，返回文本内容。大文档自动扩容到 32768 tokens"""
    if len(prompt) > 20000:
        max_tokens = 32768
    elif len(prompt) > 10000:
        max_tokens = 16384
    api_key = os.environ["DEEPSEEK_API_KEY"]
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    r = _session.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _extract_one(article: dict) -> int:
    """从 article['raw_text'] 读取清理后 HTML，LLM 输出结构化 Markdown，写入 MinIO"""
    title = article.get("title", "")
    raw_text = article.get("raw_text", "")
    doc_id = article.get("doc_id", hashlib.md5(title.encode()).hexdigest()[:8])

    logger.info("extract start doc_id=%s title=%s raw=%d chars", doc_id, title[:40], len(raw_text))
    if not raw_text or len(raw_text) < 100:
        logger.warning("extract skip doc_id=%s raw_text too short", doc_id)
        return 0

    try:
        prompt = MD_PROMPT.format(title=title, text=raw_text)
        logger.info("extract calling LLM doc_id=%s prompt=%d chars", doc_id, len(prompt))
        markdown = call_deepseek(prompt)

        if markdown and len(markdown) >= 50:
            # 剥掉可能的 ```markdown ... ``` 包裹
            markdown = markdown.strip()
            if markdown.startswith("```"):
                nl = markdown.find("\n")
                markdown = markdown[nl + 1 :] if nl > 0 else markdown[3:]
            if markdown.rstrip().endswith("```"):
                markdown = markdown.rstrip()[:-3].rstrip()

            logger.info("extract ingesting doc_id=%s md=%d bytes", doc_id, len(markdown))
            minio_path = f"{doc_id}/{title}.md"
            resp = requests.post(
                f"{API_BASE_URL}/api/documents/ingest",
                json={
                    "title": title,
                    "content": markdown,
                    "minioPath": minio_path,
                    "originalFilename": f"{title}.md",
                    "source": "SYNC",
                    "chunkSize": 500,
                    "overlapSize": 0,
                    "chunkMode": "MARKDOWN"
                },
                timeout=120
            )
            resp.raise_for_status()
            logger.info("extract done doc_id=%s md=%d bytes ingest=%s", doc_id, len(markdown), resp.json().get("data", {}).get("chunks"))
            print(f"  OK (MD {len(markdown)}字)")
            return len(markdown)
        else:
            logger.warning("extract empty result doc_id=%s", doc_id)
            return 0
    except Exception as e:
        logger.error("extract fail doc_id=%s: %s", doc_id, e, exc_info=True)
        print(f"  FAIL: {e}")
        return 0
