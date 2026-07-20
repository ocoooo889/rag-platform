/**
 * 全局业务类型定义（前端 B）
 * 约定：业务代码禁止 any；字段与 backend schema 对齐。
 */

/** 统一 API 响应外壳 */
export interface ApiResponse<T = unknown> {
  code: number
  msg?: string
  message?: string
  data: T
}

/** 分页结构 */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 输入双份隔离：原始请求值 + 渲染安全值 */
export interface DualTextInput {
  /** 原样传给后端，禁止截断删减 */
  raw: string
  /** 仅用于 DOM 展示的转义文本 */
  display: string
  /** 是否命中危险脚本拦截 */
  blocked: boolean
  /** 是否超出长度阈值 */
  overLimit: boolean
  /** 纯中文提示 */
  tip: string
}

/** 运行时可选模型（来自 GET /api/runtime-config/models → models[]） */
export interface RuntimeModelItem {
  id: number | null
  model_type: 'chat' | 'embedding' | string
  model_name: string
  api_base_url?: string
  dimension?: number | null
  is_active?: boolean
  source?: string
}

export interface RuntimeParamLimit {
  label?: string
  type?: string
  min?: number
  max?: number
  default?: number
  step?: number
  options?: number[]
}

export interface RuntimeParameterLimits {
  chat: {
    temperature: RuntimeParamLimit
    top_p: RuntimeParamLimit
    max_tokens: RuntimeParamLimit
    presence_penalty?: RuntimeParamLimit
    frequency_penalty?: RuntimeParamLimit
  }
  embedding: {
    dimension: RuntimeParamLimit
  }
}

export interface RuntimeChatParams {
  temperature: number
  top_p: number
  max_tokens: number
  presence_penalty?: number
  frequency_penalty?: number
}

export interface RuntimeEmbeddingParams {
  dimension?: number
}

/** 当前选中项（与后端 selection 对齐） */
export interface RuntimeModelSelection {
  chat_model_id: number | null
  embedding_model_id: number | null
  chat_params: RuntimeChatParams
  embedding_params: RuntimeEmbeddingParams
  updated_at?: string | null
}

/** GET /api/runtime-config/models 原始载荷 */
export interface RuntimeModelOptionsPayload {
  models: RuntimeModelItem[]
  parameter_limits: RuntimeParameterLimits
  selection: RuntimeModelSelection
}

/** PUT /api/runtime-config/models 请求体 */
export interface RuntimeModelConfigUpdate {
  chat_model_id?: number | null
  embedding_model_id?: number | null
  chat_params?: Partial<RuntimeChatParams>
  embedding_params?: Partial<RuntimeEmbeddingParams>
}

/** 本地缓存 / 表单视图（由 models + selection 派生，不含硬编码模型名） */
export interface RuntimeModelConfig {
  chat_model_id: number | null
  embedding_model_id: number | null
  /** 仅展示用，来自 models 列表 */
  chat_model_name?: string
  embedding_model_name?: string
  temperature: number
  top_p: number
  max_tokens: number
  presence_penalty?: number
  frequency_penalty?: number
  embedding_dimension?: number
}

/** 文档切分可视化配置（本地预览 / 上传侧） */
export interface ChunkStrategyConfig {
  chunk_size: number
  chunk_overlap: number
  separators: string
  clean_enabled: boolean
}

export interface ChunkPreviewItem {
  index: number
  content: string
  char_count: number
}

/** 知识库级索引配置 — 对齐 KbIndexConfigOut / KbIndexConfigUpdate */
export type KbSearchType = 'vector' | 'keyword' | 'hybrid'
export type KbSyncMode = 'pending' | 'force_all'

/** BE 权威字段 */
export interface KbIndexConfig {
  kb_id?: string
  chunk_size: number
  chunk_overlap: number
  hybrid_alpha: number
  default_search_type: KbSearchType
  enable_rerank: boolean
  default_top_n: number
  updated_at?: string | null
  /** 前端重建意图（不落 BE index-config） */
  create_snapshot?: boolean
  sync_mode?: KbSyncMode
}

/** 评测/上传仍可能使用的切分方式（与 documents/split-strategies 对齐） */
export type KbChunkMode =
  | 'recursive'
  | 'fixed'
  | 'markdown_header'
  | 'paragraph'
  | 'sentence'
  | 'semantic'
  | 'parent_child'

export interface KbRebuildJob {
  job_id: string
  kb_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message?: string
  /** BE rebuild 摘要字段（可选） */
  total?: number
  queued?: number
}

/** 评测任务 */
export type EvalTaskStatus = 'pending' | 'running' | 'completed' | 'failed'

/** 创建/运行时透传给后端的参数快照 */
export interface EvalRunParams {
  kb_id: string | number
  kb_name?: string
  /** 必须来自 runtime-config 模型列表，禁止硬编码 */
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  chunk_mode?: string
  separators?: string
  clean_enabled?: boolean
}

export interface EvalTask {
  id: string
  name: string
  status: EvalTaskStatus
  created_at: string
  sample_count: number
  rule_json?: string
  error_message?: string
  /** 透传参数快照 */
  params?: EvalRunParams
  /** 0–100；running 时由进度接口刷新 */
  progress?: number
  progress_message?: string
}

export interface EvalSample {
  id: string
  task_id: string
  question: string
  expected_answer: string
  tags?: string
}

/** 单条评测结果（后端返回；前端只解析渲染） */
export interface EvalSourceRef {
  chunk_id?: string
  document_id?: string | number
  document_name?: string
  content?: string
  score?: number
}

export interface EvalMetricRow {
  sample_id: string
  question: string
  /** 模型实际回答 */
  answer?: string
  expected_answer?: string
  score: number
  precision?: number
  recall?: number
  faithfulness?: number
  detail?: string
  /** 检索模式：semantic / keyword / hybrid */
  retrieval_mode?: string
  retrieval_degraded?: boolean
  sources?: EvalSourceRef[]
}

/**
 * 评测结果接口 data 兼容两种形态：
 * - 纯数组 EvalMetricRow[]
 * - 分页结构 { items | list, total?, page?, page_size? }
 */
export interface EvalResultsPage {
  items?: EvalMetricRow[]
  list?: EvalMetricRow[]
  total?: number
  page?: number
  page_size?: number
}

export type EvalResultsPayload = EvalMetricRow[] | EvalResultsPage

export interface EvalComparePoint {
  task_id: string
  task_name: string
  metric: string
  value: number
}

export interface EvalProgress {
  task_id: string
  status: EvalTaskStatus
  progress: number
  message?: string
}

/** 页面筛选条件本地缓存 */
export interface EvalPageFilters {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
  compare_ids?: string[]
}

/** 未提交样本草稿 */
export interface EvalSampleDraft {
  question: string
  expected_answer: string
  tags: string
  updated_at: string
}

/** 缓存分区键：用户 + 知识库双维度 */
export interface CacheScope {
  userId: string
  kbId: string
}

export interface ChatCacheMessage {
  id: string
  role: 'user' | 'assistant'
  /** 原始文本（请求/缓存） */
  content: string
  /** 转义后展示文本（仅 DOM，独立存储） */
  contentDisplay?: string
  sources?: Array<Record<string, unknown>>
  created_at?: string
}

export interface ChatQaCacheEntry {
  question: string
  answer: string
  sources?: Array<Record<string, unknown>>
  retrievalMode?: string
  retrievalDegraded?: boolean
  updated_at: string
}
