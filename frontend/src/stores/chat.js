/**
 * 智能对话 Pinia Store（前端 B）
 * - 左侧：每条用户提问对应一条历史
 * - 对话区：累积展示全部历史问答
 * - [LUO-F03] 无会话 CRUD 时本地兜底，不阻断 stream
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
  createSSEController,
  isChatSessionApiEnabled
} from '@/api/chat'
import { MOCK_OPEN } from '@/mock/flag'
import { mockMessagesBySession } from '@/mock/data'

/** [LUO-F03] Mock 或显式开启会话 API 时才请求服务端历史 */
function useRemoteSessions() {
  return MOCK_OPEN() || isChatSessionApiEnabled()
}

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
  /** 每条左侧历史对应一轮 [user, assistant] */
  const messageCache = ref({})
  let sseController = null

  function abortCurrentStream() {
    closeSSE(sseController)
    sseController = null
    streaming.value = false
  }

  /** 兼容 Mock references / 后端 sources */
  function normalizeMessages(list) {
    return (Array.isArray(list) ? list : []).map((m) => ({
      role: m.role || 'assistant',
      content: m.content || '',
      error: m.error || '',
      sources: Array.isArray(m.sources)
        ? m.sources
        : Array.isArray(m.references)
          ? m.references
          : []
    }))
  }

  function cacheTurn(turnId, userMsg, aiMsg) {
    if (!turnId) return
    const sid = String(turnId)
    const pair = [userMsg, aiMsg]
    messageCache.value[sid] = pair
    if (MOCK_OPEN()) {
      mockMessagesBySession[sid] = pair
    }
  }

  /** 按左侧历史顺序拼出完整对话（旧→新） */
  function rebuildAllHistory() {
    const all = []
    const ordered = [...sessions.value].reverse()
    for (const s of ordered) {
      const sid = String(s.session_id)
      let cached = messageCache.value[sid]
      if ((!cached || !cached.length) && MOCK_OPEN()) {
        cached = mockMessagesBySession[sid]
      }
      if (cached?.length) {
        all.push(...normalizeMessages(cached))
      }
    }
    messages.value = all
  }

  function upsertSession(sessionId, title) {
    const sid = String(sessionId)
    const exists = sessions.value.find((s) => String(s.session_id) === sid)
    if (exists) {
      if (title) exists.title = title
      exists.updated_at = new Date().toISOString()
      sessions.value = [
        exists,
        ...sessions.value.filter((s) => String(s.session_id) !== sid)
      ]
      return
    }
    sessions.value.unshift({
      session_id: sid,
      title: title || '新会话',
      kb_id: selectedKbId.value,
      updated_at: new Date().toISOString()
    })
  }

  async function ensureTurnSession(title) {
    if (useRemoteSessions()) {
      try {
        const res = await createChatSession({
          kb_id: selectedKbId.value,
          title
        })
        const sessionId = String(res.data?.session_id || res.data?.id || '')
        if (sessionId) {
          upsertSession(sessionId, title)
          return sessionId
        }
      } catch (e) {
        // 回落本地
      }
    }
    const tempId = localId()
    upsertSession(tempId, title)
    return tempId
  }

  async function loadSessions() {
    loading.value = true
    try {
      if (!useRemoteSessions()) {
        return sessions.value
      }
      const res = await fetchChatSessions({ kb_id: selectedKbId.value })
      const data = res.data || {}
      const remote = data.items || data.list || []
      const remoteIds = new Set(remote.map((s) => String(s.session_id)))
      const localOnly = sessions.value.filter(
        (s) => !remoteIds.has(String(s.session_id))
      )
      sessions.value = [...localOnly, ...remote]

      // 预取每条历史的消息，便于拼完整对话
      for (const s of remote) {
        const sid = String(s.session_id)
        if (messageCache.value[sid]?.length) continue
        try {
          const msgRes = await fetchChatMessages(sid)
          const msgData = msgRes.data || {}
          const list = normalizeMessages(
            msgData.items || msgData.list || msgData.messages || []
          )
          if (list.length) {
            messageCache.value[sid] = list
            if (MOCK_OPEN()) mockMessagesBySession[sid] = list
          }
        } catch (e) {
          // 忽略单条失败
        }
      }
      return sessions.value
    } catch (e) {
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  /** 开启新对话：清空主区，保留左侧历史列表 */
  async function createSession() {
    abortCurrentStream()
    messages.value = []
    currentSessionId.value = null
    return null
  }

  /** 点击左侧：选中该项，主区展示全部历史对话 */
  async function switchSession(sessionId) {
    abortCurrentStream()
    const sid = String(sessionId)
    currentSessionId.value = sid
    loading.value = true
    try {
      if (!messageCache.value[sid]?.length && useRemoteSessions()) {
        try {
          const res = await fetchChatMessages(sid)
          const data = res.data || {}
          const list = normalizeMessages(
            data.items || data.list || data.messages || []
          )
          if (list.length) {
            messageCache.value[sid] = list
            if (MOCK_OPEN()) mockMessagesBySession[sid] = list
          }
        } catch (e) {
          // ignore
        }
      }
      rebuildAllHistory()
    } finally {
      loading.value = false
    }
  }

  async function removeSession(sessionId) {
    const sid = String(sessionId)
    loading.value = true
    try {
      if (useRemoteSessions()) {
        try {
          await deleteChatSession(sid)
        } catch (e) {
          // 忽略
        }
      }
      sessions.value = sessions.value.filter((s) => String(s.session_id) !== sid)
      delete messageCache.value[sid]
      if (MOCK_OPEN()) delete mockMessagesBySession[sid]

      if (currentSessionId.value === sid) {
        currentSessionId.value = sessions.value[0]
          ? String(sessions.value[0].session_id)
          : null
      }
      rebuildAllHistory()
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送问题：
   * - 左侧新增一条历史（标题=问题）
   * - 对话区追加本轮问答，保留已有历史
   */
  async function sendQuestion(question) {
    if (!selectedKbId.value) return
    const text = (question || '').trim()
    if (!text) return

    abortCurrentStream()

    const title = text.slice(0, 20) || '新会话'
    const turnId = await ensureTurnSession(title)
    currentSessionId.value = turnId

    const userMsg = { role: 'user', content: text }
    const aiMessage = { role: 'assistant', content: '', sources: [], error: '' }
    messages.value.push(userMsg, aiMessage)
    cacheTurn(turnId, userMsg, aiMessage)

    streaming.value = true
    sseController = createSSEController()

    const isLocalTemp = String(turnId).startsWith('local-')
    const payload = {
      kb_id: selectedKbId.value,
      query: text,
      search_type: 'hybrid',
      top_n: 3
    }
    if (!isLocalTemp) {
      payload.session_id = String(turnId)
    }

    await streamChat(payload, {
      signal: sseController.signal,
      onStart: (event) => {
        if (event?.session_id) {
          const oldId = String(currentSessionId.value || '')
          const newId = String(event.session_id)
          if (oldId !== newId) {
            const pair = messageCache.value[oldId] || [userMsg, aiMessage]
            messageCache.value[newId] = pair
            delete messageCache.value[oldId]
            if (MOCK_OPEN()) {
              mockMessagesBySession[newId] = pair
              delete mockMessagesBySession[oldId]
            }
            const row = sessions.value.find((s) => String(s.session_id) === oldId)
            if (row) {
              row.session_id = newId
              row.title = title
            } else {
              upsertSession(newId, title)
            }
            currentSessionId.value = newId
          }
        }
      },
      onMessage: (event) => {
        if (event.content) {
          aiMessage.content += event.content
        }
        cacheTurn(currentSessionId.value, userMsg, aiMessage)
      },
      onDone: (event) => {
        if (event?.sources?.length) {
          aiMessage.sources = event.sources
        }
        if (event?.content) {
          aiMessage.content += event.content
        }
        if (!aiMessage.content) {
          aiMessage.content =
            '当前知识库暂无相关内容，请更换问题或补充文档后重试。'
        }
        cacheTurn(currentSessionId.value, userMsg, aiMessage)
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
        cacheTurn(currentSessionId.value, userMsg, aiMessage)
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
    resetState,
    rebuildAllHistory
  }
})
