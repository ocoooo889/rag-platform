/**
 * 智能对话 Pinia Store
 * - 会话列表 / 当前 session_id / 消息 / 流式状态
 * - resetState：登出或切账号时完整清空，防止跨账号污染
 * - session_id 由后端生成，前端不自主创建 UUID
 * - 消息截断由后端处理，前端仅接收过滤后列表
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createChatSession,
  fetchChatSessions,
  fetchChatMessages,
  deleteChatSession,
  streamChat,
  closeSSE,
  createSSEController
} from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const streaming = ref(false)
  const loading = ref(false)
  const selectedKbId = ref(null)
  /** 当前流式 AbortController，切会话 / 新提问 / 卸载时 abort */
  let sseController = null

  function abortCurrentStream() {
    closeSSE(sseController)
    sseController = null
    streaming.value = false
  }

  async function loadSessions() {
    loading.value = true
    try {
      const res = await fetchChatSessions()
      const data = res.data || {}
      sessions.value = data.items || data.list || []
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  async function createSession(payload = {}) {
    loading.value = true
    try {
      const res = await createChatSession({
        kb_id: selectedKbId.value,
        ...payload
      })
      // 后端返回固定 UUID v4 字符串，保持字符串传递
      const sessionId = String(res.data?.session_id || res.data?.id || '')
      await loadSessions()
      if (sessionId) {
        await switchSession(sessionId)
      }
      return sessionId
    } finally {
      loading.value = false
    }
  }

  async function switchSession(sessionId) {
    // 切换会话前先中断当前 SSE，避免多路并发打字
    abortCurrentStream()
    const sid = String(sessionId)
    currentSessionId.value = sid
    loading.value = true
    try {
      const res = await fetchChatMessages(sid)
      const data = res.data || {}
      // 直接使用后端过滤后的消息列表，不做前端裁剪
      messages.value = data.items || data.list || data.messages || []
    } finally {
      loading.value = false
    }
  }

  async function removeSession(sessionId) {
    const sid = String(sessionId)
    loading.value = true
    try {
      await deleteChatSession(sid)
      if (currentSessionId.value === sid) {
        abortCurrentStream()
        currentSessionId.value = null
        messages.value = []
      }
      await loadSessions()
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送问题并接收 SSE 流式回复
   * @param {string} question
   */
  async function sendQuestion(question) {
    if (!currentSessionId.value || !selectedKbId.value) return
    const text = (question || '').trim()
    if (!text) return

    // 新提问前中断上一轮流
    abortCurrentStream()

    // 先推入用户消息气泡
    messages.value.push({
      role: 'user',
      content: text
    })
    // 预置 AI 空气泡，流式增量写入
    const aiMessage = {
      role: 'assistant',
      content: '',
      sources: []
    }
    messages.value.push(aiMessage)

    streaming.value = true
    sseController = createSSEController()

    await streamChat(
      {
        session_id: String(currentSessionId.value),
        kb_id: selectedKbId.value,
        question: text
      },
      {
        signal: sseController.signal,
        onMessage: (event) => {
          if (event.content) {
            aiMessage.content += event.content
          }
          if (event.sources) {
            aiMessage.sources = event.sources
          }
        },
        onDone: (event) => {
          if (event?.sources) {
            aiMessage.sources = event.sources
          }
          if (event?.content) {
            aiMessage.content += event.content
          }
          // 无内容时展示固定兜底
          if (!aiMessage.content) {
            aiMessage.content = '当前知识库暂无相关内容，请更换问题或补充文档后重试。'
          }
          streaming.value = false
          sseController = null
        },
        onError: (error) => {
          // code5002 等由全局拦截/此处兜底文案处理
          if (error?.code === 5002) {
            aiMessage.content = '大模型服务异常，请稍后重试'
          } else if (!aiMessage.content) {
            aiMessage.content = error?.message || '回答生成失败，请稍后重试'
          }
          streaming.value = false
          sseController = null
        }
      }
    )
  }

  /**
   * 登出 / 切账号时调用，组合式 store 无原生 $reset
   * 完整清空会话相关状态，防止跨账号数据污染
   */
  function resetState() {
    abortCurrentStream()
    sessions.value = []
    currentSessionId.value = null
    messages.value = []
    streaming.value = false
    loading.value = false
    selectedKbId.value = null
  }

  return {
    sessions,
    currentSessionId,
    messages,
    streaming,
    loading,
    selectedKbId,
    loadSessions,
    createSession,
    switchSession,
    removeSession,
    sendQuestion,
    abortCurrentStream,
    resetState
  }
})
