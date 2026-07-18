# 第 0 步：建立评测基线

**目标：** 在改任何检索代码之前，留下一份「改前」数据，后面每一步优化都和它比。

---

## 你要做的 4 件事

### 1. 准备知识库与文档

在管理后台或 API 上传 `demo-materials` 下三篇文档到**同一个知识库**（或三个库分别记 doc_id）：

| 文档 | 文件名 |
|------|--------|
| 考勤制度 | `测试文档1-公司考勤制度.md` |
| 差旅报销 | `测试文档2-差旅报销标准.md` |
| RAG 架构 | `测试文档3-RAG系统架构设计.md` |

确保每篇状态为 **completed**。若刚上传，等 ingest 完成。

> **重要：** 若 vector 一直 0 hits，说明 Chroma 与 SQLite 未对齐，需重新上传或重跑 ingest，否则基线会误导。

### 2. 填写 `eval/config.json`

打开 `rag-tuning/eval/config.json`，填入：

- `api_base`：默认 `http://127.0.0.1:8001`
- `auth`：admin 账号（默认 admin / admin123）
- `docs` 下三篇文档的 `kb_id` 和 `doc_id`

可在文档列表 API 或前端文档管理页复制 ID。

### 3. 启动服务

```powershell
# 终端 1：Chroma
chroma run --host 127.0.0.1 --port 8000 --path .chroma_data_shang

# 终端 2：后端
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

验证：`curl http://127.0.0.1:8001/health` 返回 code=0。

### 4. 跑基线脚本

```powershell
cd rag-tuning
python scripts/run_baseline.py --tag baseline-v0
```

输出：

- `eval/results/baseline-v0.json` — 机器可读
- 终端打印每条 PASS/FAIL 摘要

---

## 如何判「命中」

脚本用 **关键词匹配**：Top3 片段的 `content` 里是否出现 `golden.json` / `stress.json` 里配置的 `keywords` 任一。

- **PASS**：至少命中 1 个关键词  
- **FAIL**：Top3 都没有  
- **EMPTY**：hits 为空（检查入库或 search_type）

人工复核：打开 JSON 看 `top_hits` 文本是否合理，比自动 PASS/FAIL 更准。

---

## 完成后

1. 在 `00-进度清单.md` 勾选第 0 步  
2. 把 `baseline-v0` 结果路径记进备注表  
3. 告诉我「第 0 步完成」，进入 **第 1 步 Query Rewrite**
