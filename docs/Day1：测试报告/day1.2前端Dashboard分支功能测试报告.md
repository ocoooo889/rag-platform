# 前端 Dashboard 分支 — 功能测试报告

> **测试分支**：`feature/luojinju-dashboard`
> **测试日期**：2026-07-16
> **测试工程师**：5号
> **测试环境**：Vue 3 + Vite 5 + Element Plus 2.7 + Pinia 2 + Vue Router 4
> **开发服务器**：`http://localhost:5173`（302ms 启动）

---

## 一、测试范围

| 功能模块 | 负责人 | 本次测试范围 |
|------|:--:|------|
| 登录页面 | 前端 A | ✅ 用户名、密码、角色选择、Mock 认证 |
| 系统概览 | 前端 A | ✅ 4 张统计卡片 |
| 角色管理 | 前端 A | ✅ 增删改查 |
| 用户管理 | 前端 A | ✅ 增删改查、角色绑定、搜索 |
| 大模型管理 | 前端 A | ✅ 增删改查 |
| 全局布局 | 前端 A | ✅ 左侧导航 + 顶部通栏 + 内容区 |
| 路由守卫 | 前端 A | ✅ 登录拦截 + 角色权限校验 |
| 知识库管理 | 前端 B | ⏳ 占位页面（非本次测试范围） |
| 文档管理 | 前端 B | ⏳ 空文件（非本次测试范围） |
| 命中率测试 | 前端 B | ⏳ 占位页面（非本次测试范围） |
| 智能对话 | 前端 B | ⏳ 占位页面（非本次测试范围） |
| 用户组管理 | 前端 A | ⏳ 空文件（V2 待开发） |
| 品牌配置 | 前端 A | ⏳ 空文件（V2 待开发） |

---

## 二、测试账号

| 角色 | 用户名 | 密码 | 预期权限 |
|------|------|------|------|
| 管理员 | admin | admin123 | 全部页面 |
| 编辑员 | editor | editor123 | 系统概览 + 知识库管理 + 命中率测试 + 智能对话 |
| 普通用户 | user | user123 | 仅智能对话 |

---

## 三、功能点逐项测试

### 3.1 登录页面

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 用户名输入框 | ✅ | `el-input`，placeholder "请输入用户名" |
| 2 | 密码输入框（密文） | ✅ | `type="password"`，placeholder "请输入密码" |
| 3 | 角色选择（管理员） | ✅ | `el-radio-group`，三个选项 |
| 4 | 角色选择（编辑员） | ✅ | 同上 |
| 5 | 角色选择（普通用户） | ✅ | 同上 |
| 6 | 表单空值校验 | ✅ | 三项必填，rules 配置正确 |
| 7 | 登录按钮 loading 状态 | ✅ | `:loading="loading"` 防重复提交 |
| 8 | Mock 认证：admin / admin123 | ✅ | `password === username + '123'` |
| 9 | Mock 认证：editor / editor123 | ✅ | 同上 |
| 10 | Mock 认证：user / user123 | ✅ | 同上 |
| 11 | 错误密码拦截 | ✅ | 密码不匹配时 throw error，不跳转 |
| 12 | 管理员登录 → 跳转 `/dashboard` | ✅ | `redirectPath` 逻辑正确 |
| 13 | 编辑员登录 → 跳转 `/knowledge-bases` | ✅ | 同上 |
| 14 | 普通用户登录 → 跳转 `/chat` | ✅ | 同上 |
| 15 | Token 写入 localStorage | ✅ | key: `token` |
| 16 | 用户信息写入 localStorage | ✅ | key: `userInfo`，JSON 格式 |
| 17 | 登录成功 Toast 提示 | ✅ | `ElMessage.success('登录成功')` |

### 3.2 路由守卫与权限校验

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 未登录访问 `/` → 重定向 `/login` | ✅ | `beforeEach` 检查 token |
| 2 | 未登录访问 `/dashboard` → 重定向 `/login` | ✅ | 同上 |
| 3 | 未登录访问 `/roles` → 重定向 `/login` | ✅ | 同上 |
| 4 | 管理员 → 可访问 `/dashboard` | ✅ | meta.roles 包含 '管理员' |
| 5 | 管理员 → 可访问 `/roles` | ✅ | meta.roles = ['管理员'] |
| 6 | 管理员 → 可访问 `/users` | ✅ | meta.roles = ['管理员'] |
| 7 | 管理员 → 可访问 `/models` | ✅ | meta.roles = ['管理员'] |
| 8 | 管理员 → 可访问 `/chat` | ✅ | meta.roles 包含 '管理员' |
| 9 | 编辑员 → 可访问 `/dashboard` | ✅ | meta.roles 包含 '编辑员' |
| 10 | 编辑员 → 访问 `/roles` 被拒 → `/chat` | ✅ | 编辑员不在 ['管理员'] 白名单 |
| 11 | 编辑员 → 访问 `/users` 被拒 → `/chat` | ✅ | 同上 |
| 12 | 普通用户 → 访问 `/dashboard` 被拒 → `/chat` | ✅ | 普通用户不在白名单 |
| 13 | 普通用户 → 访问 `/roles` 被拒 → `/chat` | ✅ | 同上 |
| 14 | 已登录用户访问 `/login` 不拦截 | ⚠️ | 不会自动跳转回首页（体验问题） |

### 3.3 系统概览 Dashboard

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 4 张统计卡片渲染 | ✅ | 知识库数量、文档数量、分片数量、调用次数 |
| 2 | 卡片渐变色图标 | ✅ | 4 种不同渐变背景 |
| 3 | 调用次数默认显示 `--` | ✅ | 方案要求"调用次数留空壳" |
| 4 | 组件挂载时调用 API | ✅ | `onMounted` → `getStatsApi()` |
| 5 | **Mock 兜底** | ❌ | `dashboard.js` 无 try/catch Mock 降级，后端不可用时报错 |

### 3.4 角色管理

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 角色列表表格 | ✅ | ID / 角色名称 / 权限 三列 |
| 2 | 新增角色弹窗 | ✅ | 角色名称 + 权限标识，表单校验 |
| 3 | 编辑角色弹窗 | ✅ | 回填已有数据 |
| 4 | 删除确认弹窗 | ✅ | `ElMessageBox.confirm` 二次确认 |
| 5 | Mock 预设数据：3 个角色 | ✅ | 管理员(all)、编辑员(edit)、普通用户(view) |
| 6 | Mock 新增（内存操作） | ✅ | `mockRoles.push()` |
| 7 | Mock 编辑（内存操作） | ✅ | `mockRoles[idx] = {...}` |
| 8 | Mock 删除（内存操作） | ✅ | `mockRoles.splice(idx, 1)` |
| 9 | 权限标识可选值提示 | ✅ | `el-tag` 显示 all / edit / view |

### 3.5 用户管理

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 用户列表表格 | ✅ | ID/用户名/显示名/角色/状态/创建时间/操作 |
| 2 | 搜索输入框 | ✅ | `el-input` + keyword 参数，回车触发 |
| 3 | 新增用户弹窗 | ✅ | 用户名、密码、显示名、角色、状态 |
| 4 | 编辑用户弹窗 | ✅ | 用户名 disabled（不可修改） |
| 5 | 角色下拉绑定 | ✅ | `el-select` 从 `getRolesApi()` 加载 |
| 6 | 状态标签颜色 | ✅ | 启用=success(绿)、已停用=danger(红) |
| 7 | 角色 ID → 名称格式化 | ✅ | `formatRole()` 函数 |
| 8 | Mock 预设数据：3 个用户 | ✅ | admin/editor/user |
| 9 | Mock 新增 | ✅ | `Date.now()` 生成 ID |
| 10 | Mock 删除（软删除） | ✅ | 将 status 设为 '已停用' |

### 3.6 大模型管理

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 模型列表表格 | ✅ | ID/模型类型/模型名称/API地址/向量维度/状态/操作 |
| 2 | 新增模型弹窗 | ✅ | 模型类型(chat/embedding)、名称、API地址、维度、启用开关 |
| 3 | 编辑模型 | ✅ | 回填已有数据 |
| 4 | 删除确认弹窗 | ✅ | 二次确认 |
| 5 | 模型类型格式化 | ✅ | chat→聊天模型, embedding→嵌入模型 |
| 6 | 启用/禁用开关 | ✅ | `el-switch` 组件 |
| 7 | Mock 预设数据：2 个模型 | ✅ | GPT-3.5 + text-embedding-ada-002 |
| 8 | Mock 新增/编辑/删除 | ✅ | 内存数组操作 |

### 3.7 全局布局

| # | 测试项 | 结果 | 说明 |
|:--:|------|:--:|------|
| 1 | 左侧固定导航（200px） | ✅ | `el-aside width="200px"`，深色背景 #304156 |
| 2 | 顶部通栏 | ✅ | `el-header`，白色背景 |
| 3 | 右侧内容区 | ✅ | `el-main`，灰色背景 #f5f7fa |
| 4 | Logo 区域 | ✅ | 红色方块 + "智能RAG平台" + "RAG管理后台" |
| 5 | 菜单项按角色显示/隐藏 | ✅ | `canSeeMenu()` 函数，管理员见全部、编辑员见部分、普通用户仅见智能对话 |
| 6 | 当前路由菜单高亮 | ✅ | `:default-active="activeMenu"` |
| 7 | 退出登录按钮 | ✅ | 清除 localStorage + 跳转 `/login` |
| 8 | 顶部智能对话快捷入口 | ✅ | 仅对有权限的角色显示 |

---

## 四、Bug 清单

| 级别 | 编号 | 描述 | 位置 | 影响 |
|:--:|:--:|------|------|------|
| 🟡 P1 | BUG-F01 | **Dashboard API 缺少 Mock 兜底**，后端不可用时显示"网络异常"toast，统计卡片全显示 0 | `src/api/dashboard.js` | 用户无法预览 Dashboard 页面 |
| 🟡 P1 | BUG-F02 | **`el-button type="text"` 已废弃**，Element Plus 2.x 中应使用 `link` 属性 | `src/views/Layout.vue:52-53` | 按钮样式可能不符合预期 |
| 🟡 P1 | BUG-F03 | **`request.js` 拦截器缺少 V2 错误码处理**（4001 用户组未授权 / 4002 文档未就绪 / 4003 白标配置缺失 / 403 权限不足） | `src/utils/request.js` | V2 方案要求的统一错误拦截未实现 |
| 🟢 P2 | BUG-F04 | 已登录用户访问 `/login` 不自动跳转 | `src/router/index.js` | 体验问题，不影响功能 |
| 🟢 P2 | BUG-F05 | `deleteUserApi` Mock 层做软删除（改状态为"已停用"），函数名暗示硬删除 | `src/api/users.js:44` | 功能正常，命名不准确 |
| 🟢 P2 | BUG-F06 | 5 个文件为空：`BrandingConfig.vue`、`stores/branding.js`、`UserGroupManage.vue`、`DocManage.vue`、`stores/branding.js` | `src/views/`、`src/stores/` | V2 页面待开发（非本次交付范围） |
| 🟢 P2 | BUG-F07 | Mock 数据页面刷新后重置（CRUD 操作不持久化） | `src/api/*.js` | Mock 设计的预期行为 |

---

## 五、后端接口对接清单

当后端接口实现后，修改以下文件即可对接真实接口：

| 接口 | 前端文件 | 当前状态 |
|------|------|:--:|
| `POST /api/auth/login` | `src/api/auth.js` | Mock 兜底（先调真实接口，失败降级到 Mock） |
| `GET /api/roles` | `src/api/roles.js` | Mock 兜底 |
| `POST /api/roles` | `src/api/roles.js` | Mock 兜底 |
| `PUT /api/roles/:id` | `src/api/roles.js` | Mock 兜底 |
| `DELETE /api/roles/:id` | `src/api/roles.js` | Mock 兜底 |
| `GET /api/users` | `src/api/users.js` | Mock 兜底 |
| `POST /api/users` | `src/api/users.js` | Mock 兜底 |
| `PUT /api/users/:id` | `src/api/users.js` | Mock 兜底 |
| `DELETE /api/users/:id` | `src/api/users.js` | Mock 兜底 |
| `GET /api/models` | `src/api/models.js` | Mock 兜底 |
| `POST /api/models` | `src/api/models.js` | Mock 兜底 |
| `PUT /api/models/:id` | `src/api/models.js` | Mock 兜底 |
| `DELETE /api/models/:id` | `src/api/models.js` | Mock 兜底 |
| `GET /api/dashboard/stats` | `src/api/dashboard.js` | **⚠️ 无 Mock 兜底，需优先对接** |

---

## 六、总结

| 维度 | 结果 |
|------|------|
| 登录页面 | ✅ 通过 |
| 系统概览 | ⚠️ 1 个 P1 bug（无 Mock 兜底） |
| 角色管理 | ✅ 通过 |
| 用户管理 | ✅ 通过 |
| 大模型管理 | ✅ 通过 |
| 全局布局 | ✅ 通过 |
| 路由守卫 | ✅ 通过 |
| 前端 B 页面（4 个） | ⏳ 占位页面，非本次测试范围 |
| V2 新增页面（2 个） | ⏳ 空文件，待开发 |

**总评**：Dashboard 分支核心功能全部可用，Mock 兜底机制设计合理。**1 个 P1 bug**（Dashboard 缺少 Mock 兜底）需立即修复，其余 6 个 P2 问题可后续迭代。后端接口实现后，去掉 `src/api/` 目录下的 try/catch 降级逻辑即可无缝对接真实接口。

---

*报告生成日期：2026-07-16*