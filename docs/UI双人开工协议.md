# RAG 平台 UI 双人开工协议

> **用途**：登录首页与管理后台并行 UI 美化时，框定文件边界、Token 契约与开工提示词，避免互相污染工作区。  
> **适用**：你（登录首页）+ 前端 1（管理后台）  
> **技术栈**：Vue 3 + Vite + Element Plus + Pinia（只改 UI，不改业务契约）  
> **日期**：2026-07-18  
> **状态**：已按仓库实况校对，供双方讨论确认后执行

---

## 1. 分工总览

| 角色 | 负责范围 | 目标 |
|------|----------|------|
| **你（登录侧）** | 项目登录首页 `/login` | 品牌优先、首屏氛围与登录表单体验 |
| **前端 1（后台侧）** | 管理后台壳子 + 后台业务页 | 侧栏/顶栏/内容区统一，业务页视觉一致 |

**共同目标**：视觉方向一致、可同时开工、PR 几乎不冲突、合入后全员可正常启动。

---

## 2. 文件所有权（硬边界）

### 2.1 登录侧（你）— 允许修改

| 路径 | 说明 |
|------|------|
| `frontend/src/views/Login.vue` | 登录页唯一主文件 |
| `frontend/src/styles/login.css`（可选新建） | 仅 Login 引用；须在 `Login.vue` 内 `import` |

### 2.2 后台侧（前端 1）— 允许修改

#### Views

| 路径 | 说明 |
|------|------|
| `frontend/src/views/Layout.vue` | 侧栏 / 顶栏 / 主区 / 页脚 |
| `frontend/src/views/Dashboard.vue` | 系统概览 |
| `frontend/src/views/RoleManage.vue` | 角色管理 |
| `frontend/src/views/UserManage.vue` | 用户管理 |
| `frontend/src/views/UserGroupManage.vue` | 用户组管理 |
| `frontend/src/views/ModelManage.vue` | 大模型管理 |
| `frontend/src/views/BrandingConfig.vue` | 品牌配置 |
| `frontend/src/views/KbManage.vue` | 知识库管理 |
| `frontend/src/views/DocManage.vue` | 文档管理 |
| `frontend/src/views/HitTest.vue` | 命中率测试 |
| `frontend/src/views/ChatDialog.vue` | 智能对话 |

#### Components（仓库现有文件；仅后台侧改样式）

> 以下为当前 `frontend/src/components/` **真实存在**的组件。可调 scoped/样式与布局，**禁止改 props / emit / 业务行为**。

| 路径 | 说明 |
|------|------|
| `AppButton.vue` | 通用按钮 |
| `AppTable.vue` | 表格 |
| `AppPagination.vue` | 分页 |
| `ConfirmDialog.vue` | 确认弹窗 |
| `EmptyState.vue` | 空状态 |
| `FileUploader.vue` | 文档上传（含批量） |
| `ChatBubble.vue` | 对话气泡 |
| `StreamText.vue` | 流式文本 |
| `RetrieveResultCard.vue` | 检索/命中结果卡片 |

> **注意**：不存在 `KbList.vue` / `DocList.vue` / `ChatMessage.vue` / `SourceReference.vue`。列表与消息能力在对应 `views` + 上表组件中，勿按虚构文件名开工。

### 2.3 协商区（默认不动；要动先对齐）

| 路径 | 规则 |
|------|------|
| `frontend/src/styles/variables.css` | 只允许**新增**变量，禁止擅自改名/改语义；建议先合 `feature/ui-tokens` |
| `frontend/src/App.vue` | UI 阶段默认不改 |
| `frontend/src/router/index.js` | **禁止**改 path / 权限守卫逻辑 |
| `frontend/src/stores/*`、`frontend/src/api/*` | **禁止**改业务逻辑与接口契约 |
| `frontend/src/utils/*`、`frontend/src/mock/*`、`frontend/vite.config.js` | **禁止**改（含 `role.js` / `request.js` / `docStatus.js`） |
| branding 相关字段消费 | 可在视图中展示；不可改字段名与接口 |
| 懒加载路由（KbManage / DocManage / HitTest / ChatDialog） | 保持现状，UI 侧无需改 import 方式 |
| `brandingStore.applyBranding()` | 必须继续生效（主题色 → `--el-color-primary`、favicon）；**禁止改 store 实现**，登录/Layout 仅调用或依赖现有行为 |

### 2.4 互斥禁令（写进每次 AI 提示词）

- 登录侧 **禁止**改 `Layout.vue`、任何后台 `views`、以及 §2.2 组件  
- 后台侧 **禁止**改 `Login.vue`、`styles/login.css`  
- 任何一方 PR 的 diff 若出现对方文件 → **必须撤回后再提**  
- 双方都 **禁止**为「好看」去改 API 字段、权限判断、SSE、文档状态枚举

---

## 3. Design Token 契约

### 3.1 原则

1. **先定方向，再动代码**：主色、背景、圆角、字号先口头/文档对齐。  
2. **只增不改名**：需要新变量时加前缀，不覆盖对方语义。  
3. **主题色继续走 branding**：`brand_theme_color` → `--el-color-primary`（由现有 `applyBranding` 写入），两边都不要写死另一套主色。  
4. **登录与后台可有差异**，但必须共享同一套主色与字体气质。

### 3.2 命名约定

| 前缀 | 谁用 | 示例 |
|------|------|------|
| 现有全局变量 | 双方只读 / 后台优先复用 | `--color-primary`、`--bg-color-page`、`--radius-card` |
| `--login-*` | **仅登录侧新增** | `--login-hero-bg`、`--login-card-shadow` |
| `--admin-*` | **仅后台侧新增** | `--admin-sidebar-width`、`--admin-card-gap` |

### 3.3 开工前建议锁定的最小 Tokens（讨论清单）

请双方确认后勾选：

- [ ] 主色（默认可参考 `#4a7aff`，可被 branding 覆盖）
- [ ] 页面背景 / 卡片背景
- [ ] 圆角（按钮 / 卡片）
- [ ] 基础字号与字重
- [ ] 侧栏深色 or 浅色（后台决定；登录不依赖侧栏变量）
- [ ] 动效上限：每侧首屏不超过 2～3 个有意运动效

### 3.4 审美避雷（双方统一）

避免：紫白/紫靛渐变俗套、厚重 glow、满屏 emoji、无意义统计条塞进登录首屏。

---

## 4. Git 与并行节奏

### 4.1 推荐分支

```text
dev
 ├─ feature/ui-tokens          （可选：仅 variables.css 新增约定变量）
 ├─ feature/ui-login-<名字>    （登录侧）
 └─ feature/ui-admin-<名字>    （后台侧）
```

### 4.2 规则

1. 从最新 `dev` 拉分支，UI 期间定期 `git fetch` + rebase/merge `dev`。  
2. **PR 只含自己归属文件**；共享 Token 变更单独 PR 或明确写在 PR 说明。  
3. 建议合并顺序：  
   - （可选）Tokens 小 PR →  
   - `ui-login` 与 `ui-admin` 可并行评审 →  
   - 先合冲突风险更小的一侧，再合另一侧。  
4. 合入后双方本地重新 `npm run dev` 做一次交叉冒烟（登录 + 进后台各点一遍）。  
5. 冒烟账号（开发环境）：`admin` / `admin123`；普通用户按环境种子为准（如 `demo` / `demo123`）。

### 4.3 PR 自检清单（提交前必填）

- [ ] 未修改对方归属文件  
- [ ] 未改 `api/*`、`router` 权限逻辑、业务 store、`utils/*`、`mock/*`  
- [ ] 登录仍可成功；错误密码仍有提示（登录侧）  
- [ ] 后台菜单与 admin/user 可见范围未变（后台侧）  
- [ ] branding 字段仍生效（Logo / 名称 / 主题色 / 页脚；favicon 全局仍更新）  
- [ ] 未写死主色 hex 替代 `--el-color-primary`（登录侧重点查）  
- [ ] 附截图：改前 / 改后（桌面；有余力补移动）

---

## 5. 功能保底（UI 改皮不能伤）

### 5.1 登录侧必须保留

- 消费 branding：`brand_name` / `brand_logo_url` / `brand_login_title` / `brand_theme_color`  
  - `brand_favicon_url`：由现有 branding 机制作用于整站，登录侧**不要破坏**（勿改 store）  
  - `brand_footer_text`：登录页**须弱展示**（底部居中小字）；须读 branding，不得写死文案  
- 员工 / 管理员登录切换（现网已有则必须保留）  
- 用户名、密码必填校验  
- 错误提示：「用户名或密码错误，请重新输入」  
- 登录成功跳转不变：普通用户 → `/chat`，管理员 → `/dashboard`  
- **主视觉颜色必须通过 CSS 变量 `--el-color-primary`（或等价 var）引用主题色**，不得在 `Login.vue` / `login.css` 写死 `#4a7aff` 等主色 hex

### 5.2 后台侧必须保留

- 现有菜单信息架构与路由 path（含品牌配置入口若菜单已有）  
- admin / 普通用户菜单可见差异（逻辑不改，只可调样式）  
- 侧栏 Logo、名称、页脚文案仍读 branding；进入后台后 `applyBranding()` 仍被调用  
- 文档状态：`pending` / `processing` / `completed` / `failed`，UI 应有差异化展示（可用现有 status class / Token）  
- 检索方式：`vector` / `keyword` / `hybrid`，切换时 UI 应即时响应  
- 文档上传/批量、对话 SSE、命中测试等交互可用  

---

## 6. 开工提示词（可直接复制给 Cursor / v0）

### 6.1 公共禁区（每次提示词第一行）

```text
UI-only：不改 API / 路由 path / 权限逻辑 / Pinia 业务状态机 / utils / mock；文件树按《UI双人开工协议》互斥；共享 Token 只增不改名。
```

### 6.2 登录侧提示词

```text
【角色】只负责登录页 UI 美化，不要碰管理后台。

【允许修改】
- frontend/src/views/Login.vue
- 可选新建：frontend/src/styles/login.css（仅 Login 引用）
- variables.css 仅可新增 --login-*，禁止改名/改语义已有全局变量

【禁止修改】
- Layout.vue、所有后台 views、frontend/src/components/*
- router、api、stores、utils、mock（可调用 brandingStore.fetchBranding / 展示字段，禁止改实现）
- 登录接口字段、角色跳转逻辑

【功能必须保留】
- brand_name / brand_logo_url / brand_login_title / brand_theme_color
- brand_footer_text 须弱展示（底部居中小字）；favicon 不破坏全局 branding 机制
- 员工/管理员切换（若已有）
- 错误密码提示：「用户名或密码错误，请重新输入」
- 登录成功：admin → /dashboard，普通用户 → /chat
- 主色只用 var(--el-color-primary)，禁止写死主色 hex

【视觉任务】
- 品牌优先首屏：品牌名/Logo 是主角；一句话标语 + 表单 + CTA
- 桌面+移动可用；避免紫白渐变俗套、厚重 glow、emoji

【交付】
- 变更文件列表 + 说明未改任何后台文件 + 截图
```

### 6.3 后台侧提示词

```text
【角色】只负责管理后台壳子与后台业务页 UI，不要碰登录页。

【允许修改】
- Layout.vue 与后台 views（Dashboard / 管理页 / Branding / Kb / Doc / HitTest / Chat 等）
- 现有 components：AppButton/AppTable/AppPagination/ConfirmDialog/EmptyState/FileUploader/ChatBubble/StreamText/RetrieveResultCard（只改样式，不改 props/事件）
- variables.css 仅可新增 --admin-*，勿改 --login-*

【禁止修改】
- Login.vue、styles/login.css
- 登录接口、鉴权、canSeeMenu / isAdminRole 等权限判断逻辑
- API 字段名、路由 path、文档状态枚举、SSE 行为、stores/api/utils/mock 实现

【功能必须保留】
- 菜单结构与 admin/user 可见范围
- branding 侧栏 Logo/名称/页脚；applyBranding 仍生效
- 文档状态 pending/processing/completed/failed 差异化展示
- 检索 vector/keyword/hybrid 切换即时响应
- 上传/批量、对话 SSE、命中测试可用（只换皮）

【视觉任务】
- 统一后台密度、卡片、表格、空状态
- 与登录页共用主色 Token，布局可为「后台工具感」

【交付】
- 变更文件列表 + 说明未改 Login.vue + 关键页截图
```

---

## 7. 讨论磨合议题（开会用）

请双方逐条拍板：

1. **视觉方向一句话**（例：冷色轻企业工具 / 科技感登录 + 稳重后台）  
2. **Tokens 最小集**是否按 §3.3 执行  
3. **文件表**是否按 §2 执行（组件表已按仓库实况列出）  
4. **Chat / HitTest / Doc** 是否全部归后台侧（建议：是）  
5. **品牌配置页**归后台侧（建议：是；登录只消费配置）  
6. **登录页是否展示** `brand_footer_text` → **已拍板：展示（弱）**  
   - 位置：登录页最底部居中  
   - 样式：约 12px、次要色、不抢主视觉  
   - 数据：`brandingStore.brandFooterText`（与后台侧栏同源）  
7. **双品牌（方案 A）** → **已拍板**  
   - 顶栏左侧：提供方固定「六朵云」+ CSS 方块标（管理员改不了）  
   - 主视觉 / 登录弹窗：使用方白标 `brand_name` 等  
   - 交互强调色：`var(--el-color-primary)`（随品牌主题）  
   - SIGN IN / ENTER → 毛玻璃登录浮窗；保留员工/管理员切换  
8. **合并顺序**与评审人  
9. **截止时间**与「冻结逻辑、只改样式」窗口  

---

## 8. 确认签字（讨论后填写）

| 事项 | 登录侧 | 后台侧（前端 1） |
|------|--------|------------------|
| 已阅读并同意文件边界 | ☐ | ☐ |
| 已同意 Token 命名约定 | ☐ | ☐ |
| 分支命名已约定 | ☐ | ☐ |
| 视觉方向一句话 | | |
| 计划开工日期 | | |

---

## 9. 参考文档

- `docs/UI设计-v0提示词.md`：v0 短/长提示词与交付物格式（适合定调，落地时请拆成登录/后台两路）  
- `docs/演示操作流程.md`：功能冒烟路径  
- `frontend/src/styles/variables.css`：当前全局 Token 源文件  

---

## 10. 协议审阅结论（工程侧）

**总体同意**你们的修改方向（懒加载说明、跳转路径写死、主题色禁写死、文档状态/检索方式保底等），这些都增强了可接入性与防逻辑伤。

已在本版校正的问题：

| 问题 | 处理 |
|------|------|
| 列出不存在的组件（KbList/DocList/ChatMessage/SourceReference） | 改为仓库真实组件表 |
| §5 保底与 §6 提示词不一致 | 已对齐 branding / 跳转 / 主题色 / 状态与检索 |
| `components/*` 边界过宽 | 写明仅后台侧 + 真实文件名单 |
| 冻结范围遗漏 utils/mock/vite | 已补入协商/禁区 |
| `brand_footer` 在登录页「必须展示」过强 | 改为可选展示，避免强迫改产品信息架构 |
| `applyBranding` 责任不清 | 明确禁止改 store，两侧只依赖现有机制 |

**一句话协议**：登录改登录、后台改后台；Token 只增不改名；逻辑冻结只换皮；组件名以仓库为准。
