/**
 * 契约对齐 Mock 数据集（前端 B）
 * 仅在 MOCK_OPEN() / VITE_USE_MOCK=true 时使用；禁止写入真实请求路径
 */
import { DOC_STATUS } from '@/utils/docStatus'

export const MOCK_USERS = [
  {
    id: 'u001',
    username: 'admin',
    display_name: '管理员',
    role_id: 'r001',
    role: 'admin',
    role_name: '管理员',
    status: '启用',
    kb_ids: [],
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'u003',
    username: 'user',
    display_name: '普通用户',
    role_id: 'r003',
    role: 'user',
    role_name: '普通用户',
    status: '启用',
    kb_ids: [],
    created_at: '2026-07-15T09:20:00'
  }
]

export const MOCK_ROLES = [
  {
    id: 'r001',
    name: 'admin',
    description: '系统管理员，拥有全部权限',
    permissions: ['kb:create', 'kb:delete', 'doc:upload', 'doc:delete', 'rag:test', 'chat:send'],
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'r003',
    name: 'user',
    description: '普通用户：授权范围内知识库/命中/对话',
    permissions: ['kb:view', 'doc:view', 'rag:test', 'chat:send'],
    created_at: '2026-07-15T09:00:00'
  }
]

/** 可变知识库列表（Mock CRUD） */
export const mockKbList = [
  {
    id: 'kb001',
    name: '公司制度知识库',
    description: '存放公司内部制度文档',
    doc_count: 5,
    document_count: 5,
    chunk_count: 68,
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'kb002',
    name: '产品手册知识库',
    description: '产品说明与 FAQ',
    doc_count: 1,
    document_count: 1,
    chunk_count: 12,
    created_at: '2026-07-15T10:00:00'
  }
]

/** 可变文档列表 — 契约字段 filename / created_at（兼 uploaded_at） */
export const mockDocList = [
  {
    id: 'doc001',
    kb_id: 'kb001',
    filename: '公司考勤制度.md',
    file_type: 'md',
    file_size: 15230,
    chunk_count: 30,
    status: DOC_STATUS.COMPLETED,
    error_message: '',
    uploaded_at: '2026-07-15T09:05:00',
    created_at: '2026-07-15T09:05:00',
    updated_at: '2026-07-15T09:06:00'
  },
  {
    id: 'doc002',
    kb_id: 'kb001',
    filename: '报销流程说明.md',
    file_type: 'md',
    file_size: 8200,
    chunk_count: 18,
    status: DOC_STATUS.COMPLETED,
    error_message: '',
    uploaded_at: '2026-07-15T09:20:00',
    created_at: '2026-07-15T09:20:00',
    updated_at: '2026-07-15T09:21:00'
  },
  {
    id: 'doc003',
    kb_id: 'kb001',
    filename: '待处理制度草稿.md',
    file_type: 'md',
    file_size: 4100,
    chunk_count: 12,
    status: DOC_STATUS.PROCESSING,
    error_message: '向量化中 4/12',
    uploaded_at: '2026-07-16T08:00:00',
    created_at: '2026-07-16T08:00:00',
    updated_at: '2026-07-16T08:01:00'
  },
  {
    id: 'doc006',
    kb_id: 'kb001',
    filename: '降级样例-仅关键词.md',
    file_type: 'md',
    file_size: 6400,
    chunk_count: 8,
    status: DOC_STATUS.DEGRADED,
    error_message: '向量模型暂不可用，已切换关键词检索',
    uploaded_at: '2026-07-16T10:00:00',
    created_at: '2026-07-16T10:00:00',
    updated_at: '2026-07-16T10:02:00'
  },
  {
    id: 'doc005',
    kb_id: 'kb001',
    filename: '解析失败样例.md',
    file_type: 'md',
    file_size: 2100,
    chunk_count: 0,
    status: DOC_STATUS.FAILED,
    error_message: '切片结果为空，请检查文档内容',
    uploaded_at: '2026-07-16T09:00:00',
    created_at: '2026-07-16T09:00:00',
    updated_at: '2026-07-16T09:00:30'
  },
  {
    id: 'doc004',
    kb_id: 'kb002',
    filename: '产品FAQ.txt',
    file_type: 'txt',
    file_size: 5600,
    chunk_count: 12,
    status: DOC_STATUS.COMPLETED,
    error_message: '',
    uploaded_at: '2026-07-15T11:00:00',
    created_at: '2026-07-15T11:00:00',
    updated_at: '2026-07-15T11:01:00'
  }
]

/** 命中检索分片池 — 对齐 hits[] 字段 */
export const MOCK_HITS_POOL = [
  {
    chunk_id: 'c001',
    content: '根据公司规定，工作满一年的员工可享受 5 天年假；满三年可享受 10 天年假。',
    score: 0.86,
    source_doc: '公司考勤制度.md',
    doc_id: 'doc001',
    method: 'vector'
  },
  {
    chunk_id: 'c002',
    content: '年假应在当年 12 月 31 日前使用完毕，逾期未休视为自动放弃。',
    score: 0.72,
    source_doc: '公司考勤制度.md',
    doc_id: 'doc001',
    method: 'vector'
  },
  {
    chunk_id: 'c003',
    content: '报销需在费用发生后 30 日内提交，并附发票与审批单。',
    score: 0.81,
    source_doc: '报销流程说明.md',
    doc_id: 'doc002',
    method: 'vector'
  },
  {
    chunk_id: 'c004',
    content: '差旅住宿标准：一线城市每日不超过 500 元，其他城市不超过 350 元。',
    score: 0.68,
    source_doc: '报销流程说明.md',
    doc_id: 'doc002',
    method: 'vector'
  },
  {
    chunk_id: 'c005',
    content: '产品支持在线工单与电话热线，工作日 9:00-18:00 响应。',
    score: 0.77,
    source_doc: '产品FAQ.txt',
    doc_id: 'doc004',
    method: 'vector'
  },
  {
    chunk_id: 'c006',
    content: '降级样例：本分片仅写入本地 BM25，无向量。关键词「降级」「关键词检索」可命中。',
    score: 0.74,
    source_doc: '降级样例-仅关键词.md',
    doc_id: 'doc006',
    method: 'bm25'
  }
]

export const MOCK_MODELS = [
  {
    id: 'm001',
    model_type: 'llm',
    model_name: 'gpt-4o-mini',
    api_base_url: 'https://api.openai.com/v1',
    is_active: true
  },
  {
    id: 'm002',
    model_type: 'embedding',
    model_name: 'text-embedding-3-small',
    dimension: 1536,
    api_base_url: 'https://api.openai.com/v1',
    is_active: true
  }
]

export const MOCK_DASHBOARD_STATS = {
  kb_count: 2,
  doc_count: 6,
  user_count: 3,
  group_count: 2,
  chunk_total: 136,
  avg_chunks_per_kb: 68,
  docs_by_status: {
    completed: 3,
    degraded: 1,
    failed: 1,
    pending: 0,
    processing: 1
  },
  docs_by_file_type: { md: 5, txt: 1 },
  today_new_docs: 1,
  failed_doc_count: 1,
  failed_docs: [
    {
      id: 'd-fail',
      filename: '损坏样例.pdf',
      kb_id: 'kb1',
      error_message: '解析失败（Mock）'
    }
  ],
  question_count: 42,
  message_count: 80,
  session_count: 12,
  today_question_count: 5,
  avg_session_rounds: 3.5,
  max_session_rounds: 9,
  call_count: 42,
  services: [
    { key: 'api', label: '后端 API', status: 'ok', detail: '正常响应' },
    { key: 'chroma', label: 'Chroma 向量服务', status: 'ok', detail: '127.0.0.1:8000' },
    { key: 'embedding', label: 'Embedding 向量化', status: 'ok', detail: '正常 · Mock' },
    {
      key: 'bm25_cache',
      label: 'BM25 内存索引',
      status: 'idle',
      detail: '已缓存 0/2 个知识库',
      cached_kb_count: 0
    },
    { key: 'sqlite', label: '会话存储', status: 'ok', detail: '消息 80 条 / 会话 12 个' }
  ],
  alerts: [
    {
      level: 'error',
      title: '文档解析失败',
      message: '损坏样例.pdf: 解析失败（Mock）'
    }
  ],
  generated_at: '2026-07-19T00:00:00Z'
}

/** SSE 模拟分段答案 + done.references */
export const MOCK_SSE_ANSWER =
  '根据公司考勤制度，工作满一年的员工可享受 5 天年假。年假应在当年 12 月 31 日前使用完毕。'

export const MOCK_SSE_REFERENCES = [
  {
    chunk_id: 'c001',
    content: '根据公司规定，工作满一年的员工可享受 5 天年假...',
    score: 0.86,
    source_doc: '公司考勤制度.md',
    method: 'vector'
  },
  {
    chunk_id: 'c002',
    content: '年假应在当年 12 月 31 日前使用完毕...',
    score: 0.72,
    source_doc: '公司考勤制度.md',
    method: 'vector'
  }
]

/** 可变会话列表 */
export const mockSessions = [
  {
    session_id: 's001',
    title: '公司年假怎么申请？',
    kb_id: 'kb001',
    last_message: '根据公司考勤制度...',
    updated_at: '2026-07-15T14:30:00'
  }
]

export const mockMessagesBySession = {
  s001: [
    {
      id: 'msg001',
      role: 'user',
      content: '公司年假有几天？',
      created_at: '2026-07-15T14:25:00'
    },
    {
      id: 'msg002',
      role: 'assistant',
      content: '根据公司考勤制度，工作满一年的员工可享受 5 天年假...',
      references: MOCK_SSE_REFERENCES,
      created_at: '2026-07-15T14:25:05'
    }
  ]
}

let idSeq = 100

export function nextMockId(prefix) {
  idSeq += 1
  return `${prefix}${String(idSeq).padStart(3, '0')}`
}
