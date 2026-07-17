/**
 * 智能对话会话接口封装（对接后端 A）
 * - 会话 CRUD 走 axios
 * - 流式对话走 fetch + ReadableStream（不使用 EventSource）
 * - session_id 全程按 UUID 字符串传递，不做类型转换
 * - 历史上下文拼接 / 10 轮截断由后端处理
 */
import request, { getToken, getEnvTag } from '@/utils/request'
import { createSSEController, closeSSE } from '@/utils/sse'

/** 创建会话，返回 UUID v4 字符串 session_id */
export function createChatSession(data = {}) {
  return request.post('/api/chat/session', data)
}

/** 获取当前用户全部历史会话列表 */
export function fetchChatSessions() {
  return request.get('/api/chat/sessions')
}

/** 获取指定会话历史消息（后端已完成 10 轮截断） */
export function fetchChatMessages(sessionId) {
  return request.get(`/api/chat/${sessionId}/messages`)
}

/** 删除会话及其消息记录 */
export function deleteChatSession(sessionId) {
  return request.delete(`/api/chat/${sessionId}`)
}

/**
 * 流式对话：fetch + ReadableStream + AbortController
 * @param {{ session_id: string, kb_id: string|number, question: string }} payload
 * @param {{ onMessage: Function, onDone: Function, onError: Function, signal?: AbortSignal }} handlers
 * @returns {AbortController}
 */
export async function streamChat(payload, handlers = {}) {
  const { onMessage, onDone, onError } = handlers
  const controller = handlers.signal ? null : createSSEController()
  const signal = handlers.signal || controller.signal

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`
      },
      body: JSON.stringify({
        ...payload,
        // session_id 保持字符串；env 由请求体携带，与全局拦截语义一致
        session_id: String(payload.session_id),
        env: getEnvTag()
      }),
      signal
    })

    if (!response.ok) {
      let errBody = null
      try {
        errBody = await response.json()
      } catch (e) {
        // ignore parse error
      }
      const error = errBody || { code: response.status, message: '流式对话请求失败' }
      onError && onError(error)
      return controller
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let finished = false

    const finish = (event) => {
      if (finished) return
      finished = true
      onDone && onDone(event)
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // 按 SSE 事件块拆分（空行分隔）
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''

      for (const chunk of chunks) {
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (!raw || raw === '[DONE]') {
            finish()
            continue
          }
          try {
            const event = JSON.parse(raw)
            if (event.done) {
              finish(event)
            } else {
              onMessage && onMessage(event)
            }
          } catch (e) {
            // 非 JSON 片段按纯文本增量追加
            onMessage && onMessage({ content: raw })
          }
        }
      }
    }
    finish()
  } catch (error) {
    if (error?.name === 'AbortError') {
      // 主动中断不视为业务异常
      return controller
    }
    onError && onError(error)
  }

  return controller
}

/** 对外暴露关闭能力，便于页面统一调用 */
export { closeSSE, createSSEController }
