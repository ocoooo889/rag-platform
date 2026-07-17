/**
 * 契约对齐 Mock 数据集（1:1 字段）
 * 仅在 VITE_MOCK_OPEN=true 时使用；禁止写入真实请求路径
 */
import { DOC_STATUS } from '@/utils/docStatus'

export const MOCK_USERS = [
  {
    id: 'u001',
    username: 'admin',
    display_name: '管理员',
    role_id: 'r001',
    role_name: '管理员',
    status: '启用',
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'u002',
    username: 'editor',
    display_name: '编辑员',
    role_id: 'r002',
    role_name: '编辑员',
    status: '启用',
    created_at: '2026-07-15T09:10:00'
  },
  {
    id: 'u003',
    username: 'user',
    display_name: '普通用户',
    role_id: 'r003',
    role_name: '普通用户',
    status: '启用',
    created_at: '2026-07-15T09:20:00'
  }
]

export const MOCK_ROLES = [
  {
    id: 'r001',
    name: '管理员',
    description: '系统管理员，拥有全部权限',
    permissions: ['kb:create', 'kb:delete', 'doc:upload', 'doc:delete', 'rag:test', 'chat:send'],
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'r002',
    name: '编辑员',
    description: '可管理知识库和文档',
    permissions: ['kb:create', 'doc:upload', 'rag:test', 'chat:send'],
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'r003',
    name: '普通用户',
    description: '仅可对话与命中测试',
    permissions: ['rag:test', 'chat:send'],
    created_at: '2026-07-15T09:00:00'
  }
]

/** 可变知识库列表（Mock CRUD） */
export const mockKbList = [
  {
    id: 'kb001',
    name: '公司制度知识库',
    description: '存放公司内部制度文档',
    doc_count: 4,
    chunk_count: 60,
    created_at: '2026-07-15T09:00:00'
  },
  {
    id: 'kb002',
    name: '产品手册知识库',
    description: '产品说明与 FAQ',
    doc_count: 1,
    chunk_count: 12,
    created_at: '2026-07-15T10:00:00'
  }
]

/** 可变文档列表 — 严格契约字段（filename / uploaded_at / status） */
export const mockDocList = [
  {
    id: 'doc001',
    kb_id: 'kb001',
    filename: '公司考勤制度.md',
    file_type: 'md',
    file_size: 15230,
    chunk_count: 30,
    status: DOC_STATUS.COMPLETED,
    uploaded_at: '2026-07-15T09:05:00'
  },
  {
    id: 'doc002',
    kb_id: 'kb001',
    filename: '报销流程说明.md',
    file_type: 'md',
    file_size: 8200,
    chunk_count: 18,
    status: DOC_STATUS.COMPLETED,
    uploaded_at: '2026-07-15T09:20:00'
  },
  {
    id: 'doc003',
    kb_id: 'kb001',
    filename: '待处理制度草稿.md',
    file_type: 'md',
    file_size: 4100,
    chunk_count: 0,
    status: DOC_STATUS.PROCESSING,
    uploaded_at: '2026-07-16T08:00:00'
  },
  {
    id: 'doc005',
    kb_id: 'kb001',
    filename: '解析失败样例.md',
    file_type: 'md',
    file_size: 2100,
    chunk_count: 0,
    status: DOC_STATUS.FAILED,
    uploaded_at: '2026-07-16T09:00:00'
  },
  {
    id: 'doc004',
    kb_id: 'kb002',
    filename: '产品FAQ.txt',
    file_type: 'txt',
    file_size: 5600,
    chunk_count: 12,
    status: DOC_STATUS.COMPLETED,
    uploaded_at: '2026-07-15T11:00:00'
  }
]

/** 命中检索分片池 — 对齐 hits[] 字段 */
export const MOCK_HITS_POOL = [
  {
    chunk_id: 'c001',
    content: '根据公司规定，工作满一年的员工可享受 5 天年假；满三年可享受 10 天年假。',
    score: 0.86,
    source_doc: '公司考勤制度.md',
    doc_id: 'doc001'
  },
  {
    chunk_id: 'c002',
    content: '年假应在当年 12 月 31 日前使用完毕，逾期未休视为自动放弃。',
    score: 0.72,
    source_doc: '公司考勤制度.md',
    doc_id: 'doc001'
  },
  {
    chunk_id: 'c003',
    content: '报销需在费用发生后 30 日内提交，并附发票与审批单。',
    score: 0.81,
    source_doc: '报销流程说明.md',
    doc_id: 'doc002'
  },
  {
    chunk_id: 'c004',
    content: '差旅住宿标准：一线城市每日不超过 500 元，其他城市不超过 350 元。',
    score: 0.68,
    source_doc: '报销流程说明.md',
    doc_id: 'doc002'
  },
  {
    chunk_id: 'c005',
    content: '产品支持在线工单与电话热线，工作日 9:00-18:00 响应。',
    score: 0.77,
    source_doc: '产品FAQ.txt',
    doc_id: 'doc004'
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
  doc_count: 5,
  chunk_count: 60,
  call_count: null
}

/** SSE 模拟分段答案 + done.references */
export const MOCK_SSE_ANSWER =
  '根据公司考勤制度，工作满一年的员工可享受 5 天年假。年假应在当年 12 月 31 日前使用完毕。'

export const MOCK_SSE_REFERENCES = [
  {
    chunk_id: 'c001',
    content: '根据公司规定，工作满一年的员工可享受 5 天年假...',
    score: 0.86,
    source_doc: '公司考勤制度.md'
  },
  {
    chunk_id: 'c002',
    content: '年假应在当年 12 月 31 日前使用完毕...',
    score: 0.72,
    source_doc: '公司考勤制度.md'
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
