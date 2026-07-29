# Pipeline API

> 南宁公积金数据管线 — 供 Java 后端调用的 HTTP 接口

## 基本信息

- 地址：`http://localhost:8001`
- 格式：JSON
- Swagger：`http://localhost:8001/docs`

## 端点

### GET /health

健康检查。

```
GET /health
→ 200 {"status":"ok"}
```

### POST /pipeline/sync

全量同步（异步）。触发爬虫 → 清洗 → LLM提取全流程。

```
POST /pipeline/sync
→ 200 {"taskId":"a1b2c3d4"}
```

### GET /pipeline/sync/{taskId}

查询同步任务状态。

```
GET /pipeline/sync/a1b2c3d4
→ 200 {
    "status": "running|done|failed",
    "stage": "crawl+extract|ingest",
    "progress": 45,
    "error": null,
    "articles": [  // 仅 done 状态返回
      {"doc_id":"abc123","title":"政策名称","minio_path":"abc123/政策名称.md"}
    ]
  }
```

## MinIO 对象结构

Pipeline 将数据写入 MinIO 的 `gjj-documents` bucket：

```
gjj-documents/
├── {doc_id}/
│   ├── {title}.md         ← 清洗后的 Markdown
│   └── clauses.json       ← LLM 提取的条款
```

## 增量判断

- 爬虫：`{doc_id}/{title}.md` 已存在 → 跳过
- 提取：`{doc_id}/clauses.json` 已存在 → 跳过

## 环境变量

| 变量 | 默认值 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `MINIO_HOST` | `localhost:9000` | MinIO 地址 |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO 用户名 |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO 密码 |
