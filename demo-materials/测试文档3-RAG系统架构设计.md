
# RAG 智能检索平台 — 系统架构设计文档



﻿# RAG 智能检索平台 — 系统架构设计文档

# RAG 智能检索平台 — 系统架构设计文档

﻿# RAG 智能检索平台 — 系统架构设计文档



> 版本：v1.0 | 更新日期：2026-07-10

---

## 一、系统概述

RAG（Retrieval-Augmented Generation）智能检索平台是一个基于检索增强生成技术的企业级知识问答系统。用户上传文档后，系统自动进行切片、向量化、存储，当用户提问时，系统从知识库中检索最相关的片段，作为上下文送入大语言模型生成回答。

---

## 二、系统架构

```
+---------------------+     +---------------------+
|   Vue 3 前端         |     |   FastAPI 后端       |
|   (Element Plus)     |---->|   (Python 3.11)     |
+---------------------+     +----------+----------+
                                       |
                    +------------------+------------------+
                    v                  v                  v
          +-----------------+  +--------------+  +--------------+
          |   SQLite 数据库   |  |  Chroma 向量库 |  |  OpenAI API  |
          |  (6 张核心表)     |  |  (1536 维)    |  |  (LLM+Embed) |
          +-----------------+  +--------------+  +--------------+
```

---

## 三、核心流程

### 3.1 文档处理流水线

```
上传文件 (.md/.txt)
    |
    v
文件存储 (./uploads/)
    |
    v
文档切片 (chunk_size=500, overlap=50)
    |
    v
Embedding 向量化 (text-embedding-3-small, 1536维)
    |
    v
向量写入 Chroma + 元数据写入 SQLite chunks 表
    |
    v
文档状态更新为 completed
```

### 3.2 检索对话流程

```
用户输入问题
    |
    v
问题分词 + 向量化
    |
    +-- 向量检索 (余弦相似度)
    +-- 全文检索 (BM25)
    +-- 混合检索 (alpha * vector + (1-alpha) * bm25)
    |
    v
命中结果排序，取 top_n
    |
    v
拼接上下文 -> 填入 rag_chat.prompt 模板
    |
    v
调用 LLM (gpt-4o-mini) 生成回答
    |
    v
返回回答 + 引用片段 (SSE 流式)
```

---

## 四、三种检索方式详解

### 4.1 向量检索（Vector Search）

使用余弦相似度计算用户问题向量与所有文档分片向量的距离，返回最相似的 top_n 个分片。

**适用场景：** 语义理解型问题，如"出差报销标准" ~ "差旅费用规定"

### 4.2 全文检索（Keyword / BM25）

基于 BM25 算法，计算用户问题中的关键词与文档分片的关键词匹配程度。

**适用场景：** 精确术语、专有名词匹配，如"1000 元/晚"、"1536 维"

### 4.3 混合检索（Hybrid Search）

将向量得分与 BM25 得分通过加权融合公式计算总分，得到最优排序。

```python
def hybrid_score(vector_score: float, bm25_score: float, alpha: float = 0.7) -> float:
    return alpha * vector_score + (1 - alpha) * bm25_score
```

**适用场景：** 通用场景，效果最好。

---

## 五、向量库设计

### 5.1 Chroma 配置

| 参数 | 值 |
|------|:---:|
| 服务模式 | HTTP Server |
| 地址 | localhost:8000 |
| 集合命名 | rag_chunks_{姓名} |
| 向量维度 | 1536 |
| 距离函数 | cosine |

### 5.2 Chroma 数据存储字段

每条 Chroma 记录存储：

- **id**: chunk 的 chroma_id（与 SQLite 中一致）
- **embedding**: 1536 维 float 数组
- **metadata**: {doc_id, kb_id, chunk_index, filename}

---

## 六、环境隔离

| 资源 | 隔离方式 | 示例 |
|------|----------|------|
| SQLite | dev_{姓名}_rag.db | dev_zhangsan_rag.db |
| Chroma 集合 | rag_chunks_{姓名} | rag_chunks_zhangsan |
| 上传目录 | uploads/dev_{姓名}/ | uploads/dev_zhangsan/ |

---

## 七、熔断与降级

| 故障点 | 降级行为 |
|--------|----------|
| Embedding API 超时 | 降级为仅 BM25 全文检索 |
| LLM API 超时 | 返回兜底文案 |

| Chroma 不可用 | 接口返回 5001 错误码 |


| Chroma 不可用 | 接口返回 5001 错误码 |

| Chroma 不可用 | 接口返回 5001 错误码 |

| Chroma 不可用 | 接口返回 5001 错误码 |

