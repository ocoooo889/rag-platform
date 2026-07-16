# Git 分支管理规范

> 版本：v2.0
> 日期：2026-07-16

---

## 1. 分支模型

采用 **Trunk-Based Development** 简化版：

```
main ──────────────────────────────────────────▶
  │
  ├── feature/xxx ──────▶ (合并后删除)
  ├── fix/xxx ──────────▶ (合并后删除)
  └── release/vX.X ────▶ (合并后打 tag，删除)
```

---

## 2. 分支命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能分支 | `feature/<模块>-<简述>` | `feature/kb-crud`、`feature/rag-retrieve` |
| 修复分支 | `fix/<模块>-<简述>` | `fix/auth-jwt-expire`、`fix/doc-upload-413` |
| 发布分支 | `release/v<版本号>` | `release/v2.0` |
| 热修复 | `hotfix/<简述>` | `hotfix/login-500` |

---

## 3. Commit 规范

采用 **Conventional Commits**：

```
<type>(<scope>): <subject>

[body]

[footer]
```

| type | 说明 |
|:--|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构（非功能变更） |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖变更 |

示例：
```
feat(api): add user group CRUD endpoints

- POST /api/user-groups
- GET /api/user-groups/:id
- PUT /api/user-groups/:id
- DELETE /api/user-groups/:id

Closes #42
```

---

## 4. 合并策略

| 规则 | 说明 |
|------|------|
| **必须通过 CI** | 合并前 CI Pipeline 必须全绿 |
| **Squash Merge** | feature/fix 分支合并到 main 使用 Squash |
| **删除源分支** | 合并后立即删除 feature/fix 分支 |
| **禁止直接 push main** | main 分支受保护，仅通过 PR 合并 |
| **Code Review** | 至少 1 人 Approve 后方可合并 |

---

## 5. Tag 规范

发布时打 tag，格式 `v<major>.<minor>.<patch>`：

```bash
git tag -a v2.0.0 -m "Release v2.0: 用户组 + 品牌配置 + 可观测性"
git push origin v2.0.0
```

---

## 6. 工作流示例

### 开发新功能

```bash
# 1. 从 main 创建分支
git checkout main && git pull
git checkout -b feature/branding-crud

# 2. 开发 + 提交
git add .
git commit -m "feat(api): add branding CRUD endpoints"

# 3. 推送并创建 PR
git push origin feature/branding-crud
# → 在 Git 平台创建 PR → Code Review → Squash Merge → 删除分支
```

### 紧急修复

```bash
# 1. 从 main 创建 hotfix
git checkout main && git pull
git checkout -b hotfix/auth-500-error

# 2. 修复 + 提交
git add .
git commit -m "fix(auth): resolve 500 error on invalid token"

# 3. 合并到 main + 打 tag
# → PR → Squash Merge → git tag v2.0.1 → 删除分支
```

---

## 7. .gitignore 关键条目

```gitignore
# 环境变量
.env

# Python
__pycache__/
*.pyc
*.egg-info/

# 数据库
*.db
*.sqlite3

# Chroma 向量数据
chroma_data/

# 日志
logs/
*.log

# IDE
.vscode/
.idea/

# 前端
node_modules/
dist/

# Docker
docker-compose.override.yml

# 上传文件
uploads/
```
