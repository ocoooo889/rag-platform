/**
 * 智能对话 Pinia Store
 * - P0：kb 范围 + SSE 流式（POST /api/chat/stream）
 * - session_id 可由后端 start 事件回传；无会话 CRUD 时走内存列表兜底
 * - resetState：登出清空，防止跨账号污染
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

function localId() {
  return `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const streaming = ref(false)
  const loading = ref(false)
  const selectedKbId = ref(null)
  /** 无后端历史接口时，按 session 缓存消息 */
  const messageCache = ref({})
  let sseController = null

  function abortCurrentStream() {
    closeSSE(sseController)
    sseController = null
    streaming.value = false
  }

  function cacheCurrentMessages() {
    if (!currentSessionId.value) return
    messageCache.value[String(currentSessionId.value)] = [...messages.value]
  }

  function upsertSession(sessionId, title) {
    const sid = String(sessionId)
    const exists = sessions.value.find((s) => String(s.session_id) === sid)
    if (exists) {
      if (title) exists.title = title
      exists.updated_at = new Date().toISOString()
      return
    }
    sessions.value.unshift({
      session_id: sid,
      title: title || '新会话',
      kb_id: selectedKbId.value,
      updated_at: new Date().toISOString()
    })
  }

  async function loadSessions() {
    loading.value = true
    try {
      const res = await fetchChatSessions({ kb_id: selectedKbId.value })
      const data = res.data || {}
      sessions.value = data.items || data.list || []
      return sessions.value
    } catch (e) {
      // 后端无 sessions 路由时保留内存列表
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  async function createSession(payload = {}) {
    loading.value = true
    try {
      cacheCurrentMessages()
      try {
        const res = await createChatSession({
          kb_id: selectedKbId.value,
          ...payload
        })
        const sessionId = String(res.data?.session_id || res.data?.id || '')
        if (sessionId) {
          upsertSession(sessionId, '新会话')
          await switchSession(sessionId)
          return sessionId
        }
      } catch (e) {
        // 无创建接口：本地占位，真正 id 由 SSE start 回填
      }
      abortCurrentStream()
      const tempId = localId()
      upsertSession(tempId, '新会话')
      currentSessionId.value = tempId
      messages.value = []
      messageCache.value[tempId] = []
      return tempId
    } finally {
      loading.value = false
    }
  }

  async function switchSession(sessionId) {
    abortCurrentStream()
    cacheCurrentMessages()
    const sid = String(sessionId)
    currentSessionId.value = sid
    loading.value = true
    try {
      try {
        const res = await fetchChatMessages(sid)
        const data = res.data || {}
        messages.value = data.items || data.list || data.messages || []
        messageCache.value[sid] = [...messages.value]
      } catch (e) {
        messages.value = [...(messageCache.value[sid] || [])]
      }
    } finally {
      loading.value = false
    }
  }

  async function removeSession(sessionId) {
    const sid = String(sessionId)
    loading.value = true
    try {
      try {
        await deleteChatSession(sid)
      } catch (e) {
        // 忽略后端无删除接口
      }
      sessions.value = sessions.value.filter((s) => String(s.session_id) !== sid)
      delete messageCache.value[sid]
      if (currentSessionId.value === sid) {
        abortCurrentStream()
        currentSessionId.value = null
        messages.value = []
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送问题并接收 SSE 流式回复
   * 入参对齐契约：kb_id + query + session_id
   */
  async function sendQuestion(question) {
    if (!selectedKbId.value) return
    const text = (question || '').trim()
    if (!text) return

    // 无会话时自动建本地会话，session_id 可在 start 事件被后端替换
    if (!currentSessionId.value) {
      await createSession()
    }

    abortCurrentStream()

    messages.value.push({ role: 'user', content: text })
    const aiMessage = { role: 'assistant', content: '', sources: [], error: '' }
    messages.value.push(aiMessage)
    cacheCurrentMessages()

    streaming.value = true
    sseController = createSSEController()

    // 本地临时 id 不传给后端，由 SSE start 回填真实 session_id
    const isLocalTemp = String(currentSessionId.value || '').startsWith('local-')
    const payload = {
      kb_id: selectedKbId.value,
      query: text,
      search_type: 'hybrid',
      top_n: 3
    }
    if (currentSessionId.value && !isLocalTemp) {
      payload.session_id = String(currentSessionId.value)
    }

    await streamChat(payload, {
      signal: sseController.signal,
      onStart: (event) => {
        if (event?.session_id) {
          const oldId = String(currentSessionId.value || '')
          const newId = String(event.session_id)
          if (oldId !== newId) {
            const cached = messageCache.value[oldId] || messages.value
            messageCache.value[newId] = [...cached]
            delete messageCache.value[oldId]
            const row = sessions.value.find((s) => String(s.session_id) === oldId)
            if (row) {
              row.session_id = newId
              row.title = text.slice(0, 20) || row.title
            } else {
              upsertSession(newId, text.slice(0, 20))
            }
            currentSessionId.value = newId
          }
        }
      },
      onMessage: (event) => {
        if (event.content) {
          aiMessage.content += event.content
        }
        cacheCurrentMessages()
      },
      onDone: (event) => {
        if (event?.sources?.length) {
          aiMessage.sources = event.sources
        }
        if (event?.content) {
          aiMessage.content += event.content
        }
        if (!aiMessage.content) {
          aiMessage.content = '当前知识库暂无相关内容，请更换问题或补充文档后重试。'
        }
        upsertSession(currentSessionId.value, text.slice(0, 20))
        cacheCurrentMessages()
        streaming.value = false
        sseController = null
      },
      onError: (error) => {
        const code = error?.code
        const msg = error?.message || error?.msg || ''
        if (code === 5002) {
          aiMessage.error = '大模型服务异常，请稍后重试'
          aiMessage.content = ''
        } else if (code === 4002) {
          aiMessage.error = msg || '文档正在处理中，请等待处理完成后再试'
          aiMessage.content = ''
        } else if (!aiMessage.content) {
          aiMessage.error = msg || '回答生成失败，请稍后重试'
        }
        cacheCurrentMessages()
        streaming.value = false
        sseController = null
      }
    })
  }

  function resetState() {
    abortCurrentStream()
    sessions.value = []
    currentSessionId.value = null
    messages.value = []
    messageCache.value = {}
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
