# gjj-pipeline — 南宁公积金数据管线

Python 微服务，提供 FastAPI 端点供 Java 后端调用。负责政策文档爬取、清洗和 LLM 格式化。

## 架构

```
POST /pipeline/sync (异步)
  ├── Crawler (8线程): 爬取HTML → BeautifulSoup清洗
  ├── Extractor (6线程): DeepSeek格式化为结构化Markdown
  └── MinIO: 存储处理后的MD文件
```

## 项目结构

```
├── pyproject.toml         # 项目元数据 + 依赖
├── requirements.txt       # 传统依赖声明
├── .env.example           # 环境变量模板
├── API.md                 # 接口文档
├── gjj_pipeline/          # 包
│   ├── main.py            # FastAPI 入口 (3个端点)
│   ├── crawler.py         # 爬虫 + HTML清洗
│   ├── extractor.py       # DeepSeek LLM 格式化
│   ├── storage.py         # MinIO 连接层
│   └── config.py          # 集中配置
└── tools/                 # 实验/开发脚本
```

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/pipeline/sync` | 触发全量同步（异步） |
| GET | `/pipeline/sync/{tid}` | 查询进度（status/progress/stage/articles） |

## 启动

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动
python -m gjj_pipeline.main
# 服务运行在 http://localhost:8001
```

## 增量同步

Pipeline 通过 MinIO 对象存在性判断文档是否已处理：
- `${doc_id}/${title}.md` 已存在 → 跳过爬虫
- 爬虫完成后立即提交提取，Producer-Consumer 管道
- 跳过时仍设置 `minio_path` 确保 Java 能获取完整列表

## 环境变量

| 变量 | 默认值 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO 地址 |
| `CRAWL_CONCURRENCY` | `8` | 爬虫并发数 |
| `EXTRACT_CONCURRENCY` | `6` | 提取并发数 |

## 许可证

Copyright (C) 2026 Tang Longhao

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See [LICENSE](LICENSE) for details.
