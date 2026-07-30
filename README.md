# gjj-pipeline — 南宁公积金数据管线

Python 微服务，爬虫→清洗→LLM格式化→直接入库。

## 架构

```
POST /pipeline/sync (异步)
  ├── Crawler (8线程): 爬取HTML → BeautifulSoup清洗 → MinIO备份
  ├── Extractor (6线程): DeepSeek格式化 → POST Java /ingest 直接入库
  └── MinIO: 存储结构化MD文件
```

## 项目结构

```
├── pyproject.toml
├── requirements.txt
├── .env.example
├── API.md
├── gjj_pipeline/
│   ├── main.py            # FastAPI 入口 (3端点)
│   ├── crawler.py         # 爬虫 + HTML清洗
│   ├── extractor.py       # DeepSeek 格式化 + 直接入库
│   ├── storage.py         # MinIO 连接
│   └── config.py          # 集中配置
└── tools/                 # 实验脚本
```

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/pipeline/sync` | 触发全量同步 |
| GET | `/pipeline/sync/{tid}` | 查询进度 |

## 启动

```bash
pip install -e .
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
python -m gjj_pipeline.main  # http://localhost:8001
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | API Key |
| `API_BASE_URL` | `http://localhost:8080` | Java 后端地址 |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO |
| `CRAWL_CONCURRENCY` | `8` | 爬虫并发 |
| `EXTRACT_CONCURRENCY` | `6` | 提取并发 |

## 许可证

Copyright (C) 2026 Tang Longhao — GNU AGPL v3. [LICENSE](LICENSE)
