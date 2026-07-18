/**
 * 智能对话 Pinia Store（前端 B）
 * - 会话列表：置顶 / 重命名 / 删除（真后端 PATCH/DELETE；local-* 本地兜底）
 * - [LUO-F03] 无会话 CRUD 时本地兜底，不阻断 stream
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createChatSession,
  fetchChatSessions,
  fetchChatMessages,
  deleteChatSession,
  updateChatSession,
  streamChat,
  closeSSE,
  createSSEController,
  isChatSessionApiEnabled
} from '@/api/chat'
import { MOCK_OPEN } from '@/mock/flag'
import { mockMessagesBySession } from '@/mock/data'

const SESSION_META_KEY = 'rag-chat-session-meta'

/** [LUO-F03] Mock 或显式开启会话 API 时才请求服务端历史 */
function useRemoteSessions() {
  return MOCK_OPEN() || isChatSessionApiEnabled()
}

function isLocalSessionId(sessionId) {
  return String(sessionId || '').startsWith('local-')
}

function localId() {
  return `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
}

function readSessionMeta() {
  try {
    const raw = localStorage.getItem(SESSION_META_KEY)
    const data = raw ? JSON.parse(raw) : {}
    return data && typeof data === 'object' ? data : {}
  } catch {
    return {}
  }
}

function writeSessionMeta(meta) {
  try {
    localStorage.setItem(SESSION_META_KEY, JSON.stringify(meta || {}))
  } catch {
    /* ignore */
  }
}

function patchLocalMeta(sessionId, patch) {
  const sid = String(sessionId)
  const meta = readSessionMeta()
  const prev = meta[sid] && typeof meta[sid] === 'object' ? meta[sid] : {}
  const next = { ...prev, ...patch }
  if (!next.pinned && !next.title) delete meta[sid]
  else meta[sid] = next
  writeSessionMeta(meta)
  return next
}

function clearLocalMeta(sessionId) {
  const meta = readSessionMeta()
  delete meta[String(sessionId)]
  writeSessionMeta(meta)
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const streaming = ref(false)
  const loading = ref(false)
  const selectedKbId = ref(null)
  const messageCache = ref({})
  let sseController = null

  function abortCurrentStream() {
    closeSSE(sseController)
    sseController = null
    streaming.value = false
  }

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

  function normalizeSession(s) {
    const sid = String(s.session_id)
    const local = isLocalSessionId(sid) ? readSessionMeta()[sid] || {} : {}
    return {
      ...s,
      session_id: sid,
      title: local.title || s.title || '未命名会话',
      pinned: local.pinned != null ? !!local.pinned : !!s.pinned,
      updated_at: s.updated_at || new Date().toISOString()
    }
  }

  function sortSessions(list) {
    return [...list].sort((a, b) => {
      const pinDiff = Number(!!b.pinned) - Number(!!a.pinned)
      if (pinDiff) return pinDiff
      return String(b.updated_at || '').localeCompare(String(a.updated_at || ''))
    })
  }

  function setSessions(list) {
    sessions.value = sortSessions((Array.isArray(list) ? list : []).map(normalizeSession))
  }

  function cacheTurn(turnId, userMsg, aiMsg) {
    if (!turnId) return
    const sid = String(turnId)
    const pair = [userMsg, aiMsg]
    messageCache.value[sid] = pair
    if (MOCK_OPEN()) mockMessagesBySession[sid] = pair
  }

  function rebuildAllHistory() {
    const all = []
    const ordered = [...sessions.value].reverse()
    for (const s of ordered) {
      const sid = String(s.session_id)
      let cached = messageCache.value[sid]
      if ((!cached || !cached.length) && MOCK_OPEN()) {
        cached = mockMessagesBySession[sid]
      }
      if (cached?.length) all.push(...normalizeMessages(cached))
    }
    messages.value = all
  }

  function upsertSession(sessionId, title) {
    const sid = String(sessionId)
    const exists = sessions.value.find((s) => String(s.session_id) === sid)
    if (exists) {
      if (title && isLocalSessionId(sid) && !readSessionMeta()[sid]?.title) {
        exists.title = title
      } else if (title && !exists.title) {
        exists.title = title
      }
      exists.updated_at = new Date().toISOString()
      setSessions(sessions.value)
      return
    }
    setSessions([
      {
        session_id: sid,
        title: title || '新会话',
        kb_id: selectedKbId.value,
        updated_at: new Date().toISOString(),
        pinned: false
      },
      ...sessions.value
    ])
  }

  async function togglePinSession(sessionId) {
    const sid = String(sessionId)
    const row = sessions.value.find((s) => String(s.session_id) === sid)
    if (!row) throw new Error('会话不存在')

    const nextPinned = !row.pinned
    const prevPinned = !!row.pinned
    row.pinned = nextPinned
    setSessions(sessions.value)

    try {
      if (isLocalSessionId(sid) || !useRemoteSessions()) {
        patchLocalMeta(sid, { pinned: nextPinned })
      } else {
        await updateChatSession(sid, { pinned: nextPinned })
      }
      return nextPinned
    } catch (e) {
      row.pinned = prevPinned
      setSessions(sessions.value)
      throw e
    }
  }

  async function renameSession(sessionId, title) {
    const sid = String(sessionId)
    const nextTitle = String(title || '').trim().slice(0, 25)
    if (!nextTitle) throw new Error('请输入会话名称')

    const row = sessions.value.find((s) => String(s.session_id) === sid)
    if (!row) throw new Error('会话不存在')

    const prevTitle = row.title
    row.title = nextTitle
    setSessions(sessions.value)

    try {
      if (isLocalSessionId(sid) || !useRemoteSessions()) {
        patchLocalMeta(sid, { title: nextTitle })
      } else {
        await updateChatSession(sid, { title: nextTitle })
      }
      return true
    } catch (e) {
      row.title = prevTitle
      setSessions(sessions.value)
      throw e
    }
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
        setSessions(sessions.value)
        return sessions.value
      }
      const res = await fetchChatSessions({
        kb_id: selectedKbId.value,
        page: 1,
        page_size: 100
      })
      const data = res.data || {}
      const remote = data.items || data.list || []
      const remoteIds = new Set(remote.map((s) => String(s.session_id)))
      const localOnly = sessions.value.filter(
        (s) => isLocalSessionId(s.session_id) && !remoteIds.has(String(s.session_id))
      )
      setSessions([...localOnly, ...remote])

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
          /* ignore */
        }
      }
      return sessions.value
    } catch (e) {
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  async function createSession() {
    abortCurrentStream()
    messages.value = []
    currentSessionId.value = null
    return null
  }

  async function switchSession(sessionId) {
    abortCurrentStream()
    const sid = String(sessionId)
    currentSessionId.value = sid
    loading.value = true
    try {
      if (!messageCache.value[sid]?.length && useRemoteSessions() && !isLocalSessionId(sid)) {
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
          /* ignore */
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
      if (!isLocalSessionId(sid) && useRemoteSessions()) {
        await deleteChatSession(sid)
      }
      sessions.value = sessions.value.filter((s) => String(s.session_id) !== sid)
      clearLocalMeta(sid)
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

    const isLocalTemp = isLocalSessionId(turnId)
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
              const oldMeta = readSessionMeta()[oldId]
              row.session_id = newId
              if (!oldMeta?.title) row.title = title
              if (oldMeta) {
                clearLocalMeta(oldId)
                patchLocalMeta(newId, oldMeta)
              }
            } else {
              upsertSession(newId, title)
            }
            currentSessionId.value = newId
            setSessions(sessions.value)
          }
        }
      },
      onMessage: (event) => {
        if (event.content) aiMessage.content += event.content
        cacheTurn(currentSessionId.value, userMsg, aiMessage)
      },
      onDone: (event) => {
        if (event?.sources?.length) aiMessage.sources = event.sources
        if (event?.content) aiMessage.content += event.content
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
    togglePinSession,
    renameSession,
    sendQuestion,
    abortCurrentStream,
    resetState,
    rebuildAllHistory
  }
})
