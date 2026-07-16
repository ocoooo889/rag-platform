# RAG 智能体项目 — 完整项目管控方案（V2）

> 适用场景：6 人 × 2 天极速交付 RAG 智能体后台
> 版本：v2.0（V2 终稿，在 V1 基础上合并五项增量）
> 阅读对象：项目负责人、全体开发、测试工程师

---

## V2 新增内容概览

| # | 增量模块 | 核心目标 | 对应章节 |
|:--:|------|------|:--:|
| 1 | 用户组权限与数据可见性隔离 | 不同用户组只能查看授权范围内的资料，防止越权访问 | 第七章 |
| 2 | 可观测性体系 | 日志管理 + Prometheus 指标 + Langfuse LLM 追踪 + 核心指标看板 | 第八章 |
| 3 | 白标定制（OEM） | 购买方可更换系统名称、Logo、主题色，实现品牌私有化 | 第九章 |
| 4 | 统一字段命名规范 | 全局检索/对话输入字段统一为 `query`，消除命名歧义 | 第十章 |
| 5 | 文档状态管控与检索准入 | 文档未处理完成时不可检索，命中测试给出等待提示 | 第十一章 |

---

## 一、人员分工（V2 终稿）

### 1.1 分工总表

| 角色 | 人员 | 核心职责 | 专属产出 |
|------|:--:|------|------|
| 项目负责人 | 1 人 | 总控 + 产品 + 规范输出 + 风险把控 | 契约文档、提示词库、排期表、部署说明、演示脚本 |
| 后端 A | 1 人 | RAG 核心算法（向量库、切片、三种检索、LLM 调用）+ Langfuse 追踪集成 | 检索接口、对话接口、Embedding 工具类、Langfuse 集成 |
| 后端 B | 1 人 | 业务 CRUD + 鉴权 + 文件上传 + **用户组权限** + **白标配置** + **Prometheus 指标** + **结构化日志** | 用户/角色/用户组/知识库/文档管理接口、登录鉴权、权限中间件、品牌配置接口、监控埋点 |
| 前端 A | 1 人 | 管理后台页面（5 页）+ **白标动态渲染** + **用户组管理页** | 系统概览、角色管理、用户管理、用户组管理、大模型管理、品牌配置入口 |
| 前端 B | 1 人 | RAG 核心页面（4 页）+ **文档状态联动禁用** | 知识库管理、文档管理、命中率测试、智能对话 |
| 测试工程师 | 1 人 | 全流程测试 + 用例编写 + **权限越权专项** + **文档状态准入专项** | 测试用例、bug 跟踪、命中测试专项用例、权限边界用例 |

### 1.2 与 V1 变更说明

- **后端 B** 新增承接：用户组权限体系（表结构 + 中间件 + 接口过滤）、白标系统配置接口、Prometheus 指标埋点、结构化日志中间件
- **后端 A** 新增承接：Langfuse LLM 追踪集成（Embedding/检索/对话全链路 Trace）
- **前端 A** 新增承接：用户组管理页面（第 5 页）、白标动态渲染（启动时拉取品牌配置，全局生效）
- **前端 B** 新增承接：文档状态联动——未完成文档在命中测试下拉中禁用并显示提示
- **测试** 新增承接：权限越权专项用例（跨组访问阻断）、文档状态准入用例（未完成不可检索）
- 前端 A 原承接的大模型管理页面不变

---

## 二、2 天工作量拆解（V2 终稿）

### Day1

| 时段 | 项目负责人 | 后端 A（RAG） | 后端 B（CRUD） | 前端 A | 前端 B | 测试 |
|------|------|------|------|------|------|------|
| 上午 | 输出全套契约 + 提示词 + 排期表；Git 仓库脚手架搭建；确认全员 API Key 可用；**输出 V2 新增表结构（用户组、系统配置）** | 数据库表模型 + 项目骨架 + Embedding 工具类 + 切片工具类 + **Langfuse SDK 初始化** | 数据库表模型 + 项目骨架 + 登录鉴权 + 用户/角色 CRUD + **用户组表结构 + 结构化日志中间件** | 全局布局 + 路由 + 权限控制 + 系统概览页 + **白标配置拉取机制** | 全局布局 + 路由 + Mock 数据对接 + 知识库管理页 | 编写全模块测试用例 + 接口文档校验 + **权限越权用例编写** |
| 下午 | 盯后端 A/B 主动脉联调；CP1 检查点 | 文档上传→切片→向量化 链路串通；向量检索 + 全文检索开发；**Langfuse Trace 包裹检索链路** | 文档上传接口 + 文件存储；知识库/大模型管理 CRUD；**用户组 CRUD + 权限中间件**；**白标配置接口**；**Prometheus /metrics 端点** | 角色管理 + 用户管理页面 + **用户组管理页面** | 文档管理页 + **命中率测试页完整 UI（含文档状态禁用逻辑）** | 单模块冒烟测试；命中测试专项用例编写；**文档状态准入用例编写** |
| 晚间 | CP2 检查点（19:00）：全员合入 dev，验证主动脉贯通 | 混合检索 + 命中测试接口完成 + **文档状态准入校验（非 completed 文档不可检索）** | 权限拦截 + 下拉筛选 + 分页接口 + **所有 KB/文档接口加用户组过滤** | 大模型管理页面 + **品牌配置页面** | 智能对话页面骨架 | 已开发接口回归测试 + **权限越权冒烟测试** |

### Day2

| 时段 | 项目负责人 | 后端 A（RAG） | 后端 B（CRUD） | 前端 A | 前端 B | 测试 |
|------|------|------|------|------|------|------|
| 上午 | 组织前后端联调；CP3 检查点（12:00） | RAG 对话链路 + LLM 流式对接 + 熔断降级 + **Langfuse 对话 Trace + Token 用量上报** | 与后端 A 数据互通 + 数据导出 + **Prometheus 自定义指标完善（检索延迟、LLM 延迟、命中率）** | 页面弹窗 + 筛选分页 + 表单校验 + **白标渲染联调** | 命中测试页对接真实接口 + 智能对话聊天窗口 + **文档状态禁用联调** | 全流程串联测试 + **权限隔离全链路测试** |
| 下午 | 汇总 bug + 分配优先级；输出交付文档 + 演示脚本 | bug 修复 + 检索速度优化 | bug 修复 + **监控指标校验** | 样式统一 + 剩余 bug + **白标切换验证** | 三种检索切换交互 + 流式渲染 + 联调 | 回归测试 + 兼容性校验 + 测试报告 + **可观测性验证** |

### 检查点纪律

| 检查点 | 时间 | 硬性通过标准 |
|:--:|------|------|
| CP1 | Day1 13:00 | 全员本地启动成功、数据库建表完成（含用户组表 + 系统配置表）、Mock 接口可调通 |
| CP2 | Day1 19:00 | 文档上传→切片→向量化→检索 主动脉贯通；**文档状态准入校验生效** |
| CP3 | Day2 12:00 | 全链路贯通（创建知识库→上传文档→**等待处理完成**→命中测试→智能对话）；**用户组权限隔离生效**；**白标配置可切换** |

---

## 三、技术框架（V2 终稿）

### 3.1 后端

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 轻量、自动接口文档、异步支持 |
| 数据库 | SQLite（每人独立文件） | 2 天无需装 MySQL，零部署 |
| 向量库 | Chroma（HTTP 服务模式） | 避免多进程 SQLite 锁冲突 |
| 文档切片 | `RecursiveCharacterTextSplitter` | chunk_size=500, overlap=50 |
| Embedding | `text-embedding-3-small`（OpenAI） | 向量维度 1536，Day1 上午定死 |
| LLM | `gpt-4o-mini` 或兼容 API | 统一封装客户端，10s 超时 |
| 鉴权 | JWT | 简易 Token 登录 |
| **结构化日志** | **`loguru` + JSON 格式化** | 统一日志格式，支持按级别过滤，输出到文件 + 控制台 |
| **指标监控** | **`prometheus-fastapi-instrumentator`** | 自动采集 HTTP 指标 + 自定义业务指标，暴露 `/metrics` 端点 |
| **LLM 可观测** | **`langfuse` Python SDK** | 追踪 Embedding/检索/LLM 调用全链路，记录 Token 用量、延迟、成本 |

### 3.2 前端

| 组件 | 选型 | 说明 |
|------|------|------|
| 框架 | Vue3 + Vite | 启动快，开发效率高 |
| UI 组件库 | Element Plus | 下拉、表格、表单、弹窗全覆盖 |
| 状态管理 | Pinia | 用户权限、全局配置、**品牌配置** |
| 请求 | Axios | 统一拦截 token、错误提示 |
| Mock | `vite-plugin-mock` 或静态 JSON | Day1 上午前端不等待后端 |

### 3.3 切片参数（写死进 `config.py`）

```python
CHUNK_SIZE = 500          # 中文约 500 字一片
CHUNK_OVERLAP = 50        # 片间重叠 50 字
SEPARATORS = ["\n## ", "\n### ", "\n", "。", ".", " "]
```

### 3.4 混合检索融合公式（写死进 `retriever.py`）

```python
def hybrid_score(vector_score: float, bm25_score: float, alpha: float = 0.7) -> float:
    """
    vector_score: 余弦相似度 (0~1)
    bm25_score: BM25 原始得分（需先 min-max 归一化到 0~1）
    alpha: 向量检索权重，默认 0.7 偏向语义
    """
    return alpha * vector_score + (1 - alpha) * bm25_score
```

### 3.5 V2 新增依赖（`requirements.txt` 追加）

```txt
# --- 日志 ---
loguru>=0.7.0

# --- Prometheus 指标监控 ---
prometheus-fastapi-instrumentator>=6.1.0
prometheus-client>=0.20.0

# --- Langfuse LLM 可观测 ---
langfuse>=2.0.0
```

### 3.6 V2 新增前端依赖（`package.json` 追加）

```json
{
  "dependencies": {
    "pinia-plugin-persistedstate": "^4.0.0"
  }
}
```

> `pinia-plugin-persistedstate` 用于持久化品牌配置，避免每次刷新闪烁。

---

## 四、🔴 环境隔离规范（Day1 上午强制落地）

### 4.1 `.env.example` 模板

```bash
# ===== 个人开发环境标识（每人不同，必须改）=====
ENV=dev-你的姓名拼音

# ===== 个人独立资源路径 =====
LOCAL_DB_NAME=dev_你的姓名拼音_rag.db
CHROMA_COLLECTION_SUFFIX=_你的姓名拼音
UPLOAD_DIR=./uploads/dev_你的姓名拼音

# ===== LLM / Embedding API Key（每人用自己的 Key）=====
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1

# ===== Chroma 服务地址（所有人统一）=====
CHROMA_HOST=localhost
CHROMA_PORT=8000

# ===== 全局超时配置 =====
LLM_TIMEOUT=10
EMBEDDING_TIMEOUT=10

# ===== V2 新增：Langfuse 配置 =====
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=http://localhost:3000

# ===== V2 新增：Prometheus 配置 =====
PROMETHEUS_ENABLED=true
METRICS_PATH=/metrics
```

### 4.2 隔离规则

| 资源 | 隔离方式 | 效果 |
|------|------|------|
| SQLite 数据库 | `dev_{姓名}_rag.db` | 每人独立数据库文件 |
| Chroma 集合 | 集合名后缀 `_{姓名}` | 每人独立向量空间 |
| 文件上传 | `./uploads/dev_{姓名}/` | 每人独立上传目录 |
| API Key | 各自 `.env` 配置 | 避免共用触发限流 |
| **Langfuse 项目** | **每人独立 Langfuse Project** | 追踪数据互不干扰 |

> ⚠️ **开工前全员互相检查 `.env`，确认 `ENV` 各有不同。A 上传的文档绝不会出现在 B 的命中测试结果中。**

### 4.3 Chroma 服务模式启动（负责人准备）

```bash
# 一键启动 Chroma HTTP 服务（所有人连接同一个服务端，但集合名隔离）
chroma run --path ./chroma_data --port 8000
```

```python
# 后端统一连接方式
import chromadb
import os
client = chromadb.HttpClient(host="localhost", port=8000)
collection_name = f"rag_chunks_{os.getenv('CHROMA_COLLECTION_SUFFIX', 'default')}"
collection = client.get_or_create_collection(name=collection_name)
```

---

## 五、🔴 LLM/Embedding 超时熔断与降级策略

### 5.1 全局配置（`config.py`）

```python
LLM_TIMEOUT = 10        # 大模型调用超时秒数
EMBEDDING_TIMEOUT = 10  # Embedding 调用超时秒数
LLM_MAX_RETRIES = 1     # 失败重试次数
```

### 5.2 统一调用封装（`utils/llm_client.py`）

> V2 变更：集成 Langfuse Trace，所有 LLM/Embedding 调用自动上报追踪信息。

```python
import httpx
from config import LLM_TIMEOUT, EMBEDDING_TIMEOUT
from langfuse import Langfuse

langfuse = Langfuse()

class LLMClient:
    """统一 LLM/Embedding 调用封装，全局超时+异常捕获+Langfuse 追踪"""

    @staticmethod
    async def embed(texts: list[str], trace_id: str = None) -> list[list[float]]:
        trace = langfuse.trace(id=trace_id, name="embedding") if trace_id else None
        try:
            async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
                response = await client.post(
                    f"{BASE_URL}/embeddings",
                    json={"model": EMBEDDING_MODEL, "input": texts},
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                if response.status_code != 200:
                    raise Exception(f"Embedding API error: {response.status_code}")
                result = [item["embedding"] for item in response.json()["data"]]
                if trace:
                    trace.generation(
                        name="embed",
                        model=EMBEDDING_MODEL,
                        input=texts,
                        metadata={"count": len(texts), "dim": len(result[0])}
                    )
                return result
        except Exception as e:
            logger.error(f"Embedding 调用失败: {e}")
            raise EmbeddingServiceError("向量模型暂不可用，已切换关键词检索")

    @staticmethod
    async def chat(messages: list[dict], query: str = "", context: str = "", trace_id: str = None) -> str:
        trace = langfuse.trace(id=trace_id, name="chat") if trace_id else None
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                response = await client.post(
                    f"{BASE_URL}/chat/completions",
                    json={"model": LLM_MODEL, "messages": messages},
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                if response.status_code != 200:
                    raise Exception(f"LLM API error: {response.status_code}")
                content = response.json()["choices"][0]["message"]["content"]
                usage = response.json().get("usage", {})
                if trace:
                    trace.generation(
                        name="llm_chat",
                        model=LLM_MODEL,
                        input={"query": query, "context": context},
                        output=content,
                        usage=usage
                    )
                return content
        except httpx.TimeoutException:
            logger.error("LLM 调用超时")
            return "大模型服务暂时不可用，请稍后重试"
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return "大模型服务暂时不可用，请稍后重试"
```

### 5.3 降级策略速查

| 故障场景 | 降级行为 | 前端提示 |
|------|------|------|
| Embedding API 超时/失败 | 自动关闭向量检索，仅保留 BM25 全文检索 | "向量模型暂不可用，已切换关键词检索" |
| LLM API 超时/失败 | 返回固定兜底文案，不阻塞页面 | "大模型服务暂时不可用，请稍后重试" |
| Chroma 服务不可用 | 命中测试接口返回 5001 | "向量库服务异常，请联系管理员" |
| **文档未处理完成** | **命中测试/对话接口返回 4002** | **"文档正在处理中，请等待处理完成后再试"** |
| **用户越权访问** | **接口返回 403** | **"您无权访问该资源"** |

---

## 六、🔴 全局统一异常码契约

### 6.1 统一返回体

**成功返回：**
```json
{
  "code": 0,
  "msg": "success",
  "data": { }
}
```

**异常返回：**
```json
{
  "code": 400,
  "msg": "详细错误描述",
  "data": null
}
```

### 6.2 统一状态码规范（V2 新增 4001/4002/4003）

| code | 含义 | 触发场景 |
|:--:|------|------|
| 0 | 成功 | 所有正常返回 |
| 400 | 参数错误 | 必填字段为空、格式校验失败 |
| 401 | 未登录/Token 失效 | 未携带 Token 或 Token 过期 |
| 403 | 权限不足 | 无权限访问该接口或**跨用户组访问资源** |
| 404 | 资源不存在 | 知识库/文档 ID 不存在 |
| 500 | 服务内部异常 | 未预期的服务器错误 |
| 5001 | 向量库异常 | Chroma 连接失败/查询失败 |
| 5002 | 大模型调用异常 | LLM API 超时/Key 失效/返回异常 |
| **4001** | **用户组未授权** | **用户不在任何用户组中，或用户组未分配任何知识库** |
| **4002** | **文档未就绪** | **文档状态非 completed，不可用于检索（pending/processing/failed）** |
| **4003** | **白标配置缺失** | **系统品牌配置未初始化，使用默认值兜底** |

### 6.3 前端统一错误拦截（`utils/request.js`）

```javascript
// Axios 响应拦截器 — 全局统一错误处理
axios.interceptors.response.use(
  response => {
    const { code, msg } = response.data
    if (code === 0) return response.data
    if (code === 401) { /* 跳转登录页 */ }
    if (code === 4002) {
      // 文档未就绪，展示等待提示
      ElMessage.warning(msg || '文档正在处理中，请等待处理完成后再试')
      return Promise.reject(new Error(msg))
    }
    if (code === 403) {
      ElMessage.error(msg || '您无权访问该资源')
      return Promise.reject(new Error(msg))
    }
    ElMessage.error(msg || '请求失败')
    return Promise.reject(new Error(msg))
  },
  error => {
    ElMessage.error('网络异常，请检查服务状态')
    return Promise.reject(error)
  }
)
```

---

## 七、🔴 用户组权限与数据可见性隔离（V2 新增）

> **目标**：不同用户组只能查看和检索授权范围内的知识库与文档，防止越权访问。

### 7.1 数据模型

在 V1 的 6 张表基础上新增 2 张表：

```
┌─────────────┐         ┌──────────────────────┐
│  user_groups │         │  user_group_members   │
├─────────────┤         ├──────────────────────┤
│ id (PK)     │◄──┐    │ id (PK)               │
│ name        │   │    │ user_id (FK→users)    │
│ description │   │    │ group_id (FK→user_groups)│
│ created_at  │   │    │ created_at            │
└─────────────┘   │    └──────────────────────┘
                  │
                  │    ┌──────────────────────┐
                  └────│  kb_group_access      │
                       ├──────────────────────┤
                       │ id (PK)               │
                       │ kb_id (FK→knowledge_bases)│
                       │ group_id (FK→user_groups) │
                       │ created_at            │
                       └──────────────────────┘
```

**表结构定义：**

```sql
-- 用户组表
CREATE TABLE user_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户-用户组关联表（多对多）
CREATE TABLE user_group_members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id   INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, group_id)
);

-- 知识库-用户组授权表（多对多）
CREATE TABLE kb_group_access (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_id      INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    group_id   INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(kb_id, group_id)
);
```

### 7.2 权限规则

| 场景 | 规则 |
|------|------|
| 知识库列表 | 用户只能看到其所属用户组被授权的知识库 |
| 文档列表 | 文档列表先按知识库筛选，知识库受用户组权限约束 |
| 命中测试 | 只能选择有权限的知识库下的文档进行检索 |
| 智能对话 | 只能在有权限的知识库范围内提问 |
| 管理员 | 拥有 `role=admin` 的用户可查看所有资源（超管模式） |
| 未分配用户组 | 用户未加入任何用户组时，不可见任何知识库（返回 4001） |

### 7.3 权限中间件实现（`utils/permission.py`）

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

async def get_user_accessible_kb_ids(db: Session, user_id: int) -> list[int]:
    """获取用户可访问的知识库 ID 列表"""
    # 查询用户所属的所有用户组
    group_ids = db.query(UserGroupMember.group_id)\
        .filter(UserGroupMember.user_id == user_id).all()
    group_ids = [g[0] for g in group_ids]

    if not group_ids:
        return []  # 未分配用户组，无权限

    # 查询这些用户组被授权的知识库
    kb_ids = db.query(KbGroupAccess.kb_id)\
        .filter(KbGroupAccess.group_id.in_(group_ids)).all()
    return [k[0] for k in kb_ids]


async def require_kb_access(kb_id: int, user=Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """知识库访问权限校验依赖"""
    if user.role == "admin":
        return  # 管理员放行

    accessible_ids = await get_user_accessible_kb_ids(db, user.id)
    if kb_id not in accessible_ids:
        raise HTTPException(status_code=403, detail="您无权访问该知识库")
```

### 7.4 接口变更

| 接口 | V1 行为 | V2 行为 |
|------|------|------|
| `GET /api/knowledge-bases` | 返回全部知识库 | **仅返回当前用户组授权的知识库** |
| `GET /api/knowledge-bases/{kb_id}/documents` | 返回该 KB 下全部文档 | **先校验 KB 权限，再返回文档** |
| `POST /api/rag/test_retrieve` | 直接检索 | **先校验 KB + 文档权限，再检索** |
| `POST /api/chat/send` | 直接对话 | **先校验 KB 权限，再对话** |
| `POST /api/knowledge-bases` | 任何人可创建 | **创建时需指定授权的用户组** |
| **`GET /api/user-groups`** | — | **V2 新增：用户组列表** |
| **`POST /api/user-groups`** | — | **V2 新增：创建用户组** |
| **`POST /api/user-groups/{id}/members`** | — | **V2 新增：添加组成员** |
| **`POST /api/user-groups/{id}/kb-access`** | — | **V2 新增：授权知识库** |

### 7.5 前端联动

- **知识库管理页**：仅展示当前用户有权限的知识库卡片
- **命中测试页**：知识库下拉仅显示授权范围；文档下拉联动过滤
- **用户组管理页**（前端 A 新增）：管理用户组成员、授权知识库
- **用户管理页**：新增"所属用户组"多选字段

---

## 八、🔴 可观测性体系：日志管理 + Prometheus + Langfuse + 核心指标（V2 新增）

> **目标**：构建从基础设施到 LLM 调用的全链路可观测能力，支撑问题排查与效果优化。

### 8.1 架构总览

```
┌──────────────────────────────────────────────────────┐
│                    FastAPI 应用                        │
│                                                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ 结构化日志 │  │ Prometheus   │  │ Langfuse SDK   │  │
│  │ (loguru)  │  │ 指标埋点      │  │ LLM Trace      │  │
│  └────┬─────┘  └──────┬───────┘  └───────┬────────┘  │
│       │               │                  │            │
└───────┼───────────────┼──────────────────┼────────────┘
        │               │                  │
        ▼               ▼                  ▼
   日志文件         /metrics 端点      Langfuse Server
   (JSON 格式)      (Prometheus 抓取)   (Trace 可视化)
        │               │                  │
        ▼               ▼                  ▼
   日志归档         Grafana 看板      Langfuse Dashboard
```

### 8.2 结构化日志管理（`utils/logger.py`）

```python
from loguru import logger
import sys
import os

def setup_logger():
    """初始化结构化日志"""
    log_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(log_dir, exist_ok=True)

    # JSON 格式化输出
    logger.remove()
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[request_id]} | {message}",
        level="INFO"
    )
    logger.add(
        f"{log_dir}/rag_{{time:YYYY-MM-DD}}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[request_id]} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8"
    )
    return logger
```

**日志规范：**

| 日志级别 | 使用场景 |
|------|------|
| DEBUG | 切片详情、Embedding 向量维度、检索中间分数 |
| INFO | 接口请求/响应摘要、文档状态流转、用户操作 |
| WARNING | 降级触发（Embedding 失败切 BM25）、文档处理超时 |
| ERROR | LLM 调用失败、Chroma 连接异常、权限校验失败 |

**每条日志必须包含的上下文字段：**

```json
{
  "timestamp": "2026-07-16T12:00:00",
  "level": "INFO",
  "request_id": "req-uuid-xxx",
  "user_id": 1,
  "action": "test_retrieve",
  "kb_id": 3,
  "doc_id": 7,
  "search_type": "hybrid",
  "query": "如何配置...",
  "duration_ms": 850,
  "message": "检索完成，命中 3 条"
}
```

### 8.3 Prometheus 指标监控

#### 8.3.1 自动采集（HTTP 层）

使用 `prometheus-fastapi-instrumentator` 自动采集：

| 指标名 | 类型 | 说明 |
|------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数（按 method/path/status 标签） |
| `http_request_duration_seconds` | Histogram | HTTP 请求延迟分布 |
| `http_requests_in_progress` | Gauge | 当前进行中的请求数 |

#### 8.3.2 自定义业务指标（`utils/metrics.py`）

```python
from prometheus_client import Counter, Histogram, Gauge

# === RAG 检索指标 ===
rag_retrieve_total = Counter(
    "rag_retrieve_total",
    "RAG 检索请求总数",
    ["search_type", "kb_id"]
)

rag_retrieve_duration = Histogram(
    "rag_retrieve_duration_seconds",
    "RAG 检索耗时",
    ["search_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

rag_retrieve_hits = Histogram(
    "rag_retrieve_hits_count",
    "单次检索命中数量",
    buckets=[0, 1, 3, 5, 10, 20]
)

# === LLM 调用指标 ===
llm_call_total = Counter(
    "llm_call_total",
    "LLM 调用次数",
    ["model", "type"]  # type: chat / embedding
)

llm_call_duration = Histogram(
    "llm_call_duration_seconds",
    "LLM 调用耗时",
    ["model", "type"],
    buckets=[0.5, 1.0, 3.0, 5.0, 10.0, 30.0]
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM Token 消耗总量",
    ["model", "type"]  # type: prompt / completion
)

# === 文档处理指标 ===
doc_processing_duration = Histogram(
    "doc_processing_duration_seconds",
    "文档处理耗时（切片+向量化）",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

doc_status_gauge = Gauge(
    "doc_status_current",
    "各状态文档数量",
    ["status"]  # pending / processing / completed / failed
)

# === 系统指标 ===
active_users_gauge = Gauge(
    "active_users_current",
    "当前活跃用户数"
)
```

#### 8.3.3 指标暴露端点

```python
from prometheus_fastapi_instrumentator import Instrumentator

# main.py 中注册
Instrumentator.instrument(app).expose(app, endpoint="/metrics")
```

Prometheus 抓取配置（`prometheus.yml`）：

```yaml
scrape_configs:
  - job_name: 'rag-platform'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

### 8.4 Langfuse LLM 追踪

#### 8.4.1 集成方式

在 `utils/llm_client.py` 中已集成（见第五章 5.2 代码）。每次 LLM/Embedding 调用自动创建 Trace，记录：

| 追踪维度 | 记录内容 |
|------|------|
| Trace ID | 唯一标识，贯穿一次完整 RAG 链路 |
| 用户信息 | user_id、session_id |
| 检索阶段 | query、search_type、命中数量、各 chunk 分数 |
| LLM 阶段 | 输入 Prompt、输出内容、model、token 用量 |
| 延迟 | 各阶段耗时（检索 / LLM / 总链路） |
| 成本 | 按 model + token 估算费用 |

#### 8.4.2 RAG 链路追踪封装

```python
# rag_engine/rag_pipeline.py
from langfuse import Langfuse

langfuse = Langfuse()

class RAGPipeline:
    @staticmethod
    async def query(kb_id: int, query: str, search_type: str, user_id: int):
        """完整 RAG 链路，带 Langfuse 追踪"""
        trace = langfuse.trace(
            name="rag_query",
            user_id=str(user_id),
            metadata={"kb_id": kb_id, "search_type": search_type}
        )

        # 阶段 1：检索
        retrieval_span = trace.span(name="retrieval", input={"query": query})
        hits = await retriever.search(query, kb_id, search_type)
        retrieval_span.end(output={"hits_count": len(hits)})

        # 阶段 2：LLM 生成
        generation = trace.generation(
            name="llm_response",
            model=LLM_MODEL,
            input={"query": query, "context": hits},
        )
        answer = await llm_client.chat(messages, query=query, context=context)
        generation.end(output=answer, usage=usage)

        return answer, hits
```

### 8.5 核心指标看板（Grafana / Langfuse Dashboard）

#### 8.5.1 Prometheus + Grafana 核心指标

| 指标分类 | 指标名称 | 计算方式 | 告警阈值 |
|------|------|------|------|
| **可用性** | API 请求成功率 | `1 - (5xx / total)` | < 99% 触发告警 |
| **性能** | API P95 延迟 | `histogram_quantile(0.95, ...)` | > 3s 告警 |
| **性能** | 检索 P95 延迟 | `rag_retrieve_duration` P95 | > 2s 告警 |
| **性能** | LLM P95 延迟 | `llm_call_duration` P95 | > 8s 告警 |
| **业务** | 检索平均命中数 | `avg(rag_retrieve_hits)` | < 1 需排查 |
| **业务** | 文档处理成功率 | `completed / (completed+failed)` | < 95% 告警 |
| **资源** | Token 消耗速率 | `rate(llm_tokens_total[5m])` | 突增 3x 告警 |
| **资源** | 活跃用户数 | `active_users_current` | — |

#### 8.5.2 Langfuse 核心看板

| 看板模块 | 展示内容 |
|------|------|
| 查询分析 | 每日查询量趋势、热门 query TOP 10、零命中 query 列表 |
| 响应质量 | LLM 平均响应时长、Token 消耗趋势、成本估算 |
| Trace 浏览 | 按 query / user / 时间筛选，展开查看完整链路 |
| 检索效果 | 平均命中数、命中分数分布、各 search_type 对比 |

### 8.6 日志-指标-追踪关联

三个可观测维度通过 `request_id` 关联：

```
用户请求 → 生成 request_id（UUID）
  ├── 结构化日志：每条日志携带 request_id
  ├── Prometheus 指标：标签中携带 request_id（仅关键路径）
  └── Langfuse Trace：trace.id = request_id
```

**排查流程**：发现异常指标 → Grafana 看板定位时间点 → 查日志按 request_id 过滤 → Langfuse 看 Trace 详情。

---

## 九、🔴 白标定制（OEM）（V2 新增）

> **目标**：购买方可将系统名称、Logo、主题色等替换为自己公司的品牌元素，实现品牌私有化部署。

### 9.1 数据模型

新增系统配置表：

```sql
CREATE TABLE system_config (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key  TEXT NOT NULL UNIQUE,
    config_value TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**预置配置项：**

| config_key | 说明 | 默认值 |
|------|------|------|
| `brand_name` | 系统显示名称 | "RAG 智能知识平台" |
| `brand_logo_url` | Logo 图片 URL（支持本地路径或外链） | 内置默认 Logo |
| `brand_favicon_url` | 浏览器标签图标 URL | 内置默认 favicon |
| `brand_theme_color` | 主题色（HEX 格式，用于按钮/菜单高亮） | `#409EFF` |
| `brand_login_title` | 登录页标语 | "企业知识，智能问答" |
| `brand_footer_text` | 页脚文案 | "Powered by RAG Platform" |

### 9.2 后端接口

```
接口名称：获取品牌配置
请求方式：GET
路径：/api/system/branding
鉴权：无需鉴权（登录页也需要展示品牌信息）

成功返回：
{
  "code": 0,
  "msg": "success",
  "data": {
    "brand_name": "某企业智能知识平台",
    "brand_logo_url": "/uploads/branding/logo.png",
    "brand_favicon_url": "/uploads/branding/favicon.ico",
    "brand_theme_color": "#1890FF",
    "brand_login_title": "知识驱动，智能决策",
    "brand_footer_text": "© 2026 某企业"
  }
}
```

```
接口名称：更新品牌配置
请求方式：PUT
路径：/api/system/branding
鉴权：需要管理员权限

请求体（multipart/form-data）：
  brand_name: string
  brand_logo: File（可选，上传 Logo 图片）
  brand_theme_color: string
  brand_login_title: string
  brand_footer_text: string
```

### 9.3 前端动态渲染

#### 9.3.1 应用启动流程

```
App.vue mounted
  │
  ├── 1. 调用 GET /api/system/branding 获取品牌配置
  ├── 2. 存入 Pinia store（branding store），持久化到 localStorage
  ├── 3. 动态设置 document.title = brand_name
  ├── 4. 动态设置 <link rel="icon"> href = brand_favicon_url
  ├── 5. 动态设置 CSS 变量 --el-color-primary = brand_theme_color
  └── 6. 渲染布局（Logo、系统名称、页脚使用 store 中的值）
```

#### 9.3.2 Pinia 品牌配置 Store

```javascript
// stores/branding.js
import { defineStore } from 'pinia'
import { persist } from 'pinia-plugin-persistedstate'

export const useBrandingStore = defineStore('branding', {
  state: () => ({
    brand_name: 'RAG 智能知识平台',
    brand_logo_url: '',
    brand_favicon_url: '',
    brand_theme_color: '#409EFF',
    brand_login_title: '企业知识，智能问答',
    brand_footer_text: 'Powered by RAG Platform'
  }),
  actions: {
    async fetchBranding() {
      const res = await api.get('/api/system/branding')
      if (res.code === 0) {
        Object.assign(this, res.data)
        this.applyBranding()
      }
    },
    applyBranding() {
      // 设置标题
      document.title = this.brand_name
      // 设置 favicon
      const favicon = document.querySelector("link[rel='icon']")
      if (favicon && this.brand_favicon_url) {
        favicon.href = this.brand_favicon_url
      }
      // 设置主题色
      document.documentElement.style.setProperty(
        '--el-color-primary', this.brand_theme_color
      )
    }
  },
  persist: true  // 持久化到 localStorage，避免每次刷新闪烁
})
```

#### 9.3.3 品牌生效范围

| 页面区域 | 品牌元素 |
|------|------|
| 浏览器标签 | `brand_favicon_url` + `document.title` |
| 侧边栏顶部 | `brand_logo_url` + `brand_name` |
| 登录页 | `brand_logo_url` + `brand_name` + `brand_login_title` |
| 全局主题色 | `brand_theme_color`（按钮、菜单高亮、链接） |
| 页脚 | `brand_footer_text` |
| 对话窗口标题 | `brand_name` + "智能助手" |

### 9.4 品牌配置管理页面

前端 A 新增品牌配置入口（可集成在系统概览页的设置弹窗中，或独立页面）：

- 系统名称输入框
- Logo 上传组件（`el-upload`，支持 .png/.jpg/.svg，最大 2MB）
- 主题色选择器（`el-color-picker`）
- 登录页标语输入框
- 页脚文案输入框
- 实时预览面板
- 保存按钮 → 调用 `PUT /api/system/branding` → 刷新 store

### 9.5 文件存储

品牌资源文件存储在 `uploads/branding/` 目录下：

```
backend/uploads/branding/
├── logo.png
├── favicon.ico
└── ...
```

通过 FastAPI StaticFiles 暴露为静态资源：`/uploads/branding/{filename}`。

---

## 十、🔴 统一字段命名规范（V2 新增）

> **目标**：全局统一使用 `query` 作为检索/对话输入字段名，消除 `question`、`user_query`、`keyword`（检索场景）等混用问题。

### 10.1 命名规则

| 范围 | 规则 | 示例 |
|------|------|------|
| API 请求体 | 检索/对话输入字段统一为 `query` | `{"query": "如何配置..."}` |
| API 响应体 | 回显用户输入时使用 `query` | `{"query": "如何配置...", "hits": [...]}` |
| 提示词占位符 | 统一使用 `{{query}}` | `用户问题：{{query}}` |
| 前端变量 | 检索/对话输入绑定的变量使用 `query` | `const query = ref('')` |
| 后端函数参数 | 检索/对话函数的输入参数使用 `query` | `def search(query: str)` |
| 数据库字段 | 对话历史表中用户输入字段使用 `query` | `conversations.query TEXT` |
| Langfuse 追踪 | Trace 中用户输入字段使用 `query` | `trace.input = {"query": "..."}` |
| 日志上下文 | 日志中用户输入字段使用 `query` | `{"query": "如何配置..."}` |

### 10.2 V1 → V2 字段迁移

| 位置 | V1 字段名 | V2 字段名 | 状态 |
|------|------|------|:--:|
| `test_retrieve` 请求体 | `query` | `query` | ✅ V1 已统一 |
| `retrieve_rewrite.prompt` | `{{query}}` | `{{query}}` | ✅ V1 已统一 |
| `rag_chat.prompt` | `{{query}}` | `{{query}}` | ✅ V1 已统一 |
| `chat/send` 请求体 | `question` / `message` | **`query`** | 🔴 V2 修正 |
| 前端 ChatDialog 输入变量 | `question` / `inputText` | **`query`** | 🔴 V2 修正 |
| 后端对话函数参数 | `question` | **`query`** | 🔴 V2 修正 |
| conversations 表 | `message` / `content` | **`query`**（用户消息）/ `answer`（AI 回复） | 🔴 V2 修正 |

### 10.3 统一后的 API 契约示例

**命中测试接口（已统一）：**
```json
{
  "kb_id": "知识库ID",
  "doc_id": "文档ID",
  "search_type": "vector | keyword | hybrid",
  "query": "测试问题（必填）",
  "top_n": 3
}
```

**智能对话接口（V2 修正）：**
```json
{
  "kb_id": "知识库ID",
  "query": "用户提问内容（必填）",
  "session_id": "会话ID（可选，多轮对话）",
  "search_type": "hybrid"
}
```

> ⚠️ **注意区分**：用户管理模块中的搜索参数 `keyword` 是管理员搜索用户的关键词，属于管理后台 CRUD 范畴，不在本规范约束范围内。本规范仅约束 RAG 检索/对话链路中的用户查询输入。

---

## 十一、🔴 文档状态管控与检索准入机制（V2 新增）

> **目标**：文档未处理完成（切片+向量化）时不可被检索，用户在命中测试中选择未就绪文档时给出明确的等待提示。

### 11.1 文档状态流转

```
                    ┌──────────┐
    用户上传 ──────► │ pending  │
                    └────┬─────┘
                         │ 开始切片+向量化
                         ▼
                    ┌──────────┐
                    │processing│
                    └────┬─────┘
                    ╱         ╲
              成功 ╱            ╲ 失败
                 ╱               ╲
    ┌──────────┐              ┌──────────┐
    │completed │              │  failed  │
    └──────────┘              └──────────┘
         │                         │
    可检索 ✅                不可检索 ❌
                              可重试 → processing
```

### 11.2 检索准入规则

| 文档状态 | 命中测试 | 智能对话 | 文档下拉 |
|------|------|------|------|
| `pending` | ❌ 返回 4002 | ❌ 返回 4002 | 显示但禁用，标注"等待中" |
| `processing` | ❌ 返回 4002 | ❌ 返回 4002 | 显示但禁用，标注"处理中" |
| `completed` | ✅ 正常检索 | ✅ 正常对话 | 可选，标注"就绪" |
| `failed` | ❌ 返回 4002 | ❌ 返回 4002 | 显示但禁用，标注"失败"，提供重试 |

### 11.3 后端校验实现

```python
# api/rag.py
from fastapi import HTTPException

@router.post("/api/rag/test_retrieve")
async def test_retrieve(req: RetrieveRequest, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    # 1. 权限校验
    await require_kb_access(req.kb_id, user, db)

    # 2. 文档状态校验（V2 新增）
    doc = db.query(Document).filter(Document.id == req.doc_id).first()
    if not doc:
        return {"code": 404, "msg": "文档不存在", "data": None}

    if doc.status != "completed":
        status_text = {
            "pending": "等待处理",
            "processing": "正在处理中",
            "failed": "处理失败"
        }.get(doc.status, "未就绪")
        return {
            "code": 4002,
            "msg": f"文档「{doc.filename}」{status_text}，请等待处理完成后再试",
            "data": {"doc_id": doc.id, "status": doc.status}
        }

    # 3. 正常检索
    hits = await retriever.search(req.query, req.kb_id, req.doc_id, req.search_type, req.top_n)
    return {"code": 0, "msg": "success", "data": {"search_type": req.search_type, "total_hits": len(hits), "hits": hits}}
```

```python
# api/chat.py
@router.post("/api/chat/send")
async def chat_send(req: ChatRequest, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    # 1. 权限校验
    await require_kb_access(req.kb_id, user, db)

    # 2. 知识库下文档状态检查
    pending_docs = db.query(Document)\
        .filter(Document.kb_id == req.kb_id, Document.status != "completed").count()
    total_docs = db.query(Document).filter(Document.kb_id == req.kb_id).count()

    if total_docs == 0:
        return {"code": 404, "msg": "该知识库下暂无可用文档", "data": None}

    if pending_docs > 0 and total_docs == pending_docs:
        # 全部文档都未就绪
        return {
            "code": 4002,
            "msg": f"知识库下 {pending_docs} 篇文档正在处理中，请等待处理完成后再试",
            "data": None
        }

    # 3. 正常对话（仅检索 completed 文档）
    hits = await retriever.search(req.query, req.kb_id, search_type="hybrid")
    # ... 后续 LLM 生成
```

### 11.4 前端联动

#### 11.4.1 文档下拉禁用逻辑（HitTest.vue）

```javascript
// 文档下拉选项
const docOptions = computed(() => {
  return docList.value.map(doc => ({
    value: doc.id,
    label: doc.filename,
    disabled: doc.status !== 'completed',
    tag: {
      'pending': { text: '等待中', type: 'info' },
      'processing': { text: '处理中', type: 'warning' },
      'completed': { text: '就绪', type: 'success' },
      'failed': { text: '失败', type: 'danger' }
    }[doc.status]
  }))
})
```

```html
<!-- 文档选择下拉，禁用未就绪文档 -->
<el-select v-model="selectedDocId" placeholder="请选择文档">
  <el-option
    v-for="doc in docOptions"
    :key="doc.value"
    :value="doc.value"
    :label="doc.label"
    :disabled="doc.disabled"
  >
    <span>{{ doc.label }}</span>
    <el-tag size="small" :type="doc.tag.type" style="margin-left: 8px">
      {{ doc.tag.text }}
    </el-tag>
  </el-option>
</el-select>
```

#### 11.4.2 等待提示交互

```javascript
// 点击"运行测试"
async function runTest() {
  if (!selectedDocId.value) {
    ElMessage.warning('请选择目标文档')
    return
  }
  if (!query.value.trim()) {
    ElMessage.warning('请输入测试问题')
    return
  }

  const selectedDoc = docList.value.find(d => d.id === selectedDocId.value)
  if (selectedDoc && selectedDoc.status !== 'completed') {
    // 文档未就绪，展示等待提示
    const statusMap = {
      'pending': '等待处理',
      'processing': '正在处理中',
      'failed': '处理失败'
    }
    ElMessageBox.alert(
      `文档「${selectedDoc.filename}」当前状态为：${statusMap[selectedDoc.status]}。\n请等待文档处理完成后再进行命中测试。`,
      '文档未就绪',
      { confirmButtonText: '我知道了', type: 'warning' }
    )
    return
  }

  // 正常发起检索
  loading.value = true
  try {
    const res = await api.post('/api/rag/test_retrieve', {
      kb_id: selectedKbId.value,
      doc_id: selectedDocId.value,
      search_type: searchType.value,
      query: query.value,
      top_n: topN.value
    })
    if (res.code === 4002) {
      // 后端返回文档未就绪
      ElMessage.warning(res.msg)
      return
    }
    hitResults.value = res.data
  } finally {
    loading.value = false
  }
}
```

#### 11.4.3 文档管理页状态实时刷新

```javascript
// DocManage.vue — 自动轮询文档状态
let pollTimer = null

function startPolling() {
  pollTimer = setInterval(async () => {
    const hasProcessing = docList.value.some(
      d => d.status === 'pending' || d.status === 'processing'
    )
    if (hasProcessing) {
      await fetchDocList()  // 刷新文档列表
    } else {
      clearInterval(pollTimer)  // 全部完成，停止轮询
    }
  }, 3000)  // 每 3 秒轮询一次
}

onMounted(() => { startPolling() })
onUnmounted(() => { clearInterval(pollTimer) })
```

---

## 十二、命中率测试边界用例（V2 更新，测试直接使用）

| # | 边界场景 | 操作步骤 | 预期结果 |
|:--:|------|------|------|
| 1 | 未选择文档 | 知识库下拉已选，文档下拉留空，点击"运行测试" | 前端拦截，提示"请选择目标文档"，不发起请求 |
| 2 | 输入空问题 | 知识库+文档已选，问题输入框留空，点击"运行测试" | 前端拦截，提示"请输入测试问题"，不发起请求 |
| 3 | 检索无匹配 | 选择文档，输入一个与该文档内容完全无关的问题 | 返回 `code: 0, data: []`，前端展示空状态提示"未检索到相关内容" |
| 4 | 三种检索模式差异化 | 同一文档、同一问题，分别切换向量检索/全文检索/混合检索 | 三次返回结果排序不同：向量偏语义匹配、全文偏关键词匹配、混合检索融合排序 |
| 5 | 跨知识库隔离 | 知识库 A 中有文档 doc1，知识库 B 中无文档。选择知识库 B | 知识库 B 的下拉文档列表中不出现 doc1；无法跨库检索 |
| **6** | **文档未处理完成** | **上传一篇文档后立即在命中测试中选择该文档（status=processing），点击"运行测试"** | **前端弹出等待提示"文档正在处理中，请等待处理完成后再试"；后端返回 code: 4002** |
| **7** | **文档处理失败** | **将一篇文档状态标记为 failed，在命中测试中选择该文档，点击"运行测试"** | **前端弹出提示"文档处理失败，请重新上传或联系管理员"；下拉中该文档标注红色"失败"标签且禁用** |
| **8** | **跨用户组越权访问** | **用户 A 属于用户组 G1（授权知识库 KB1），用户 B 属于用户组 G2（授权知识库 KB2）。用户 A 尝试通过 API 直接访问 KB2 的文档** | **返回 code: 403，提示"您无权访问该知识库"；知识库列表中不出现 KB2** |
| **9** | **未分配用户组** | **新建用户但不分配任何用户组，登录后查看知识库列表** | **知识库列表为空，返回 code: 4001，提示"您尚未被分配到任何用户组，请联系管理员"** |

---

## 十三、Git 项目管理规范

### 13.1 分支策略

```
main ──────────────────── 稳定交付分支（只读保护）
  ▲
  │ PR（仅管理员，dev 稳定后）
  │
dev ───────────────────── 开发集成分支（组员不直接推）
  ▲         ▲
  │ PR      │ PR
  │         │
feature/A  feature/B ──── 个人功能分支
```

### 13.2 强制合并窗口（仅 2 次）

| 窗口 | 时间 | 规则 |
|:--:|------|------|
| 合并窗口 1 | Day1 19:00 | 全员将完成代码 push → 发起 PR → 合入 dev |
| 合并窗口 2 | Day2 12:00 | 最终全量合入 dev，准备下午联调演示 |

> 其余时间均在个人 feature 分支独立开发，**禁止随意合入 dev**。PR 合入前必须 `git pull origin dev` 解决冲突。

### 13.3 提交注释规范

```
feat: 新增命中率测试页面
fix: 修复文档下拉联动不同步
doc: 更新 API 契约文档
feat: 新增用户组权限中间件
feat: 集成 Langfuse LLM 追踪
feat: 新增白标品牌配置接口
fix: 文档未完成时可检索的问题
```

---

## 十四、需求优先级与砍需求决策底线（V2 更新）

| 优先级 | 功能 | 策略 |
|:--:|------|------|
| P0 必保 | 命中率测试（三种检索） | ❌ 不可砍，核心验收项 |
| P0 必保 | 知识库 + 文档管理 CRUD | ❌ 不可砍，命中测试依赖 |
| P0 必保 | 智能对话（RAG 问答） | ❌ 不可砍，项目核心价值 |
| **P0 必保** | **文档状态准入（未完成不可检索）** | **❌ 不可砍，数据正确性底线** |
| **P0 必保** | **统一字段命名 `query`** | **❌ 不可砍，契约规范，改动量极小** |
| **P0 必保** | **结构化日志（loguru）** | **❌ 不可砍，排查问题的基础设施** |
| **P1 可降级** | **用户组权限与数据隔离** | **✅ 降级方案：Day1 晚间完成表结构 + 基础中间件，若时间紧张则降级为"登录即管理员 + 知识库全局可见"，Day2 补全权限过滤** |
| **P1 可降级** | **Prometheus 指标监控** | **✅ 降级方案：仅保留 HTTP 自动指标（Instrumentator 默认），自定义业务指标 Day2 补充** |
| **P1 可降级** | **Langfuse LLM 追踪** | **✅ 降级方案：仅追踪对话接口（chat），命中测试的检索阶段暂不追踪** |
| **P1 可降级** | **白标定制** | **✅ 降级方案：仅实现品牌名称 + Logo 替换，主题色动态切换留二期** |
| P1 可降级 | 系统概览统计 | ✅ 降级为静态展示知识库数+文档数，调用次数留空壳 |
| P1 可降级 | 角色权限精细控制 | ✅ 降级为"登录即管理员"，角色页面 UI 保留 |
| P1 可降级 | 大模型管理页面 | ✅ 配置写死 `.env`，页面留空壳，二期再对接 |
| P2 可砍 | 数据导出 | ✅ 纯前端 CSV 导出（命中测试结果） |
| P2 可砍 | 对话历史记录 | ✅ 有条件触发：CP3 提前通过则启动 |
| **P2 可砍** | **Grafana 看板配置** | **✅ 提供 prometheus.yml + 指标文档，Grafana Dashboard JSON 留二期** |

---

## 十五、契约文件与提示词模板

### 15.1 API 契约示例（命中率测试接口）

```
接口名称：检索命中测试
请求方式：POST
路径：/api/rag/test_retrieve

请求体：
{
  "kb_id": "知识库ID（必填）",
  "doc_id": "文档ID（必填）",
  "search_type": "vector | keyword | hybrid（必填）",
  "query": "测试问题（必填）",
  "top_n": 3
}

成功返回：
{
  "code": 0,
  "msg": "success",
  "data": {
    "search_type": "hybrid",
    "total_hits": 2,
    "hits": [
      {
        "chunk_id": "c001",
        "content": "命中分片原文...",
        "score": 0.86,
        "source_doc": "文档名称.md",
        "doc_id": "doc001"
      }
    ]
  }
}

异常返回（文档未就绪）：
{
  "code": 4002,
  "msg": "文档「xxx.md」正在处理中，请等待处理完成后再试",
  "data": {"doc_id": 7, "status": "processing"}
}

异常返回（越权访问）：
{
  "code": 403,
  "msg": "您无权访问该知识库",
  "data": null
}

异常返回（参数错误）：
{
  "code": 400,
  "msg": "缺少必填参数: query",
  "data": null
}
```

> ⚠️ 本章 JSON 示例为示意，完整接口定义以 `docs/api_contract.md` 为准。

### 15.2 智能对话接口（V2 修正字段命名）

```
接口名称：智能对话
请求方式：POST
路径：/api/chat/send

请求体：
{
  "kb_id": "知识库ID（必填）",
  "query": "用户提问内容（必填）",
  "session_id": "会话ID（可选，多轮对话时传入）",
  "search_type": "hybrid（默认混合检索）"
}

成功返回：
{
  "code": 0,
  "msg": "success",
  "data": {
    "answer": "AI 回复内容...",
    "query": "用户原始提问",
    "session_id": "会话ID",
    "references": [
      {
        "chunk_id": "c001",
        "content": "引用片段...",
        "score": 0.86,
        "source_doc": "文档名称.md"
      }
    ]
  }
}
```

### 15.3 系统品牌配置接口（V2 新增）

```
接口名称：获取品牌配置
请求方式：GET
路径：/api/system/branding
鉴权：无需鉴权

成功返回：
{
  "code": 0,
  "msg": "success",
  "data": {
    "brand_name": "某企业智能知识平台",
    "brand_logo_url": "/uploads/branding/logo.png",
    "brand_favicon_url": "/uploads/branding/favicon.ico",
    "brand_theme_color": "#1890FF",
    "brand_login_title": "知识驱动，智能决策",
    "brand_footer_text": "© 2026 某企业"
  }
}
```

### 15.4 提示词模板

**检索改写提示词（`prompts/retrieve_rewrite.prompt`）：**

```
你是查询优化助手，根据用户原始问题，拆解出3个细分检索关键词，用于知识库检索，只输出关键词列表，不要多余描述。

用户问题：{{query}}
```

**RAG 对话提示词（`prompts/rag_chat.prompt`）：**

```
# 对话历史
{{chat_history}}

# 角色
你是知识库专属问答助手，仅基于下方参考文档回答用户问题，禁止编造文档外内容。

# 参考知识库片段
{{context_chunks}}

# 用户问题
{{query}}

# 约束
1. 如果参考文档无对应信息，直接回复：当前知识库未查询到相关内容。
2. 回答条理清晰，引用文档原文片段。
3. 禁止脱离参考内容进行拓展猜测。
4. 回答语言与用户问题语言保持一致。
5. 如果结果中给出了多个来源，在下文依次列出每个来源的出处。
```

### 15.5 各角色开工提示词（Day1 上午坐下即用）

> 以下 5 份提示词面向具体执行人员，每人拿到后可直接开始编码，不再需要从方案各处拼凑信息。
> 项目负责人自身不需要提示词（你是写这些的人）。

---

#### 后端 A（3号）— RAG 核心引擎 + Langfuse 集成

```
═══════════════════════════════════════════
  后端 A · RAG 核心引擎 + Langfuse · 开工提示词
═══════════════════════════════════════════

【你的身份】
你是整个项目的算法核心。检索质量、对话效果、向量库稳定性全看你的代码。
V2 新增：你还要负责 Langfuse LLM 追踪集成，让每次检索和对话都有完整的 Trace。

【技术栈】
- Python 3.10+ / FastAPI / SQLAlchemy / ChromaDB (HTTP Client)
- OpenAI SDK: text-embedding-3-small (1536维) + gpt-4o-mini
- 切片库: langchain.text_splitter.RecursiveCharacterTextSplitter
- 全文检索: rank-bm25 库
- V2 新增: langfuse Python SDK（LLM 全链路追踪）

【开工第一步 — 环境检查】
cd backend
cp ../.env.example ../.env    # 然后填入你的 API Key + Langfuse Key
# 确认 .env 中 ENV=dev-你的姓名拼音
pip install -r requirements.txt
# 确认 Chroma 服务已启动: curl http://localhost:8000/api/v1/heartbeat
# 确认 Langfuse SDK 可用: python -c "from langfuse import Langfuse; print('ok')"

【你的专属文件清单】
backend/app/
├── config.py              # 全局配置（切片参数、模型名、超时、Langfuse）
├── api/
│   ├── rag.py             # 命中测试接口 POST /api/rag/test_retrieve
│   └── chat.py            # 对话接口 POST /api/chat/send + /api/chat/stream
├── rag_engine/
│   ├── splitter.py        # 文档切片
│   ├── embedder.py        # Embedding 向量化（集成 Langfuse Trace）
│   ├── retriever.py       # 三种检索
│   ├── generator.py       # LLM 对话生成（集成 Langfuse Trace）
│   └── rag_pipeline.py    # V2 新增：RAG 全链路 + Langfuse 追踪封装
├── utils/
│   └── llm_client.py      # LLM/Embedding 统一封装（超时+熔断+Langfuse）
└── prompts/
    ├── retrieve_rewrite.prompt
    └── rag_chat.prompt

⚠️ 不要碰的文件（归 4 号）：auth.py、users.py、roles.py、kb.py、docs.py、models.py、
   permission.py、branding.py、metrics.py、logger.py

【命名规范 — V2 强制】
- 所有检索/对话输入参数统一命名为 query（不要用 question/message/input_text）
- 提示词占位符统一 {{query}}
- Langfuse Trace 中用户输入字段用 query

【Day1 上午任务】

09:00-10:00 → 建骨架
  - config.py 写入:
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIM = 1536
    LLM_MODEL = "gpt-4o-mini"
    HYBRID_ALPHA = 0.7
    LLM_TIMEOUT = 10
    EMBEDDING_TIMEOUT = 10
    # V2 新增
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
  - db/models.py（8 张表，V2 新增 user_groups + user_group_members + kb_group_access + system_config）
  - rag_engine/ 目录 + 五个空 .py 文件

10:00-12:00 → 核心工具类 + Langfuse 初始化
  - 写 embedder.py：封装 OpenAI Embedding API
  - 写 splitter.py：RecursiveCharacterTextSplitter
  - 写 llm_client.py：统一封装，10s 超时 + Langfuse Trace（参考方案 Section 5.2 代码）
  - 初始化 Langfuse: langfuse = Langfuse()

【Day1 下午任务】

13:00-14:00 → 主动脉串通
  - 文档上传后：切片 → embedder → 写 Chroma → 写 chunks 表
  - V2 新增：文档状态校验 — 只有 status=completed 的文档可检索

14:00-15:00 → 命中测试接口
  - POST /api/rag/test_retrieve
  - 请求体: {kb_id, doc_id, search_type, query, top_n}
  - V2 新增：文档状态校验 — 非 completed 返回 code: 4002
  - V2 新增：权限校验 — 调用 require_kb_access(kb_id)

15:00-19:00 → 智能对话 + 熔断降级 + Langfuse 追踪
  - POST /api/chat/send: query 字段名（不要用 question）
  - POST /api/chat/stream: SSE 流式
  - V2 新增：rag_pipeline.py — 封装完整 RAG 链路，每步创建 Langfuse Trace/Span
  - 降级实现同 V1

【Day2 任务】
- 上午: SSE 完善 + Langfuse 对话 Trace + Token 用量上报 + 与前端 B 对接
- 下午: bug 修复 + 检索速度优化

【关键参数速查】
- chunk_size=500, overlap=50, alpha=0.7, embedding_dim=1536
- 字段命名: 统一 query
- 文档状态准入: 非 completed → code 4002
- Langfuse: 每次 chat 创建 trace，记录 query/answer/usage/cost

【遇到问题时】
- 30 分钟内搞不定 → @6号
- Langfuse 连不上 → 检查 .env 中 Key 和 Host，降级方案：不追踪不影响功能
- API Key 报错 → 找 6 号
```

---

#### 后端 B（4号）— 业务 CRUD + 鉴权 + 用户组权限 + 白标 + 监控

```
═══════════════════════════════════════════
  后端 B · CRUD + 鉴权 + 权限 + 白标 + 监控 · 开工提示词
═══════════════════════════════════════════

【你的身份】
你是项目的数据底座。V2 给你加了不少活：用户组权限体系、白标配置、Prometheus 指标、结构化日志。
但别慌，大部分是模板代码，照着方案抄就行。

【技术栈】
- Python 3.10+ / FastAPI / SQLAlchemy / SQLite
- JWT: python-jose + passlib[bcrypt]
- V2 新增: loguru（结构化日志）
- V2 新增: prometheus-fastapi-instrumentator（指标监控）

【你的专属文件清单】
backend/app/
├── api/
│   ├── auth.py             # 登录鉴权
│   ├── users.py            # 用户管理
│   ├── roles.py            # 角色管理
│   ├── kb.py               # 知识库管理（V2: 加用户组过滤）
│   ├── docs.py             # 文档管理+上传（V2: 加权限校验）
│   ├── models.py           # 大模型管理
│   ├── user_groups.py      # V2 新增：用户组 CRUD + 成员管理 + 授权管理
│   └── branding.py         # V2 新增：白标配置 GET/PUT
├── db/
│   ├── models.py           # 数据模型（V2: 8 张表，新增 4 张）
│   └── database.py         # 数据库连接
├── utils/
│   ├── auth.py             # JWT
│   ├── permission.py       # V2 新增：权限中间件
│   ├── logger.py           # V2 新增：结构化日志
│   └── metrics.py          # V2 新增：Prometheus 自定义指标
└── schema/

⚠️ 不要碰的文件（归 3 号）：rag.py、chat.py、rag_engine/、llm_client.py

【Day1 上午任务】

09:00-10:00 → 建骨架 + 日志
  - database.py: SQLite 连接
  - db/models.py: 8 张表
    V1 原有: roles, users, knowledge_bases, documents, chunks, model_configs
    V2 新增: user_groups, user_group_members, kb_group_access, system_config
  - utils/logger.py: loguru 结构化日志（参考方案 Section 8.2 代码）
  - utils/metrics.py: Prometheus 自定义指标定义（参考方案 Section 8.3.2 代码）

10:00-11:00 → 鉴权 + 用户 CRUD + 用户组 CRUD
  - utils/auth.py: JWT 签发 + 校验
  - api/auth.py: 登录接口
  - api/users.py: 用户 CRUD（V2: 新增"所属用户组"字段）
  - api/user_groups.py: V2 新增
    GET /api/user-groups（列表）
    POST /api/user-groups（创建）
    POST /api/user-groups/{id}/members（添加成员）
    POST /api/user-groups/{id}/kb-access（授权知识库）

11:00-12:00 → 权限中间件 + 白标配置
  - utils/permission.py: 参考方案 Section 7.3 代码
    get_user_accessible_kb_ids(db, user_id) → list[int]
    require_kb_access(kb_id, user, db) → 依赖注入
  - api/branding.py: V2 新增
    GET /api/system/branding（公开，无需鉴权）
    PUT /api/system/branding（管理员权限）
  - 初始化 system_config 表默认值

【Day1 下午任务】

13:00-14:00 → 文档上传 + 知识库 CRUD（加权限过滤）
  - kb.py: GET 列表加用户组过滤（非 admin 用户只返回授权 KB）
  - docs.py: 上传 + 列表 + 删除（加权限校验）
  - main.py: 注册 Prometheus Instrumentator + 日志中间件

14:00-16:00 → 补全接口
  - GET /api/dashboard/stats
  - GET /api/models
  - GET /api/documents/all

16:00-19:00 → 联调 + 权限完善
  - 所有 KB/文档接口加 require_kb_access 依赖
  - CORS 配置
  - 与前端 A/B 对接

【Day2 任务】
- 上午: 权限拦截完善 + Prometheus 自定义指标埋点 + 白标联调
- 下午: bug 修复 + 监控指标校验

【关键参数速查】
- 状态码: 0/400/401/403/404/4001/4002/4003/500/5001/5002
- 权限规则: admin 放行；非 admin 只看授权 KB
- 白标: GET 公开 / PUT 需 admin
- Prometheus: /metrics 端点，Instrumentator 自动 + 自定义业务指标

【遇到问题时】
- 30 分钟搞不定 → @6号
- 3 号的方法不知道怎么调 → 拉 3 号对参数
- 权限逻辑不确定 → 对照方案 Section 7.2 权限规则表
```

---

#### 前端 A（1号）— 管理后台 5 页 + 白标渲染

```
═══════════════════════════════════════════
  前端 A · 管理后台 5 页 + 白标渲染 · 开工提示词
═══════════════════════════════════════════

【你的身份】
你负责管理后台侧全部页面。V2 给你加了用户组管理页和白标动态渲染。
白标渲染是重点——App 启动时第一件事就是拉品牌配置。

【技术栈】
- Vue 3 + Vite + Composition API
- Element Plus
- Pinia + pinia-plugin-persistedstate（V2 新增，持久化品牌配置）
- Axios 封装

【你的专属文件清单】
frontend/src/
├── views/
│   ├── Dashboard.vue       # 系统概览
│   ├── RoleManage.vue      # 角色管理
│   ├── UserManage.vue      # 用户管理（V2: 加用户组多选）
│   ├── UserGroupManage.vue # V2 新增：用户组管理
│   ├── ModelManage.vue     # 大模型管理
│   └── BrandingConfig.vue  # V2 新增：品牌配置页（可合并到 Dashboard 弹窗）
├── stores/
│   ├── user.js             # 用户状态
│   └── branding.js         # V2 新增：品牌配置 Store
├── router/index.js
└── utils/request.js

【Day1 上午任务】

09:00-10:00 → 全局布局 + 白标初始化
  - 路由配置（5 个管理页 + 品牌配置入口）
  - 写 stores/branding.js: 参考方案 Section 9.3.2 代码
  - App.vue mounted 中调用 branding.fetchBranding()
  - 写 utils/request.js: 拦截器（参考 Section 6.3，加 4002/4003 处理）

10:00-12:00 → 系统概览 + 角色管理 + 用户管理
  - Dashboard.vue
  - RoleManage.vue
  - UserManage.vue（V2: 新增"所属用户组"多选 el-select）

【Day1 下午任务】

13:00-14:00 → 用户组管理页（V2 新增）
  - UserGroupManage.vue:
    ① 用户组列表（el-table: 名称/描述/成员数/授权知识库数）
    ② 创建/编辑弹窗
    ③ 成员管理弹窗（添加/移除用户）
    ④ 知识库授权弹窗（el-transfer 穿梭框）

14:00-15:00 → 大模型管理页 + 品牌配置入口
  - ModelManage.vue（数据写死）
  - BrandingConfig.vue 或 Dashboard 设置弹窗:
    系统名称 + Logo 上传 + 主题色选择器 + 登录标语 + 页脚文案 + 实时预览

15:00-19:00 → 真实接口对接
  - 全部管理接口对接
  - V2: 白标配置 PUT 接口对接 + 刷新 store
  - V2: 用户组接口对接

【Day2 任务】
- 上午: 联调 + 白标切换验证（改名称/Logo/颜色后全站生效）
- 下午: 样式统一 + bug 修复

【关键参数速查】
- 品牌配置: App 启动时 GET /api/system/branding → store → 全站渲染
- 主题色: document.documentElement.style.setProperty('--el-color-primary', color)
- 用户组管理: el-transfer 穿梭框用于知识库授权
```

---

#### 前端 B（2号）— RAG 核心页面 4 页 + 文档状态联动

```
═══════════════════════════════════════════
  前端 B · RAG 核心页面 + 文档状态联动 · 开工提示词
═══════════════════════════════════════════

【你的身份】
你负责项目最核心的 RAG 交互页面。V2 新增文档状态联动——未完成文档不可检索，
用户点命中测试时要给等待提示。这是用户体验的关键细节。

【技术栈】
- Vue 3 + Vite + Composition API
- Element Plus（el-upload / el-select / el-cascader / el-tag）
- Axios + EventSource（SSE）

【你的专属文件清单】
frontend/src/
├── views/
│   ├── KbManage.vue        # 知识库管理（V2: 仅显示有权限的 KB）
│   ├── DocManage.vue       # 文档管理（V2: 状态轮询自动刷新）
│   ├── HitTest.vue         # 命中率测试（V2: 文档状态禁用 + 等待提示）
│   └── ChatDialog.vue      # 智能对话
├── api/rag.js              # RAG 接口封装
└── mock/mock_data_B.json

【命名规范 — V2 强制】
- 命中测试输入框绑定变量: query（不要用 question/inputText）
- 对话输入框绑定变量: query
- API 请求体字段: query

【Day1 上午任务】

09:00-11:00 → 知识库管理 + 文档管理
  - KbManage.vue（V2: 知识库列表来自后端，已按权限过滤）
  - DocManage.vue:
    ① el-upload 上传
    ② 文档列表（V2: 状态标签 pending=灰/processing=蓝/completed=绿/failed=红）
    ③ V2 新增: 状态自动轮询（每 3 秒检查 pending/processing 文档，参考 Section 11.4.3）

11:00-12:00 → 命中率测试页 UI
  - HitTest.vue:
    ① 级联选择: 知识库 → 文档（联动）
    ② V2 新增: 文档下拉中非 completed 文档禁用 + 状态标签（参考 Section 11.4.1）
    ③ 检索方式切换（el-radio-group）
    ④ 问题输入框（变量名: query）
    ⑤ top_n 滑块
    ⑥ "运行测试"按钮
    ⑦ V2 新增: 点击运行时检查文档状态，未就绪弹出等待提示（参考 Section 11.4.2）

【Day1 下午任务】

13:00-15:00 → 命中测试对接 + 智能对话
  - 命中测试: POST /api/rag/test_retrieve
    请求: {kb_id, doc_id, search_type, query, top_n}
    V2: 处理 code=4002（文档未就绪）和 code=403（越权）
  - 智能对话: ChatDialog.vue
    输入变量: query
    POST /api/chat/send + /api/chat/stream

15:00-19:00 → 流式对话 + 三种检索切换
  - SSE EventSource 流式渲染
  - SSE 断连 → 非流式兜底

【Day2 任务】
- 上午: 真实接口全面对接 + 文档状态联动联调
- 下午: 流式渲染优化 + bug 修复

【关键参数速查】
- 字段命名: query（统一）
- 文档状态: pending/processing/completed/failed
- 文档未就绪: 前端拦截提示 + 后端返回 4002
- 检索方式: vector / keyword / hybrid
- SSE 事件: start / chunk / done
```

---

#### 测试工程师（5号）

```
═══════════════════════════════════════════
  测试工程师 · 全流程质量保障 · 开工提示词
═══════════════════════════════════════════

【你的身份】
你是项目的质量守门员。V2 新增了权限越权和文档状态两个专项测试，
这两个是核心安全/正确性场景，必须覆盖。

【V2 新增测试模块】

【用户组权限模块 — 越权专项】
- TC-P01: 用户 A（组 G1，授权 KB1）登录 → 知识库列表仅显示 KB1 ✅
- TC-P02: 用户 A 尝试 GET /api/knowledge-bases/{KB2_id}/documents → 期望 403
- TC-P03: 用户 A 尝试 POST /api/rag/test_retrieve 传 KB2 的 kb_id → 期望 403
- TC-P04: 用户 A 尝试 POST /api/chat/send 传 KB2 的 kb_id → 期望 403
- TC-P05: 未分配用户组的用户登录 → 知识库列表为空，期望 4001
- TC-P06: admin 用户登录 → 可查看所有知识库（超管模式）

【文档状态准入模块 — 状态专项】
- TC-S01: 上传文档后立即命中测试（status=pending）→ 期望 4002 + 等待提示
- TC-S02: 文档处理中命中测试（status=processing）→ 期望 4002
- TC-S03: 文档处理完成后命中测试（status=completed）→ 期望正常检索
- TC-S04: 文档处理失败后命中测试（status=failed）→ 期望 4002 + 失败提示
- TC-S05: 文档下拉中非 completed 文档禁用 + 状态标签显示正确
- TC-S06: 知识库下全部文档未就绪时对话 → 期望 4002

【白标定制模块】
- TC-B01: GET /api/system/branding（未登录）→ 期望 200 + 品牌配置
- TC-B02: PUT /api/system/branding（管理员）→ 期望 200 + 配置更新
- TC-B03: PUT /api/system/branding（普通用户）→ 期望 403
- TC-B04: 修改品牌名称 → 前端全站标题更新
- TC-B05: 修改主题色 → 前端按钮/菜单颜色更新
- TC-B06: 上传新 Logo → 侧边栏 + 登录页 Logo 更新

【可观测性验证】
- TC-O01: 访问 /metrics 端点 → 期望返回 Prometheus 格式指标
- TC-O02: 发起命中测试 → /metrics 中 rag_retrieve_total 增加
- TC-O03: 发起对话 → /metrics 中 llm_call_total 增加
- TC-O04: 查看日志文件 → 期望 JSON 格式 + request_id 关联
- TC-O05: Langfuse Dashboard → 期望看到对话 Trace（query → answer → usage）

【V1 原有测试用例保持不变】
- 鉴权模块: TC-A01~A04
- 用户管理: TC-U01~U06
- 角色管理: TC-R01~R02
- 知识库模块: TC-K01~K02
- 文档管理: TC-D01~D04
- 命中测试: TC-H01~H05 + V2 新增 TC-H06~H09（见 Section 12）
- 智能对话: TC-C01~C03
- 降级测试: TC-F01~F02

【Day2 全流程串联测试（CP3 核心！）】
完整走通:
1. 登录（admin）→ 配置品牌名称/Logo
2. 创建用户组 G1 → 添加用户 A → 授权知识库 KB1
3. 创建知识库 KB1 → 上传文档 → 等待处理完成
4. 切换用户 A 登录 → 知识库列表仅显示 KB1
5. 命中测试（三种检索各一次）→ 查看结果 + Langfuse Trace
6. 智能对话提问 → 查看回复 + 引用
7. 上传新文档 → 立即命中测试 → 验证 4002 等待提示
8. 用户 A 尝试访问不存在的 KB2 → 验证 403
9. 检查 /metrics 指标 + 日志文件

【Bug 严重级别定义】
- P0 阻塞: 核心功能不可用、权限绕过、文档未完成可检索
- P1 严重: 功能可用但结果错误、白标不生效、监控缺失
- P2 一般: UI 显示问题、交互体验问题
- P3 建议: 文案优化、样式微调
```

---

## 十六、项目目录结构（V2 终稿）

```
rag-platform/
├── backend/
│   ├── app/
│   │   ├── api/              # 接口层
│   │   │   ├── auth.py       # 登录鉴权（后端 B）
│   │   │   ├── users.py      # 用户管理（后端 B）
│   │   │   ├── roles.py      # 角色管理（后端 B）
│   │   │   ├── user_groups.py # V2 新增：用户组管理（后端 B）
│   │   │   ├── kb.py         # 知识库管理（后端 B，V2: 加权限过滤）
│   │   │   ├── docs.py       # 文档管理+上传（后端 B，V2: 加权限校验）
│   │   │   ├── models.py     # 大模型管理（后端 B）
│   │   │   ├── branding.py   # V2 新增：白标配置（后端 B）
│   │   │   ├── rag.py        # 命中测试+检索（后端 A，V2: 加状态校验）
│   │   │   └── chat.py       # 智能对话（后端 A，V2: 字段改 query）
│   │   ├── rag_engine/       # RAG 核心引擎（后端 A）
│   │   │   ├── splitter.py   # 文档切片
│   │   │   ├── embedder.py   # Embedding 向量化
│   │   │   ├── retriever.py  # 三种检索实现
│   │   │   ├── generator.py  # LLM 对话生成
│   │   │   └── rag_pipeline.py # V2 新增：RAG 全链路 + Langfuse 追踪
│   │   ├── db/
│   │   │   ├── models.py     # SQLAlchemy 数据模型（V2: 8 张表）
│   │   │   └── database.py   # 数据库连接
│   │   ├── schema/           # Pydantic 请求/响应模型
│   │   ├── utils/
│   │   │   ├── llm_client.py # LLM/Embedding 封装（超时+熔断+Langfuse）
│   │   │   ├── auth.py       # JWT 签发+校验
│   │   │   ├── permission.py # V2 新增：权限中间件
│   │   │   ├── logger.py     # V2 新增：结构化日志
│   │   │   └── metrics.py    # V2 新增：Prometheus 自定义指标
│   │   ├── config.py         # 全局配置
│   │   └── main.py           # FastAPI 入口（V2: 注册 Instrumentator + 日志）
│   ├── prompts/              # 提示词模板
│   │   ├── retrieve_rewrite.prompt
│   │   └── rag_chat.prompt
│   ├── logs/                 # V2 新增：日志文件目录（gitignore）
│   ├── uploads/
│   │   └── branding/         # V2 新增：品牌资源文件目录
│   ├── chroma_data/          # 向量库持久化（gitignore）
│   ├── requirements.txt      # V2: 追加 loguru/prometheus/langfuse
│   └── .env.example          # V2: 追加 Langfuse/Prometheus 配置
├── frontend/
│   ├── src/
│   │   ├── views/            # 页面
│   │   │   ├── Dashboard.vue       # 系统概览（前端 A）
│   │   │   ├── RoleManage.vue      # 角色管理（前端 A）
│   │   │   ├── UserManage.vue      # 用户管理（前端 A，V2: 加用户组字段）
│   │   │   ├── UserGroupManage.vue # V2 新增：用户组管理（前端 A）
│   │   │   ├── ModelManage.vue     # 大模型管理（前端 A）
│   │   │   ├── BrandingConfig.vue  # V2 新增：品牌配置（前端 A）
│   │   │   ├── KbManage.vue        # 知识库管理（前端 B）
│   │   │   ├── DocManage.vue       # 文档管理（前端 B，V2: 状态轮询）
│   │   │   ├── HitTest.vue         # 命中率测试（前端 B，V2: 文档状态禁用）
│   │   │   └── ChatDialog.vue      # 智能对话（前端 B，V2: 字段改 query）
│   │   ├── components/       # 公共组件
│   │   ├── api/              # 接口封装 + Mock 数据
│   │   ├── router/           # 路由配置
│   │   ├── stores/           # Pinia 状态管理
│   │   │   ├── user.js       # 用户状态
│   │   │   └── branding.js   # V2 新增：品牌配置 Store
│   │   └── utils/            # 工具函数 + Axios 封装
│   ├── package.json          # V2: 追加 pinia-plugin-persistedstate
│   └── vite.config.js
├── docs/                     # 所有规范文档
│   ├── api_contract.md       # API 契约（V2: 新增用户组/品牌接口 + query 统一）
│   ├── db_schema.md          # 数据库设计（V2: 新增 4 张表）
│   ├── 2天项目排期表.md
│   ├── 风险与预案清单.md
│   ├── 交付验收标准.md
│   ├── 演示操作流程.md
│   ├── monitoring_guide.md   # V2 新增：监控配置指南
│   ├── 测试用例/
│   └── meeting/              # 每日会议纪要
├── demo-materials/           # 演示素材
│   ├── 测试文档1.md
│   ├── 测试文档2.md
│   ├── 测试文档3.md
│   └── 标准测试问题集.md
├── scripts/
│   ├── start_all.sh          # 一键启动 Chroma + 后端 + 前端
│   ├── start_all.bat
│   ├── init_db.py            # 数据库初始化（V2: 含用户组+系统配置预置数据）
│   └── start_langfuse.sh     # V2 新增：启动 Langfuse 服务
├── .gitignore
├── README.md
└── Git分支管理规范.md
```

---

## 十七、项目负责人 Day1 上午必做清单（V2 更新）

- [ ] 1. GitHub 仓库创建，按上述目录结构提交脚手架，全员 clone
- [ ] 2. 定死 Embedding 模型和向量维度（1536），写入 `config.py`
- [ ] 3. 定死切片参数（chunk_size=500, overlap=50），写入 `config.py`
- [ ] 4. 输出 `api_contract.md`（包含命中测试 + 对话 + **用户组 + 品牌配置**接口 + 统一异常码）
- [ ] 5. 输出 `db_schema.md`（**8 张表**：V1 原有 6 张 + V2 新增 user_groups + user_group_members + kb_group_access + system_config）
- [ ] 6. 输出 Mock 数据 JSON（前端 A 和 B 各一份，**含用户组 + 品牌配置 Mock**）
- [ ] 7. 输出 `.env.example`（含 `ENV` 环境隔离 + **Langfuse + Prometheus** 配置）
- [ ] 8. 确认 6 人 API Key 可用，余额充足
- [ ] 9. 输出 `2天项目排期表.md`（按小时拆分，**含 V2 新增任务分配**）
- [ ] 10. 启动 Chroma HTTP 服务模式，确认全员可连接
- [ ] 11. 输出 `风险与预案清单.md`（含环境隔离、熔断降级、混合检索、边界用例、**权限越权、文档状态准入**）
- [ ] 12. 准备 3 篇演示 md 文档 + 10 条标准测试问题
- [ ] **13. V2 新增：输出 `monitoring_guide.md`（Langfuse 部署 + Prometheus 配置 + Grafana 指标说明）**
- [ ] **14. V2 新增：确认 `query` 字段命名规范已写入 `api_contract.md` 并全员通知**
- [ ] **15. V2 新增：预置 system_config 表默认品牌数据 + 初始化一个 admin 用户组**

---

## 附录：变更记录

| 版本 | 变更内容 |
|:--:|------|
| v1.0 | 原始评审方案（8 技术盲区 + 5 流程缺口） |
| v2.0（V1） | 合并四项增量：① 多人环境物理隔离 ② LLM/Embedding 超时熔断降级 ③ 全局统一异常码契约 ④ 命中率测试 5 大边界用例；前端工作量重新分配；Git 合并窗口精简为 2 次 |
| v2.1（V1） | 多轮对话功能落地；数据导出纯前端 CSV 方案 |
| v2.2（V1） | 契约格式对齐；变量名统一 {{user_query}} → {{query}} |
| **V2** | **合并五项增量：① 用户组权限与数据可见性隔离（第七章）② 可观测性体系：日志管理+Prometheus+Langfuse+核心指标（第八章）③ 白标定制 OEM（第九章）④ 统一字段命名规范 `query`（第十章）⑤ 文档状态管控与检索准入机制（第十一章）。新增 4 张数据表、6 个新接口、4 个新错误码（4001/4002/4003）、4 个新边界用例。人员分工、排期、技术框架、目录结构同步更新。** |

---

*V2 终稿日期：2026-07-16*
