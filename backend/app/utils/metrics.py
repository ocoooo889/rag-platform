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
