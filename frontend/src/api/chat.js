/**
 * 智能对话会话接口
 * Mock / Real 双分支；SSE 经 runSSE 通用钩子（页面无感知）
 */
import request, { API_BASE_URL, getToken, getEnvTag } from '@/utils/request'
import { isMockOpen, mockResolve } from '@/mock/flag'
import {
  mockSessions,
  mockMessagesBySession,
  nextMockId,
  MOCK_SSE_ANSWER,
  MOCK_SSE_REFERENCES
} from '@/mock/data'
import { matchMockScenario } from '@/mock/scenarios'
import { runSSE, closeSSE, createSSEController } from '@/composables/useSSE'

/** 创建会话 */
export async function createChatSession(data = {}) {
  if (isMockOpen()) {
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
  return request.post('/api/chat/session', data, { silent: true })
}

/** 获取会话列表 */
export async function fetchChatSessions(params = {}) {
  if (isMockOpen()) {
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
  return request.get('/api/chat/sessions', { params, silent: true })
}

/** 获取会话历史 */
export async function fetchChatMessages(sessionId) {
  if (isMockOpen()) {
    const items = mockMessagesBySession[String(sessionId)] || []
    return mockResolve({
      items,
      total: items.length,
      page: 1,
      page_size: 50
    })
  }
  return request
    .get(`/api/chat/sessions/${sessionId}/messages`, { silent: true })
    .catch(() => request.get(`/api/chat/${sessionId}/messages`, { silent: true }))
}

/** 删除会话 */
export async function deleteChatSession(sessionId) {
  if (isMockOpen()) {
    const sid = String(sessionId)
    const idx = mockSessions.findIndex((s) => String(s.session_id) === sid)
    if (idx !== -1) mockSessions.splice(idx, 1)
    delete mockMessagesBySession[sid]
    return mockResolve(null)
  }
  return request
    .delete(`/api/chat/sessions/${sessionId}`, { silent: true })
    .catch(() => request.delete(`/api/chat/${sessionId}`, { silent: true }))
}

/**
 * 流式对话：组装契约入参后交给 runSSE
 * Mock 异常：query 含 __timeout__ / __5002__ 等触发词
 */
export async function streamChat(payload, handlers = {}) {
  const body = {
    kb_id: String(payload.kb_id),
    query: payload.query || payload.question || '',
    search_type: payload.search_type || 'hybrid',
    top_n: payload.top_n || 3,
    env: getEnvTag()
  }
  if (payload.session_id) {
    body.session_id = String(payload.session_id)
  }

  const scenario = isMockOpen() ? matchMockScenario(body.query) : null
  let errorScenario = null
  if (scenario === 'timeout') errorScenario = 'timeout'
  if (scenario === 'llm_error') errorScenario = 'llm_error'

  return runSSE({
    payload: body,
    url: `${API_BASE_URL}/api/chat/stream`,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    },
    body,
    signal: handlers.signal,
    handlers: {
      onStart: handlers.onStart,
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
