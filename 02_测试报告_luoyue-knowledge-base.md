# 测试报告：luoyue-knowledge-base（work-luoyue）

| 项 | 内容 |
|---|---|
| 工作树 | `workspace_rag/work-luoyue` |
| 分支 / HEAD | `feature/luoyue-knowledge-base` @ `8e0cea0` |
| 对比基线 | `origin/dev` |
| 测试时间 | 2026-07-17 |
| 实测 | `frontend`: `npm install` + `npm run build` ✅；后端相对 dev **几乎无业务 diff** |
| 结论 | **前端知识库/文档/命中测试/对话 UI + Mock 可独立构建；关 Mock 连真实后端时契约与端口均不匹配，无法联调通过。后端 B 仍为空壳。** |

---

## 1. 依赖 / 环境 / 启动脚本

### 1.1 通过项

- `frontend/package.json` 依赖完整（Vue3 / Pinia / Element Plus / `vite-plugin-mock`）。
- 首次无 `node_modules` 时 `npm install` 成功；`npm run build` **约 3.75s 成功出 dist**。
- 后端 `requirements.txt` / `.env.example` 与主线同构，可单独起 A 服务（但本分支未增强后端）。

### 1.2 问题清单

#### [LUO-D01] Vite 代理默认打到 **8000**（高）

- **文件**：`frontend/vite.config.js`
- **片段**：

```24:31:work-luoyue/frontend/vite.config.js
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
```

- **问题**：后端约定端口为 **8001**；**8000 通常是 Chroma**。关 Mock 后请求会打到向量库或空端口。
- **修复建议**：`target: 'http://127.0.0.1:8001'`，或通过 `VITE_API_PROXY` 环境变量配置；并行测试时用 `5174` + `8012`。

#### [LUO-D02] Mock **默认 enable: true**（中）

- **片段**：同文件 `viteMockServe({ enable: true })`
- **风险**：开发者以为在测真后端，实际全走 Mock；联调结论失真。
- **建议**：`enable: process.env.VITE_USE_MOCK === 'true'`，文档写明开关。

#### [LUO-D03] 无一键启动 / 后端 B 空文件（中）

- `backend/app/api/auth.py`、`kb.py`、`docs.py`… 均为 **0 字节**（与 shang 相同）。
- 本分支 `git diff origin/dev...HEAD -- backend/` 几乎只有 pycache 清理，**后端能力未落地**。

---

## 2. 前端功能与契约测试

### 2.1 Mock 模式下（默认）

| 模块 | 预期 | 结果 |
|---|---|---|
| KbManage / DocManage / HitTest / ChatDialog | 页面可构建、Mock 可返回列表 | ✅ build 通过；Mock 结构自洽 |
| 命中测试 Store | 发 `doc_ids` + `mode`，读 `items` | ✅ 对 Mock 正确 |

命中测试请求体（前端真实发出）：

```35:41:work-luoyue/frontend/src/stores/hitTest.js
      const res = await testRetrieve({
        kb_id: kbId.value,
        doc_ids: docIds.value,
        query: query.value,
        mode: mode.value,
        top_n: topN.value
      })
```

Mock 返回 `items`：

```86:100:work-luoyue/frontend/src/mock/rag.mock.js
      if (!queryText.trim() || !body.doc_ids || !body.doc_ids.length) {
        return ok({ items: [], env, mode })
      }
      ...
      return ok({ items, env, mode })
```

### 2.2 对接真实后端 A（shang / dev）—— **失败契约**

后端 A 契约（shang 实测）：

| 字段 | 后端 A | 前端 luoyue | 兼容？ |
|---|---|---|---|
| 文档 | `doc_id: string` | `doc_ids: array` | ❌ |
| 模式 | `search_type` | `mode` | ❌ |
| 结果列表 | `hits` / `total_hits` | `items` | ❌ |
| 校验失败 | 422 missing fields | — | 实测：错误字段 → 422 |

#### [LUO-A01] 命中测试请求/响应字段与后端 A 不一致（阻断联调）

- **文件**：`frontend/src/api/rag.js`、`frontend/src/stores/hitTest.js`、`frontend/src/mock/rag.mock.js`
- **修复建议**（二选一，需团队统一契约）：
  1. 前端改为：`doc_id`（单选或循环调用）、`search_type`、解析 `data.hits`；
  2. 后端 A 扩展兼容：`doc_ids[]`、`mode` 别名、`items` 别名。

#### [LUO-A02] 列表字段兜底 `items || list` 与 B 响应未对齐（中）

- **文件**：`frontend/src/stores/kb.js`、`doc.js`
- **说明**：yulin 若返回 `{code,msg,data:[...]}` 或 `data.list`，需再适配；当前仅 Mock 友好。

#### [LUO-A03] 前端端口固定 5173（并行中）

- 三前端同开会冲突；并行请用 `--port 5174`。

---

## 3. 与 `origin/dev` 差异对比

`48 files, +4790/-510`，几乎全在 `frontend/`：

- 新增：Kb/Doc/Hit/Chat 视图、Pinia stores、Mock、组件库、SSE/CSV 工具
- 修改：`router`、`request.js`、`vite.config.js`、部分 api 封装

### 冲突 / 兼容判断

| 点 | 判断 |
|---|---|
| 相对纯前端增强 | 对 `dev` **加性**，后端不动 |
| 与 shang | **契约冲突**（见上），合入后「页面好看但调不通」 |
| 与 yulin | 代理端口、路径双 prefix、鉴权 Header 均未对齐；Mock 掩盖问题 |
| 空后端 api 文件 | 与 shang 相同，**合入勿覆盖** yulin 实现 |

---

## 4. 风险点（本分支）

| ID | 风险 | 级别 |
|---|---|---|
| R1 | Proxy → 8000 打到 Chroma | 高 |
| R2 | Mock 默认开，联调假绿 | 高 |
| R3 | `doc_ids`/`mode`/`items` 与 A 契约不一致 | 高 |
| R4 | 前端 5173 端口冲突 | 中 |
| R5 | 空 B 文件合入覆盖 | 高 |

---

## 5. 本分支建议验收标准（最小）

1. `npm run build` 通过  
2. `VITE_USE_MOCK=true` 下 KB/文档/命中/对话主路径可点通  
3. `VITE_USE_MOCK=false` + 代理 8001 时，按**统一契约**打通至少一条 `test_retrieve`  
4. 文档明确 Mock 开关与代理端口  

---

*报告人：测试工程师（本地并行测试）*
