# Day4：本地可运行性与 Chroma 联通修复报告

> **报告日期**：2026-07-19  
> **编制**：测试 / 联调（张宇）  
> **分支**：`zhangyu-mlbg`  
> **对照**：README 最短正确路径、部署说明、风险预案、产品手册主链路可演示门禁  

---

## 一、问题现象

联调 / 命中测试 / 对话检索时频繁出现：

> 向量库（Chroma localhost:8000）未启动或地址不通（），已切换关键词检索

侧栏偶发「Chroma 异常」；队友按旧 README / 默认 `chroma run` 启动后难以复现「向量检索正常」。

---

## 二、根因分析

| 层级 | 结论 |
|------|------|
| 监听地址 | Windows 上 `chroma run` **未指定 `--host`** 时，常只监听 **`[::1]:8000`（IPv6）** |
| 客户端 | 后端 `HttpClient` / 部分探测走 **`127.0.0.1`（IPv4）** → 连接失败 |
| 表象 | 浏览器用 `localhost` 偶发能通，后端仍报「未启动」并降级 BM25 |
| 次要因素 | 启动脚本先起 Chroma 再装依赖、固定 sleep、多实例叠端口、文档端口写成 5001、heartbeat 写 v1 |

**不是**系统要去开关 IPv4/IPv6；关键是 **Chroma 监听地址** 与 **`.env` 的 `CHROMA_HOST`** 必须一致。

---

## 三、修复方案（已落地）

### 3.1 固定约定（全员）

```bash
chroma run --path ./chroma_data --host 127.0.0.1 --port 8000
```

```env
CHROMA_HOST=127.0.0.1
CHROMA_PORT=8000
```

自检：http://127.0.0.1:8000/api/v2/heartbeat  

### 3.2 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/start_all.bat/.sh` | 首次：检查 `.env` → venv+pip → Chroma(`--host 127.0.0.1`) → **轮询心跳** → 后端 → 前端 |
| `scripts/restart_dev.bat/.sh` | **日常快速重启**（跳过 pip/npm），同样等心跳 |
| `scripts/stop_all.bat/.sh` | 停 8000/8001/5173；bat 支持 `nopause` |

### 3.3 依赖与工程约定

| 项 | 变更 |
|----|------|
| `backend/requirements.txt` | `chromadb==1.5.9`；显式 `bcrypt>=4,<5` |
| `frontend/package.json` | `"engines": { "node": ">=18" }` |
| `config.py` 默认 | `CHROMA_HOST` 默认 `127.0.0.1` |
| `embedder.py` | 探测候选优先 `127.0.0.1`，回退 `localhost` |

### 3.4 文档同步

已统一改写 / 对齐：

- `README.md`（最短正确路径 + 快速重启）
- `.env.example` / `backend/.env.example`
- `docs/部署说明.md`、`docs/风险与预案清单.md`
- `docs/尚欢欢-本地迁移动说明.md`
- `RAG项目完整管控方案-V2.md`
- `docs/测试用例/测试环境就绪检查清单.md`（及 Day1 副本）
- Day2 并行测试策略中的 Chroma 启动示例

---

## 四、验证记录（本机 2026-07-19）

| 检查项 | 结果 |
|--------|:----:|
| `netstat` 显示 `127.0.0.1:8000` LISTEN（非仅 `[::1]`） | ✅ |
| `curl http://127.0.0.1:8000/api/v2/heartbeat` | ✅ |
| `chromadb.HttpClient(host='127.0.0.1', port=8000).heartbeat()` | ✅ |
| `GET /health` / Dashboard `services.chroma=ok` | ✅ |
| 前端 `http://127.0.0.1:5173` | ✅ |

---

## 五、给队友的防再发清单

1. **永远**带 `--host 127.0.0.1` 启动 Chroma  
2. `.env` 写死 `CHROMA_HOST=127.0.0.1`  
3. 日常用 `scripts\restart_dev.bat`，不要手搓漏参数  
4. 自检只用 **v2** heartbeat，端口：**Chroma 8000 / API 8001 / Vite 5173**  
5. 克隆后先 `git checkout` 可运行分支（如 `dev` / `zhangyu-mlbg`），勿停在空/旧 `main`

---

## 六、遗留与建议

| 项 | 说明 |
|----|------|
| 历史 Day1～Day3 报告正文 | 保留当日结论；错误码 `5001` 仍为业务码，未改 |
| 可选增强 | 后端启动时若 Chroma 未就绪，健康检查明确提示「请先起 Chroma」 |
| 提交 | 本批改动待推送到远程，供队友拉取 |
