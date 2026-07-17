# RAG 智能体项目 — Day 1 测试报告

> **版本**：V2
> **报告日期**：2026-07-16
> **编制人**：测试工程师（5号）-张宇
> **检查点**：CP2（Day1 19:00）
> **分支**：`feature/yulin`（已合并 dev、feature/luojinju-dashboard、feature/zhangyu-testcase、后端A、后端B 等分支）

---

## 一、CP2 检查点硬性通过标准回顾

| # | 标准 | 状态 |
|:--:|------|:--:|
| 1 | 文档上传→切片→向量化→检索 主动脉贯通 | ⚠️ 部分通过 |
| 2 | 文档状态准入校验生效（非 completed 返回 4002） | ✅ 通过 |
| 3 | 全员本地启动成功 | ❌ 未验证 |
| 4 | 数据库建表完成（含用户组表 + 系统配置表） | ❌ 未完成 |
| 5 | Mock 接口可调通 | ⚠️ 前端 Mock 可用，后端 CRUD 接口全部为空 |

---

## 二、各角色交付物审查

### 2.1 后端 A（3号）— RAG 核心引擎 + Langfuse

| 文件 | 状态 | 代码行数 | 评价 |
|------|:--:|:--:|------|
| `api/rag.py` | ✅ 已完成 | 87 | 命中测试接口，参数校验、4002 文档状态准入、三种检索、5001 异常处理 |
| `api/chat.py` | ✅ 已完成 | 216 | 对话接口 /send + /stream，V2 问题全部修复 |
| `rag_engine/rag_pipeline.py` | ✅ 已完成 | 200 | 完整 RAG 链路，Langfuse Trace 包裹检索+生成 |
| `rag_engine/retriever.py` | ✅ 已完成 | 138 | 三种检索（vector/keyword/hybrid） |
| `rag_engine/embedder.py` | ✅ 已完成 | 86 | Embedding 向量化 |
| `rag_engine/generator.py` | ✅ 已完成 | 52 | LLM 生成 + 流式 |
| `rag_engine/splitter.py` | ✅ 已完成 | 24 | 文档切片 |
| `rag_engine/ingest.py` | ✅ 已完成 | 125 | 文档上传→切片→向量化→入库 完整链路 |
| `utils/llm_client.py` | ✅ 已完成 | 201 | LLM/Embedding 统一封装，超时+熔断+Langfuse |
| `utils/langfuse_tracer.py` | ✅ 已完成 | 140 | Langfuse 追踪，NullTrace 降级 |
| `db/sqlite_helper.py` | ✅ 已完成 | 114 | 轻量 SQLite 访问 |
| `db/schema_compat.py` | ✅ 已完成 | 41 | Schema 兼容层 |
| `config.py` | ✅ 已完成 | 105 | V2 全局配置，含 Langfuse 配置 |

**后端 A 小结**：RAG 核心链路完整交付。V2 方案要求的检索/对话/文档准入/Langfuse 追踪全部实现。上一轮测试发现的 5 个 Bug 修复了 4 个（BUG-04 `query` 字段、BUG-05 异常机制、BUG-06 search_type 校验、BUG-03 Langfuse 配置）。

**未修复的遗留问题**：

| 编号 | 问题 | 说明 |
|:--:|------|------|
| BUG-01 | 接口缺少鉴权依赖 | `rag.py` 和 `chat.py` 仍无 `user=Depends(get_current_user)` 和 `require_kb_access`。这是后端 B 的职责——后端 B 的 `auth.py` 和 `permission.py` 均为空文件，后端 A 无法调用 |

---

### 2.2 后端 B（4号）— 业务 CRUD + 鉴权 + 权限 + 白标 + 监控

| 文件 | 状态 | 评价 |
|------|:--:|------|
| `api/auth.py` | ❌ 空文件 | 登录鉴权未实现 |
| `api/users.py` | ❌ 空文件 | 用户管理 CRUD 未实现 |
| `api/roles.py` | ❌ 空文件 | 角色管理 CRUD 未实现 |
| `api/kb.py` | ❌ 空文件 | 知识库管理未实现 |
| `api/docs.py` | ❌ 空文件 | 文档管理未实现 |
| `api/models.py` | ❌ 空文件 | 大模型管理未实现 |
| `api/user_groups.py` | ❌ 空文件 | V2 用户组管理未实现 |
| `api/branding.py` | ❌ 空文件 | V2 白标配置未实现 |
| `db/models.py` | ❌ 空文件 | ORM 数据模型未定义 |
| `db/database.py` | ❌ 空文件 | 数据库连接未实现 |
| `utils/auth.py` | ❌ 空文件 | JWT 签发+校验未实现 |
| `utils/permission.py` | ❌ 空文件 | V2 权限中间件未实现 |
| `utils/logger.py` | ❌ 空文件 | V2 结构化日志未实现 |
| `utils/metrics.py` | ❌ 空文件 | V2 Prometheus 指标未实现 |
| `scripts/init_db.py` | ⚠️ 有内容但缺表 | 仅有 7 张 V1 表，缺少 4 张 V2 表（user_groups、user_group_members、kb_group_access、system_config） |
| `main.py` | ⚠️ 部分实现 | 仅注册了 rag/chat 路由，未注册 auth/users/roles/kb/docs/models 等路由，未集成 Prometheus Instrumentator |

**后端 B 小结**：**Day1 全部 CRUD 业务接口未交付**。`api/` 下 8 个文件、`db/` 下 2 个文件、`utils/` 下 4 个文件均为空文件。这是 Day1 最大的阻塞项。

**影响范围**：
- 前端 A 所有管理页面虽然 Mock 可用，但无法对接真实后端
- 前端 B 的 RAG 页面依赖后端 B 的知识库/文档接口才能创建知识库和上传文档
- 权限越权专项（TC-P01~P06）无法测试
- 白标模块（TC-B01~B06）无法测试
- 可观测性验证（TC-O01~O05）无法测试

---

### 2.3 前端 A（1号）— 管理后台 5 页 + 白标渲染

| 文件 | 状态 | 评价 |
|------|:--:|------|
| `views/Login.vue` | ✅ 已完成 | 180 行，员工/管理员双标签登录，Mock 兜底 |
| `views/Layout.vue` | ✅ 已完成 | 161 行，侧边栏+顶栏+内容区，菜单权限控制 |
| `views/Dashboard.vue` | ✅ 已完成 | 105 行，4 张统计卡片 |
| `views/RoleManage.vue` | ✅ 已完成 | 160 行，CRUD + Mock |
| `views/UserManage.vue` | ✅ 已完成 | 194 行，CRUD + 搜索 + 角色绑定 |
| `views/ModelManage.vue` | ✅ 已完成 | 165 行，CRUD + Mock |
| `router/index.js` | ✅ 已完成 | 72 行，路由守卫 + 角色权限 |
| `stores/user.js` | ✅ 已完成 | 27 行，Token + 用户信息管理 |
| `utils/request.js` | ✅ 已完成 | 55 行，Axios 拦截器 |
| `api/auth.js` | ✅ 已完成 | 63 行，Mock 认证 |
| `api/dashboard.js` | ✅ 已完成 | 14 行，Mock 兜底已修复 |
| `api/roles.js` | ✅ 已完成 | 49 行，Mock CRUD |
| `api/users.js` | ✅ 已完成 | 49 行，Mock CRUD |
| `api/models.js` | ✅ 已完成 | 48 行，Mock CRUD |
| `views/BrandingConfig.vue` | ❌ 空文件 | V2 品牌配置页未开发 |
| `views/UserGroupManage.vue` | ❌ 空文件 | V2 用户组管理页未开发 |
| `stores/branding.js` | ❌ 空文件 | V2 品牌 Store 未开发 |

**前端 A 小结**：管理后台 5 个核心页面（登录、概览、角色、用户、大模型）全部完成，Mock 兜底正常。上一轮测试发现的 BUG-F01（Dashboard 无 Mock 兜底）已修复。V2 新增的白标配置和用户组管理页面未开发。

**未修复的遗留问题**：

| 编号 | 问题 | 位置 |
|:--:|------|------|
| BUG-F02 | `el-button type="text"` 已废弃（Element Plus 2.x） | `Layout.vue:52-53` |
| BUG-F03 | `request.js` 拦截器缺少 V2 错误码处理（4001/4002/4003/403） | `utils/request.js` |
| BUG-F04 | 已登录用户访问 `/login` 不自动跳转 | `router/index.js` |

---

### 2.4 前端 B（2号）— RAG 核心页面 4 页 + 文档状态联动

| 文件 | 状态 | 评价 |
|------|:--:|------|
| `views/KbManage.vue` | ⏳ 占位 | 14 行，仅显示 `el-empty` 占位 |
| `views/HitTest.vue` | ⏳ 占位 | 14 行，仅显示 `el-empty` 占位 |
| `views/ChatDialog.vue` | ⏳ 占位 | 14 行，仅显示 `el-empty` 占位 |
| `views/DocManage.vue` | ❌ 空文件 | 0 字节 |

**前端 B 小结**：**Day1 全部 RAG 核心页面未交付**。4 个页面中 3 个是占位符，1 个是空文件。这是 Day1 第二大的阻塞项。

**影响范围**：
- 知识库管理、文档上传、命中率测试、智能对话 4 个核心功能无法在前端使用
- 即使后端 A 的 RAG 接口已就绪，前端 B 没有页面可以调用
- CP2 检查点"文档上传→切片→向量化→检索"的**前端用户路径**无法走通

---

### 2.5 测试工程师（5号）— 全流程质量保障

| 产出 | 状态 | 说明 |
|------|:--:|------|
| `demo-materials/测试文档1-公司考勤制度.md` | ✅ | 3.1 KB，含考勤制度全文 |
| `demo-materials/测试文档2-差旅报销标准.md` | ✅ | 2.6 KB，含报销标准全文 |
| `demo-materials/测试文档3-RAG系统架构设计.md` | ✅ | 3.7 KB，含 RAG 架构文档 |
| `demo-materials/标准测试问题集.md` | ✅ | 3.4 KB，10 条问题含预期答案 |
| `docs/测试用例/全模块测试用例汇总表.md` | ✅ | 12.6 KB，55 条用例逐条标注状态 |
| `docs/测试用例/权限越权专项用例.md` | ✅ | 8.3 KB，8 条用例含前置条件+步骤 |
| `docs/测试用例/V2-智能对话与命中测试接口测试报告.md` | ✅ | 14.3 KB，后端 A 接口完整测试 |
| `docs/测试用例/前端Dashboard分支功能测试报告.md` | ✅ | 9.7 KB，前端 A 页面完整测试 |
| `docs/测试用例/测试环境就绪检查清单.md` | ✅ | 5.2 KB，26 项环境检查 |

**测试小结**：Day1 测试任务全部完成。全模块 55 条用例已编写，权限越权 8 条用例已展开，后端 A 接口和前端 A 页面已完成专项测试。测试环境和数据已就绪。

---

## 三、Bug 汇总（Day1 末）

### 已修复

| 编号 | 描述 | 修复人 | 修复提交 |
|:--:|------|:--:|------|
| BUG-04 | `/chat/send` 响应缺少 `query` 字段 | 后端 A | `3db0358f` |
| BUG-05 | LLM 异常检测改为 `LLMServiceError` 异常机制 | 后端 A | `3db0358f` |
| BUG-06 | `chat.py` 新增 `search_type` 校验 | 后端 A | `3db0358f` |
| BUG-03 | `config.py` 新增 Langfuse 配置项 | 后端 A | `67d7fbc1` |
| BUG-F01 | Dashboard API 新增 Mock 兜底 | 前端 A | `eb920eb9` |

### 未修复（Day2 需跟进）

| 编号 | 级别 | 描述 | 负责 |
|:--:|:--:|------|:--:|
| BUG-01 | 🔴 P0 | 后端 A 接口缺少鉴权依赖（rag.py + chat.py） | 后端 B 先完成 auth.py 和 permission.py，后端 A 再加依赖 |
| BUG-02 | 🔴 P0 | `init_db.py` 缺少 V2 四张表 + 种子数据 | 后端 B |
| BUG-F02 | 🟡 P1 | `el-button type="text"` 已废弃 | 前端 A |
| BUG-F03 | 🟡 P1 | `request.js` 缺少 V2 错误码处理 | 前端 A |
| BUG-F04 | 🟢 P2 | 已登录用户访问 `/login` 不跳转 | 前端 A |
| BUG-07 | 🟡 P1 | `init_db.py` 缺少 V2 种子数据 | 后端 B |
| BUG-08 | 🟢 P2 | `top_n` 无边界校验 | 后端 A |
| BUG-09 | 🟢 P2 | SSE 流断连时对话记录丢失 | 后端 A |

### Day1 新增发现

| 编号 | 级别 | 描述 | 负责 |
|:--:|:--:|------|:--:|
| BUG-D1-01 | 🔴 P0 | **后端 B 全部 CRUD 业务接口未交付**（8 个 api 文件为空） | 后端 B |
| BUG-D1-02 | 🔴 P0 | **前端 B 全部 RAG 核心页面未交付**（4 个页面占位/空） | 前端 B |
| BUG-D1-03 | 🔴 P0 | `main.py` 仅注册 rag/chat 路由，未注册 auth/users/roles/kb/docs/models 等路由 | 后端 B |
| BUG-D1-04 | 🟡 P1 | `main.py` 未集成 Prometheus Instrumentator 和日志中间件 | 后端 B |
| BUG-D1-05 | 🟡 P1 | 前端 A 的 V2 新增页面（BrandingConfig、UserGroupManage）为空文件 | 前端 A |
| BUG-D1-06 | 🟡 P1 | 后端 B 的 `db/models.py` 为空，ORM 数据模型未定义 | 后端 B |

---

## 四、测试用例可执行率

| 模块 | 用例数 | 可测 | 阻塞 | 待开发 |
|------|:--:|:--:|:--:|:--:|
| 鉴权 | 4 | 3 | 1 | 0 |
| 用户管理 | 6 | 6 | 0 | 0 |
| 角色管理 | 2 | 2 | 0 | 0 |
| 知识库 | 2 | 0 | 0 | 2 |
| 文档管理 | 4 | 0 | 0 | 4 |
| 命中测试 | 9 | 0 | 6 | 3 |
| 智能对话 | 3 | 0 | 3 | 0 |
| 降级测试 | 2 | 0 | 2 | 0 |
| 权限越权 | 6 | 0 | 6 | 0 |
| 文档状态准入 | 6 | 0 | 4 | 2 |
| 白标定制 | 6 | 0 | 6 | 0 |
| 可观测性 | 5 | 0 | 5 | 0 |
| **合计** | **55** | **11** | **33** | **11** |

> **当前可执行率：20%（11/55）**。可执行的 11 条全部集中在前端 A 的管理后台页面（鉴权 3 条 + 用户管理 6 条 + 角色管理 2 条）。

---

## 五、CP2 检查点结论

| 检查项 | 标准 | 实际 | 判定 |
|------|------|------|:--:|
| 文档上传→切片→向量化→检索 | 主动脉贯通 | 后端 A 链路完整（ingest.py + rag.py），但前端 B 无页面可用 | ⚠️ 后端通，前端不通 |
| 文档状态准入校验 | 非 completed 返回 4002 | rag.py 和 chat.py 均已实现 | ✅ 通过 |
| 全员本地启动成功 | 6 人均可启动 | 未验证（后端 B 无接口，前端 B 无页面，无法完整启动） | ❌ 未通过 |
| 数据库建表完成 | 含 V2 用户组表 + 系统配置表 | V2 四张表未建 | ❌ 未通过 |
| Mock 接口可调通 | 前端可预览 | 前端 A Mock 可用，前端 B 无页面 | ⚠️ 部分通过 |

**CP2 结论：未通过**。后端 B 的 CRUD 业务接口和前端 B 的 RAG 核心页面是 Day1 最大的两个缺口，导致 CP2 的三项硬性标准无法满足。

---

## 六、Day2 建议优先级

| 优先级 | 任务 | 负责 | 预计耗时 |
|:--:|------|:--:|:--:|
| 🔴 P0 | 后端 B 完成 auth.py + users.py + roles.py + kb.py + docs.py + models.py CRUD | 后端 B | 4h（上午） |
| 🔴 P0 | 后端 B 完成 `init_db.py` V2 四张表 + 种子数据 | 后端 B | 0.5h |
| 🔴 P0 | 后端 B 完成 `main.py` 路由注册 + Prometheus + 日志 | 后端 B | 0.5h |
| 🔴 P0 | 前端 B 完成 HitTest.vue + ChatDialog.vue 核心页面 | 前端 B | 4h（上午） |
| 🟡 P1 | 后端 B 完成 permission.py + user_groups.py 权限体系 | 后端 B | 2h（下午） |
| 🟡 P1 | 后端 A 在 rag.py/chat.py 加鉴权依赖 | 后端 A | 0.5h |
| 🟡 P1 | 前端 B 完成 KbManage.vue + DocManage.vue | 前端 B | 2h（下午） |
| 🟡 P1 | 前端 A 完成 BrandingConfig.vue + UserGroupManage.vue | 前端 A | 2h（下午） |
| 🟢 P2 | 后端 B 完成 branding.py + logger.py + metrics.py | 后端 B | 2h |
| 🟢 P2 | 全员联调 + 测试执行全模块用例 | 全员 | 下午 |

---

*报告生成日期：2026-07-16*