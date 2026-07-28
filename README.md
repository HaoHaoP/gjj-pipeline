# 南宁公积金数据管线 (gjj-pipeline)

Python 微服务，提供 FastAPI 端点供 Java 后端调用。

## 项目结构

```
├── pyproject.toml        项目元数据
├── requirements.txt      依赖（兼容旧方式）
├── gjj_pipeline/         管线服务包
│   ├── __init__.py
│   ├── main.py           FastAPI 入口
│   ├── crawler.py        HTML爬虫 + BS4清洗 + MD转换
│   └── extractor.py      DeepSeek LLM 条款提取
└── tools/                实验/开发辅助脚本
    ├── encoder.py        BGE-M3 向量编码
    ├── kg.py             知识图谱引用提取
    ├── eval.py           评估脚本
    ├── test_gen.py       测试集生成
    ├── rag_test.py       RAG+KG融合测试
    └── neo4j_import.py   Neo4j数据导入
```

## 环境变量

项目需要 DeepSeek API Key 作为环境变量。仓库提供 `.env.example` 模板，实际 Key 存放在本地 `.env` 文件中（已加入 `.gitignore`，不会上传）。

```bash
# 复制模板
cp .env.example .env
# 编辑 .env，填入你的 API Key
# DEEPSEEK_API_KEY=***
```

## 启动

```bash
# 1. 安装依赖
pip install -e .
# 或: pip install -r requirements.txt

# 2. 加载 DeepSeek API Key
source ../rag-api/.env

# 3. 启动服务 (默认 :8001)
python -m gjj_pipeline.main

# 4. 验证
curl http://localhost:8001/health
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/pipeline/sync` | 全量同步（异步：爬虫→清洗→LLM提取） |
| GET | `/pipeline/sync/{taskId}` | 查询同步状态 |

## 开发

```bash
# 单独运行爬虫
python -c "from gjj_pipeline.crawler import run_crawl; run_crawl()"

# 单独运行提取
python -c "from gjj_pipeline.extractor import run_extract; run_extract()"

# 运行工具脚本
python tools/kg.py
python tools/test_gen.py
```
