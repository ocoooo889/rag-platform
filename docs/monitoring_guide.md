<span style="color:red"># 智能 RAG 平台 — 监控配置指南（V2）</span>

<span style="color:red">> 版本：V2（含 Langfuse + Prometheus + Grafana）</span>
<span style="color:red">> 输出：项目负责人</span>
<span style="color:red">> 适用：部署与运维</span>
<span style="color:red">> **【项目负责人补充内容】**</span>

---

## 一、可观测性体系架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Grafana 可视化看板                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  RAG 检索指标 │ │  LLM 调用指标 │ │  系统健康指标 │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌───────────────┐               ┌───────────────┐
│   Prometheus  │               │    Langfuse   │
│  指标采集与存储│               │   LLM 追踪    │
└───────┬───────┘               └───────┬───────┘
        │                               │
        ▼                               ▼
┌───────────────┐               ┌───────────────┐
│   /metrics    │               │  Trace API    │
│   端点采集     │               │  自动上报      │
└───────┬───────┘               └───────┬───────┘
        │                               │
        └───────────┬───────────────────┘
                    ▼
            ┌───────────────┐
            │   RAG 平台后端 │
            │  (FastAPI)    │
            └───────────────┘
```

---

## 二、Langfuse 部署与配置

### 2.1 安装与启动

**方式一：Docker 部署（推荐）**

```bash
# 创建 docker-compose.yml
cat > docker-compose.langfuse.yml << 'EOF'
version: '3.8'
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langfuse
      - NEXTAUTH_SECRET=your-secret-key-here
      - SALT=your-salt-here
      - LANGFUSE_HOST=http://localhost:3000
    depends_on:
      - postgres
    restart: always

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=langfuse
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

volumes:
  postgres_data:
EOF

# 启动服务
docker-compose -f docker-compose.langfuse.yml up -d
```

**方式二：脚本启动（开发环境）**

```bash
# 使用项目提供的启动脚本
bash scripts/start_langfuse.sh
```

### 2.2 配置后端集成

在 `.env` 文件中配置 Langfuse：

```bash
# Langfuse 配置
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=http://localhost:3000
```

### 2.3 验证部署

1. 访问 Langfuse UI：`http://localhost:3000`
2. 使用注册账号登录
3. 创建 Project（每人独立一个）
4. 获取 Public Key 和 Secret Key
5. 配置到 `.env` 中

### 2.4 追踪维度说明

| 追踪阶段 | 记录内容 |
|------|------|
| **Trace** | 唯一标识，贯穿一次完整 RAG 链路 |
| **检索阶段** | query、search_type、命中数量、各 chunk 分数 |
| **LLM 阶段** | 输入 Prompt、输出内容、model、token 用量 |
| **延迟** | 各阶段耗时（检索 / LLM / 总链路） |
| **成本** | 按 model + token 估算费用 |

---

## 三、Prometheus 配置

### 3.1 安装 Prometheus

**Linux/Mac：**

```bash
# 下载安装
wget https://github.com/prometheus/prometheus/releases/download/v2.47.0/prometheus-2.47.0.linux-amd64.tar.gz
tar xvfz prometheus-2.47.0.linux-amd64.tar.gz
cd prometheus-2.47.0.linux-amd64
```

**Windows：**

下载地址：`https://github.com/prometheus/prometheus/releases/download/v2.47.0/prometheus-2.47.0.windows-amd64.zip`

### 3.2 配置文件

创建 `prometheus.yml`：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'rag-platform'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: /metrics

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 3.3 启动 Prometheus

```bash
# Linux/Mac
./prometheus --config.file=prometheus.yml --web.listen-address=":9090"

# Windows
prometheus.exe --config.file=prometheus.yml --web.listen-address=":9090"
```

### 3.4 验证指标端点

访问 `http://localhost:8001/metrics`，确认以下指标存在：

- `http_requests_total`
- `http_request_duration_seconds`
- `rag_retrieve_total`
- `llm_call_total`
- `doc_processing_duration_seconds`

---

## 四、Grafana 配置

### 4.1 安装 Grafana

**Linux/Mac：**

```bash
# 使用官方脚本安装
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update && sudo apt-get install grafana

# 启动服务
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

**Windows：**

下载地址：`https://dl.grafana.com/oss/release/grafana-10.1.0.windows-amd64.zip`

### 4.2 启动 Grafana

```bash
# Linux/Mac（默认端口 3000，注意与 Langfuse 冲突）
# 修改端口启动：
grafana-server --config=/etc/grafana/grafana.ini --homepath=/usr/share/grafana --port=3001

# Windows
grafana-server.exe --config=conf/defaults.ini --port=3001
```

### 4.3 添加数据源

1. 访问 Grafana：`http://localhost:3001`
2. 默认登录：admin / admin
3. 进入 **Configuration** → **Data Sources**
4. 点击 **Add data source** → 选择 **Prometheus**
5. 配置 URL：`http://localhost:9090`
6. 点击 **Save & Test**

### 4.4 导入 Dashboard

#### 4.4.1 官方 Dashboard

| Dashboard ID | 名称 | 说明 |
|:--:|------|------|
| 12900 | Prometheus Stats | Prometheus 自身监控 |
| 13836 | FastAPI | FastAPI 应用监控 |

#### 4.4.2 自定义 RAG Dashboard

创建自定义 Dashboard，包含以下面板：

##### 面板 1：RAG 检索请求数

```promql
sum(rate(rag_retrieve_total[5m])) by (search_type)
```

##### 面板 2：LLM 调用次数

```promql
sum(rate(llm_call_total[5m])) by (model)
```

##### 面板 3：检索延迟分布

```promql
histogram_quantile(0.95, rate(rag_retrieve_duration_seconds_bucket[5m]))
```

##### 面板 4：LLM 延迟分布

```promql
histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m]))
```

##### 面板 5：Token 消耗趋势

```promql
sum(rate(llm_tokens_total[5m])) by (type)
```

##### 面板 6：文档处理状态分布

```promql
doc_status_current
```

##### 面板 7：HTTP 请求状态码

```promql
sum(rate(http_requests_total[5m])) by (status)
```

##### 面板 8：活跃用户数

```promql
active_users_current
```

---

## 五、自定义指标说明

### 5.1 RAG 检索指标

| 指标名 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `rag_retrieve_total` | Counter | search_type, kb_id | RAG 检索请求总数 |
| `rag_retrieve_duration_seconds` | Histogram | search_type | RAG 检索耗时 |
| `rag_retrieve_hits_count` | Histogram | - | 单次检索命中数量 |

### 5.2 LLM 调用指标

| 指标名 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `llm_call_total` | Counter | model, type | LLM 调用次数 |
| `llm_call_duration_seconds` | Histogram | model, type | LLM 调用耗时 |
| `llm_tokens_total` | Counter | model, type | LLM Token 消耗总量 |

### 5.3 文档处理指标

| 指标名 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `doc_processing_duration_seconds` | Histogram | - | 文档处理耗时 |
| `doc_status_current` | Gauge | status | 各状态文档数量 |

### 5.4 系统指标

| 指标名 | 类型 | 说明 |
|------|------|------|
| `active_users_current` | Gauge | 当前活跃用户数 |

---

## 六、告警配置

### 6.1 Prometheus 告警规则

创建 `alerting_rules.yml`：

```yaml
groups:
  - name: rag-platform-alerts
    rules:
      - alert: HighRetrieveLatency
        expr: histogram_quantile(0.95, rate(rag_retrieve_duration_seconds_bucket[5m])) > 3
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "RAG 检索延迟过高"
          description: "95% 检索请求延迟超过 3 秒"

      - alert: HighLLMLatency
        expr: histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m])) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "LLM 调用延迟过高"
          description: "95% LLM 调用延迟超过 10 秒"

      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
          description: "HTTP 错误率超过 5%"

      - alert: LLMCallFailure
        expr: sum(rate(llm_call_total{type="error"}[5m])) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "LLM 调用失败"
          description: "检测到 LLM 调用失败"
```

在 `prometheus.yml` 中引用：

```yaml
rule_files:
  - alerting_rules.yml
```

### 6.2 Grafana 告警通道

1. 进入 **Alerting** → **Notification channels**
2. 添加告警通道（如 Email、Slack、Webhook）
3. 配置通知规则

---

## 七、部署清单

| # | 检查项 | 状态 |
|:--:|------|:--:|
| 1 | Langfuse 服务启动成功（端口 3000） | ☐ |
| 2 | Prometheus 服务启动成功（端口 9090） | ☐ |
| 3 | Grafana 服务启动成功（端口 3001） | ☐ |
| 4 | 后端 `/metrics` 端点可访问 | ☐ |
| 5 | Prometheus 已配置抓取任务 | ☐ |
| 6 | Grafana 已添加 Prometheus 数据源 | ☐ |
| 7 | 自定义 Dashboard 已创建 | ☐ |
| 8 | 告警规则已配置 | ☐ |
| 9 | Langfuse 追踪数据正常上报 | ☐ |
| 10 | 所有指标正常采集 | ☐ |

---

## 八、常见问题

| 问题 | 解决方案 |
|------|------|
| Langfuse 无法连接 | 检查 LANGFUSE_HOST 配置，确保服务启动 |
| Prometheus 无法抓取指标 | 检查防火墙规则，确认 `/metrics` 端点可访问 |
| Grafana 数据源连接失败 | 检查 Prometheus 地址和端口配置 |
| 指标缺失 | 检查 Instrumentator 是否在 `main.py` 中注册 |
| Langfuse 追踪不生效 | 检查 API Key 是否正确配置 |

---

*监控配置指南版本：V2*<br>
*输出日期：2026-07-17*