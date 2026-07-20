/**
 * 对话检索模式标识（仅前端展示/本地持久化）
 * 后端契约：search_type = vector | keyword | hybrid
 * 运行时降级：SSE status.message 含「关键词检索兜底」等文案
 */

export const RETRIEVAL_MODE = {
  SEMANTIC: 'semantic',
  KEYWORD: 'keyword',
  HYBRID: 'hybrid'
}

/** 消息级展示文案（需求：语义检索 / 关键词检索） */
export const RETRIEVAL_MODE_LABEL = {
  semantic: '语义检索',
  vector: '语义检索',
  keyword: '关键词检索',
  bm25: '关键词检索',
  hybrid: '混合检索'
}

export function getRetrievalModeLabel(mode) {
  const key = String(mode || '').toLowerCase()
  return RETRIEVAL_MODE_LABEL[key] || ''
}

/** 检测 SSE status 是否为向量→关键词降级 */
export function isDegradeStatusMessage(message = '') {
  return /关键词检索兜底|已切换关键词|已启用关键词|向量检索.*不可用/.test(String(message || ''))
}

/**
 * 根据请求 search_type + 是否降级，得到消息级检索模式
 * @param {{ requested?: string, degraded?: boolean }} opts
 */
export function resolveRetrievalMode({ requested = 'vector', degraded = false } = {}) {
  const req = String(requested || 'vector').toLowerCase()
  if (req === 'keyword' || req === 'bm25') return RETRIEVAL_MODE.KEYWORD
  if (degraded) return RETRIEVAL_MODE.KEYWORD
  if (req === 'hybrid') return RETRIEVAL_MODE.HYBRID
  return RETRIEVAL_MODE.SEMANTIC
}

export function retrievalModeTagType(mode) {
  const m = String(mode || '').toLowerCase()
  if (m === 'keyword' || m === 'bm25') return 'warning'
  if (m === 'hybrid') return 'info'
  return 'success'
}
