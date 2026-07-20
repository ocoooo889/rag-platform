/**
 * 智能对话会话接口（前端 B）
 * Mock / Real 双分支；SSE 经 runSSE 通用钩子（页面无感知）
 *
 * [LUO-F03] 真后端目前仅有 send/stream。默认不请求 session CRUD，避免 404；
 * 仅 stream/send。后端补齐会话 API 后设 VITE_CHAT_SESSION_API=true 再开启。
 */
import request, { API_BASE_URL, getToken, getEnvTag } from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import {
  mockSessions,
  mockMessagesBySession,
  nextMockId,
  MOCK_SSE_ANSWER,
  MOCK_SSE_REFERENCES
} from '@/mock/data'
import { matchMockScenario } from '@/mock/scenarios'
import { runSSE, closeSSE, createSSEController } from '@/composables/useSSE'

/** 是否允许打真实会话 CRUD（默认 false = 本地会话降级） */
export function isChatSessionApiEnabled() {
  return String(import.meta.env.VITE_CHAT_SESSION_API || '').toLowerCase() === 'true'
}

function rejectSessionApiUnavailable() {
  return Promise.reject({
    code: 404,
    msg: '会话历史接口未启用，已使用本地会话',
    data: { localOnly: true }
  })
}

/** 创建会话 */
export async function createChatSession(data = {}) {
  if (MOCK_OPEN()) {
    const sessionId = nextMockId('s')
    const row = {
      session_id: sessionId,
      title: '新会话',
      kb_id: data.kb_id || null,
      last_message: '',
      updated_at: new Date().toISOString()
    }
    mockSessions.unshift(row)
    mockMessagesBySession[sessionId] = []
    return mockResolve({ session_id: sessionId })
  }
  // 后端无独立创建端点：本地生成 session_id，首条 send/stream 时落库
  const localId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
  return Promise.resolve({ data: { session_id: localId, localOnly: true } })
}

/** 获取会话列表 */
export async function fetchChatSessions(params = {}) {
  if (MOCK_OPEN()) {
    let items = [...mockSessions]
    if (params.kb_id) {
      items = items.filter((s) => String(s.kb_id) === String(params.kb_id))
    }
    const page = Number(params.page) || 1
    const pageSize = Number(params.page_size) || 20
    return mockResolve({
      items,
      total: items.length,
      page,
      page_size: pageSize
    })
  }
  if (!isChatSessionApiEnabled()) {
    return rejectSessionApiUnavailable()
  }
  return request.get('/api/chat/sessions', { params, silent: true })
}

/** 获取会话历史 */
export async function fetchChatMessages(sessionId) {
  if (MOCK_OPEN()) {
    const items = mockMessagesBySession[String(sessionId)] || []
    return mockResolve({
      items,
      total: items.length,
      page: 1,
      page_size: 50
    })
  }
  if (!isChatSessionApiEnabled()) {
    return rejectSessionApiUnavailable()
  }
  return request.get(`/api/chat/sessions/${sessionId}/messages`, { silent: true })
}

/** 删除会话 */
export async function deleteChatSession(sessionId) {
  if (MOCK_OPEN()) {
    const sid = String(sessionId)
    const idx = mockSessions.findIndex((s) => String(s.session_id) === sid)
    if (idx !== -1) mockSessions.splice(idx, 1)
    delete mockMessagesBySession[sid]
    return mockResolve(null)
  }
  if (!isChatSessionApiEnabled()) {
    return rejectSessionApiUnavailable()
  }
  return request.delete(`/api/chat/sessions/${sessionId}`, { silent: true })
}

/** 更新会话：重命名 / 置顶 */
export async function updateChatSession(sessionId, data = {}) {
  const sid = String(sessionId)
  const payload = {}
  if (data.title != null) payload.title = String(data.title).trim().slice(0, 25)
  if (data.pinned != null) payload.pinned = !!data.pinned

  if (MOCK_OPEN()) {
    const row = mockSessions.find((s) => String(s.session_id) === sid)
    if (!row) {
      return Promise.reject({ code: 404, msg: '会话不存在' })
    }
    if (payload.title != null) {
      if (!payload.title) {
        return Promise.reject({ code: 400, msg: '标题不能为空' })
      }
      row.title = payload.title
    }
    if (payload.pinned != null) {
      row.pinned = payload.pinned
    }
    // 置顶排前
    mockSessions.sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned))
    return mockResolve({
      session_id: sid,
      title: row.title || '',
      pinned: !!row.pinned
    })
  }
  if (!isChatSessionApiEnabled()) {
    return rejectSessionApiUnavailable()
  }
  return request.patch(`/api/chat/sessions/${sid}`, payload)
}

/**
 * 流式对话：组装契约入参后交给 runSSE
 * Mock 异常：query 含 __timeout__ / __5002__ 等触发词
 */
function normalizeUrl(url = '') {
  return String(url || '').trim().replace(/\/$/, '')
}

/** 开发态 SSE 直连后端，避开 Vite http-proxy 对 event-stream 的攒包 */
function resolveStreamUrl() {
  if (API_BASE_URL) return `${API_BASE_URL}/api/chat/stream`
  const proxy = normalizeUrl(
    import.meta.env.VITE_API_PROXY || import.meta.env.VITE_API_PROXY_TARGET || ''
  )
  if (import.meta.env.DEV && proxy) {
    return `${proxy}/api/chat/stream`
  }
  return '/api/chat/stream'
}

export async function streamChat(payload, handlers = {}) {
  const body = {
    kb_id: String(payload.kb_id),
    query: payload.query || payload.question || '',
    // 对话默认向量检索，比 hybrid 少一次全库 BM25，首 token 更快
    search_type: payload.search_type || 'vector',
    top_n: payload.top_n || 3,
    env: getEnvTag()
  }
  if (payload.session_id) {
    body.session_id = String(payload.session_id)
  }
  // 与 ChatRequest.enable_rerank 对齐；undefined 时不传，由服务端默认决定
  if (typeof payload.enable_rerank === 'boolean') {
    body.enable_rerank = payload.enable_rerank
  }

  const scenario = MOCK_OPEN() ? matchMockScenario(body.query) : null
  let errorScenario = null
  if (scenario === 'timeout') errorScenario = 'timeout'
  if (scenario === 'llm_error') errorScenario = 'llm_error'

  return runSSE({
    payload: body,
    url: resolveStreamUrl(),
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    },
    body,
    signal: handlers.signal,
    handlers: {
      onStart: handlers.onStart,
      onStatus: handlers.onStatus,
      onMessage: handlers.onMessage,
      onDone: handlers.onDone,
      onError: handlers.onError
    },
    mock: {
      answerText: MOCK_SSE_ANSWER,
      references: MOCK_SSE_REFERENCES,
      intervalMs: 45,
      chunkSize: 2,
      errorScenario,
      sessionIdFactory: () => nextMockId('s'),
      requestIdFactory: () => nextMockId('req')
    }
  })
}

export { closeSSE, createSSEController }

/** 预热知识库索引 / 向量链路，缩短首问等待 */
export async function warmupChat(kbId) {
  if (!kbId) return null
  if (MOCK_OPEN()) {
    return mockResolve({ kb_id: kbId, chunks: 0, vector_ready: true })
  }
  return request.post(
    '/api/chat/warmup',
    null,
    { params: { kb_id: String(kbId) }, silent: true }
  )
}
