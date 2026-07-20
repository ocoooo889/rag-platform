/**
 * 全局业务类型定义（前端 B）
 * 约定：业务代码禁止 any；后端未就绪字段以注释标注。
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

/** 运行时大模型配置（对话侧参数，非模型 CRUD） */
export interface RuntimeModelConfig {
  embedding_model: string
  llm_model: string
  temperature: number
  max_tokens: number
}

/** 后端返回的参数合法区间 */
export interface RuntimeModelBounds {
  temperature_min: number
  temperature_max: number
  max_tokens_min: number
  max_tokens_max: number
}

export interface RuntimeModelOptionsPayload {
  embedding_models: string[]
  llm_models: string[]
  bounds: RuntimeModelBounds
  current?: Partial<RuntimeModelConfig>
}

/** 文档切分可视化配置 */
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

/** 知识库级索引配置（前端展示/本地缓存；后端按库生效待对接） */
export type KbChunkMode = 'recursive' | 'fixed'
export type KbSyncMode = 'pending' | 'force_all'

export interface KbIndexConfig {
  chunk_size: number
  chunk_overlap: number
  chunk_mode: KbChunkMode
  /** 分割符号，多个用 | 分隔（切分策略并入索引配置） */
  separators: string
  /** 文本清洗开关 */
  clean_enabled: boolean
  embedding_model: string
  /** 变更时先建快照，问答继续用旧索引直至重建完成 */
  create_snapshot: boolean
  sync_mode: KbSyncMode
}

export interface KbRebuildJob {
  job_id: string
  kb_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message?: string
}

/** 评测任务 */
export type EvalTaskStatus = 'pending' | 'running' | 'completed' | 'failed'

/** 创建/运行时透传给后端的参数快照 */
export interface EvalRunParams {
  kb_id: string | number
  kb_name?: string
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
