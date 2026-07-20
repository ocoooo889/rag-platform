/**
 * 智能对话 Pinia Store
 * - 多轮：同一会话复用 session_id，主区只展示当前会话
 * - 历史：优先读写用户本地 localStorage，远程会话 API 作补充
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
  isChatSessionApiEnabled,
  warmupChat
} from '@/api/chat'
import { MOCK_OPEN } from '@/mock/flag'
import { mockMessagesBySession } from '@/mock/data'
import {
  isDegradeStatusMessage,
  resolveRetrievalMode
} from '@/utils/retrievalMode'
import { readCurrentUserId } from '@/utils/cacheLifecycle'

const SESSION_META_KEY = 'rag-chat-session-meta'
const HISTORY_KEY_PREFIX = 'rag-chat-history'
const MAX_SESSIONS = 80
const MAX_MESSAGES_PER_SESSION = 120

function useRemoteSessions() {
  return MOCK_OPEN() || isChatSessionApiEnabled()
}

function isLocalSessionId(sessionId) {
  return String(sessionId || '').startsWith('local-')
}

function localId() {
  return `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
}

function msgId() {
  return `m-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function currentUserScope() {
  return readCurrentUserId()
}

function historyStorageKey() {
  return `${HISTORY_KEY_PREFIX}:${currentUserScope()}`
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

function readLocalHistory() {
  try {
    const raw = localStorage.getItem(historyStorageKey())
    const data = raw ? JSON.parse(raw) : null
    if (!data || typeof data !== 'object') return null
    return data
  } catch {
    return null
  }
}

function writeLocalHistory(payload) {
  try {
    localStorage.setItem(historyStorageKey(), JSON.stringify(payload))
  } catch (e) {
    // 配额满时裁剪后再试
    try {
      const slim = {
        ...payload,
        sessions: (payload.sessions || []).slice(0, 40),
        messagesBySession: {}
      }
      for (const s of slim.sessions) {
        const sid = String(s.session_id)
        const list = (payload.messagesBySession || {})[sid] || []
        slim.messagesBySession[sid] = list.slice(-40)
      }
      localStorage.setItem(historyStorageKey(), JSON.stringify(slim))
    } catch {
      /* ignore */
    }
  }
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const streaming = ref(false)
  const loading = ref(false)
  const selectedKbId = ref(null)
  /** 流式阶段提示：检索中 / 生成中 */
  const streamStatus = ref('')
  /** 最近一次向量→关键词降级通知（供对话页弹窗消费，用过即清） */
  const lastDegradeNotice = ref(null)
  /** 知识库后台预热中（不挡发送） */
  const kbWarming = ref(false)
  /** session_id -> 消息数组（与当前展示共用同一引用） */
  const messageCache = ref({})
  let sseController = null
  let persistTimer = null
  let hydrated = false
  /** 流式 UI 节流定时器（abort 时也要清） */
  let streamUiTimer = null
  /** 预热世代：切库时递增，忽略过期回调 */
  let warmupGeneration = 0

  function clearStreamUiTimer() {
    if (streamUiTimer != null) {
      clearInterval(streamUiTimer)
      streamUiTimer = null
    }
  }

  function abortCurrentStream() {
    const wasStreaming = streaming.value
    closeSSE(sseController)
    sseController = null
    streaming.value = false
    streamStatus.value = ''
    clearStreamUiTimer()
    if (wasStreaming) {
      // 停止生成时落盘已输出内容
      persistNow()
    }
  }

  function normalizeMessages(list) {
    return (Array.isArray(list) ? list : []).map((m) => ({
      id: m.id || msgId(),
      role: m.role || 'assistant',
      content: m.content || '',
      contentDisplay: m.contentDisplay || '',
      error: m.error || '',
      sources: Array.isArray(m.sources)
        ? m.sources
        : Array.isArray(m.references)
          ? m.references
          : [],
      searchType: m.searchType || '',
      retrievalMode: m.retrievalMode || '',
      retrievalDegraded: !!m.retrievalDegraded
    }))
  }

  function normalizeSession(s) {
    const sid = String(s.session_id)
    const local = readSessionMeta()[sid] || {}
    return {
      ...s,
      session_id: sid,
      title: local.title || s.title || '未命名会话',
      pinned: local.pinned != null ? !!local.pinned : !!s.pinned,
      updated_at: s.updated_at || new Date().toISOString(),
      kb_id: s.kb_id ?? selectedKbId.value
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
    const next = sortSessions((Array.isArray(list) ? list : []).map(normalizeSession))
    sessions.value = next.slice(0, MAX_SESSIONS)
  }

  function persistNow() {
    const run = () => {
      try {
        const messagesBySession = {}
        for (const s of sessions.value) {
          const sid = String(s.session_id)
          const list = messageCache.value[sid]
          if (list?.length) {
            messagesBySession[sid] = list.slice(-MAX_MESSAGES_PER_SESSION).map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content || '',
              contentDisplay: m.contentDisplay || '',
              error: m.error || '',
              sources: Array.isArray(m.sources) ? m.sources : [],
              searchType: m.searchType || '',
              retrievalMode: m.retrievalMode || '',
              retrievalDegraded: !!m.retrievalDegraded
            }))
          }
        }
        const cur = currentSessionId.value
        if (cur && !messagesBySession[String(cur)] && messageCache.value[String(cur)]) {
          messagesBySession[String(cur)] = messageCache.value[String(cur)]
            .slice(-MAX_MESSAGES_PER_SESSION)
            .map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content || '',
              contentDisplay: m.contentDisplay || '',
              error: m.error || '',
              sources: Array.isArray(m.sources) ? m.sources : [],
              searchType: m.searchType || '',
              retrievalMode: m.retrievalMode || '',
              retrievalDegraded: !!m.retrievalDegraded
            }))
        }

        writeLocalHistory({
          version: 1,
          updatedAt: new Date().toISOString(),
          currentSessionId: currentSessionId.value,
          selectedKbId: selectedKbId.value,
          sessions: sessions.value.map((s) => ({
            session_id: s.session_id,
            title: s.title,
            kb_id: s.kb_id,
            pinned: !!s.pinned,
            updated_at: s.updated_at
          })),
          messagesBySession
        })
      } catch {
        /* ignore */
      }
    }
    // 大 JSON 序列化放到空闲时段，避免卡住其它页面
    if (typeof requestIdleCallback === 'function') {
      requestIdleCallback(run, { timeout: 800 })
    } else {
      setTimeout(run, 0)
    }
  }

  function schedulePersist() {
    if (persistTimer) clearTimeout(persistTimer)
    persistTimer = setTimeout(() => {
      persistTimer = null
      persistNow()
    }, 400)
  }

  function hydrateFromLocal() {
    if (hydrated) return
    hydrated = true
    const data = readLocalHistory()
    if (!data) return

    if (data.selectedKbId != null && selectedKbId.value == null) {
      selectedKbId.value = data.selectedKbId
    }

    const cache = {}
    const bySession = data.messagesBySession || {}
    for (const [sid, list] of Object.entries(bySession)) {
      cache[sid] = normalizeMessages(list)
    }
    messageCache.value = cache

    if (Array.isArray(data.sessions) && data.sessions.length) {
      setSessions(data.sessions)
    }

    if (data.currentSessionId) {
      currentSessionId.value = String(data.currentSessionId)
    }
  }

  function bindMessagesToSession(sessionId) {
    const sid = sessionId ? String(sessionId) : null
    if (!sid) {
      messages.value = []
      return
    }
    if (!messageCache.value[sid]) {
      messageCache.value[sid] = []
    }
    // 与 cache 共用引用，流式更新自动同步
    messages.value = messageCache.value[sid]
  }

  function upsertSession(sessionId, title, extra = {}) {
    const sid = String(sessionId)
    const exists = sessions.value.find((s) => String(s.session_id) === sid)
    if (exists) {
      if (title && (!exists.title || exists.title === '新会话' || exists.title === '未命名会话')) {
        exists.title = title
      }
      if (extra.kb_id != null) exists.kb_id = extra.kb_id
      exists.updated_at = new Date().toISOString()
      setSessions(sessions.value)
      schedulePersist()
      return
    }
    setSessions([
      {
        session_id: sid,
        title: title || '新会话',
        kb_id: extra.kb_id ?? selectedKbId.value,
        updated_at: new Date().toISOString(),
        pinned: false
      },
      ...sessions.value
    ])
    schedulePersist()
  }

  function remapSessionId(oldId, newId, title) {
    const from = String(oldId)
    const to = String(newId)
    if (!from || !to || from === to) return

    const list = messageCache.value[from] || messages.value || []
    messageCache.value[to] = list
    delete messageCache.value[from]
    if (MOCK_OPEN()) {
      mockMessagesBySession[to] = list
      delete mockMessagesBySession[from]
    }

    const row = sessions.value.find((s) => String(s.session_id) === from)
    if (row) {
      const oldMeta = readSessionMeta()[from]
      row.session_id = to
      if (title && (!row.title || row.title === '新会话')) row.title = title
      if (oldMeta) {
        clearLocalMeta(from)
        patchLocalMeta(to, oldMeta)
      }
    } else {
      upsertSession(to, title)
    }

    if (String(currentSessionId.value) === from) {
      currentSessionId.value = to
    }
    setSessions(sessions.value)
    bindMessagesToSession(to)
    schedulePersist()
  }

  async function togglePinSession(sessionId) {
    const sid = String(sessionId)
    const row = sessions.value.find((s) => String(s.session_id) === sid)
    if (!row) throw new Error('会话不存在')

    const nextPinned = !row.pinned
    const prevPinned = !!row.pinned
    row.pinned = nextPinned
    setSessions(sessions.value)
    schedulePersist()

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
      schedulePersist()
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
    schedulePersist()

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
      schedulePersist()
      throw e
    }
  }

  /** 新建空会话（开启新对话） */
  async function ensureNewSession(title = '新会话', extra = {}) {
    const kbId = extra.kb_id ?? selectedKbId.value
    if (useRemoteSessions()) {
      try {
        const res = await createChatSession({
          kb_id: kbId,
          title
        })
        const sessionId = String(res.data?.session_id || res.data?.id || '')
        if (sessionId) {
          if (!messageCache.value[sessionId]) messageCache.value[sessionId] = []
          upsertSession(sessionId, title, { kb_id: kbId })
          return sessionId
        }
      } catch {
        /* 回落本地 */
      }
    }
    const tempId = localId()
    messageCache.value[tempId] = []
    upsertSession(tempId, title, { kb_id: kbId })
    return tempId
  }

  async function loadSessions() {
    hydrateFromLocal()
    const keepCurrent = currentSessionId.value
      ? String(currentSessionId.value)
      : null
    loading.value = true
    try {
      if (!useRemoteSessions()) {
        // 纯本地：也按当前知识库过滤侧栏
        if (selectedKbId.value != null && selectedKbId.value !== '') {
          setSessions(
            sessions.value.filter(
              (s) =>
                s.kb_id == null ||
                s.kb_id === '' ||
                String(s.kb_id) === String(selectedKbId.value)
            )
          )
        }
        if (keepCurrent && sessions.value.some((s) => String(s.session_id) === keepCurrent)) {
          bindMessagesToSession(keepCurrent)
        } else if (sessions.value.length) {
          currentSessionId.value = String(sessions.value[0].session_id)
          bindMessagesToSession(currentSessionId.value)
        } else {
          currentSessionId.value = null
          messages.value = []
        }
        return sessions.value
      }

      const res = await fetchChatSessions({
        kb_id: selectedKbId.value,
        page: 1,
        page_size: 100
      })
      const data = res.data || {}
      const remote = data.items || data.list || []

      // 增量合并：按 session_id 合并，保留本地独有会话，避免整表覆盖闪烁
      const byId = new Map()
      for (const s of sessions.value) {
        byId.set(String(s.session_id), { ...s })
      }
      for (const s of remote) {
        const sid = String(s.session_id)
        const prev = byId.get(sid)
        byId.set(sid, prev ? { ...prev, ...s, title: s.title || prev.title } : { ...s })
      }
      // 增量合并后按当前知识库过滤，避免侧栏串库
      let merged = [...byId.values()]
      if (selectedKbId.value != null && selectedKbId.value !== '') {
        merged = merged.filter(
          (s) =>
            s.kb_id == null ||
            s.kb_id === '' ||
            String(s.kb_id) === String(selectedKbId.value)
        )
      }
      setSessions(merged)

      // 已有当前会话则不跳转；仅在空闲时选默认
      if (keepCurrent && byId.has(keepCurrent)) {
        currentSessionId.value = keepCurrent
        bindMessagesToSession(keepCurrent)
      } else if (!currentSessionId.value && sessions.value.length) {
        currentSessionId.value = String(sessions.value[0].session_id)
        bindMessagesToSession(currentSessionId.value)
      }

      // 只补当前会话缺失消息；其余会话在 switchSession 时懒加载
      const cur = currentSessionId.value ? String(currentSessionId.value) : null
      if (
        cur &&
        !isLocalSessionId(cur) &&
        !messageCache.value[cur]?.length
      ) {
        try {
          const msgRes = await fetchChatMessages(cur)
          const msgData = msgRes.data || {}
          const list = normalizeMessages(
            msgData.items || msgData.list || msgData.messages || []
          )
          if (list.length) {
            messageCache.value[cur] = list
            if (MOCK_OPEN()) mockMessagesBySession[cur] = list
            if (String(currentSessionId.value) === cur) {
              bindMessagesToSession(cur)
            }
          }
        } catch {
          /* ignore */
        }
      }

      schedulePersist()
      return sessions.value
    } catch {
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  async function createSession(extra = {}) {
    abortCurrentStream()
    const sid = await ensureNewSession('新会话', {
      kb_id: extra.kb_id ?? selectedKbId.value
    })
    currentSessionId.value = sid
    bindMessagesToSession(sid)
    schedulePersist()
    return sid
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
          messageCache.value[sid] = list
          if (MOCK_OPEN()) mockMessagesBySession[sid] = list
        } catch {
          if (!messageCache.value[sid]) messageCache.value[sid] = []
        }
      }
      if (!messageCache.value[sid]) messageCache.value[sid] = []
      bindMessagesToSession(sid)
      schedulePersist()
    } finally {
      loading.value = false
    }
  }

  async function removeSession(sessionId) {
    const sid = String(sessionId)
    loading.value = true
    try {
      if (!isLocalSessionId(sid) && useRemoteSessions()) {
        try {
          await deleteChatSession(sid)
        } catch {
          /* 本地仍删除 */
        }
      }
      sessions.value = sessions.value.filter((s) => String(s.session_id) !== sid)
      clearLocalMeta(sid)
      delete messageCache.value[sid]
      if (MOCK_OPEN()) delete mockMessagesBySession[sid]

      if (String(currentSessionId.value) === sid) {
        const next = sessions.value[0]
        currentSessionId.value = next ? String(next.session_id) : null
        bindMessagesToSession(currentSessionId.value)
      }
      persistNow()
    } finally {
      loading.value = false
    }
  }

  async function sendQuestion(question) {
    if (!selectedKbId.value) return
    const text = (question || '').trim()
    if (!text) return

    abortCurrentStream()
    // 不要在每次发送时 hydrate：大历史 JSON.parse 会卡死整站主线程

    // 高频重复提问：命中本地 QA 缓存则直接渲染，不发网络请求
    try {
      const { buildCacheScope } = await import('@/utils/cacheLifecycle')
      const { loadQaCache, saveChatHistory } = await import('@/utils/indexedDbCache')
      const scope = buildCacheScope(selectedKbId.value)
      const cached = await loadQaCache(scope, text)
      if (cached?.answer) {
        const title = text.slice(0, 20) || '新会话'
        let sessionId = currentSessionId.value ? String(currentSessionId.value) : null
        if (!sessionId || !sessions.value.some((s) => String(s.session_id) === sessionId)) {
          sessionId = await ensureNewSession(title)
          currentSessionId.value = sessionId
          bindMessagesToSession(sessionId)
        } else {
          upsertSession(sessionId, title)
          bindMessagesToSession(sessionId)
        }
        const { escapeHtml } = await import('@/utils/inputFilter')
        messages.value.push(
          { id: msgId(), role: 'user', content: text, contentDisplay: escapeHtml(text) },
          {
            id: msgId(),
            role: 'assistant',
            content: cached.answer,
            sources: cached.sources || [],
            error: '',
            searchType: 'vector',
            retrievalMode: cached.retrievalMode || 'semantic',
            retrievalDegraded: !!cached.retrievalDegraded
          }
        )
        schedulePersist()
        streamStatus.value = '已命中本地缓存回答'
        setTimeout(() => {
          if (streamStatus.value === '已命中本地缓存回答') streamStatus.value = ''
        }, 1200)
        void saveChatHistory(scope, String(sessionId), messages.value)
        return
      }
    } catch {
      /* IndexedDB 不可用时继续走网络 */
    }

    const title = text.slice(0, 20) || '新会话'
    let sessionId = currentSessionId.value ? String(currentSessionId.value) : null

    // 无当前会话，或当前会话不属于列表时，才新建
    if (!sessionId || !sessions.value.some((s) => String(s.session_id) === sessionId)) {
      sessionId = await ensureNewSession(title)
      currentSessionId.value = sessionId
      bindMessagesToSession(sessionId)
    } else {
      upsertSession(sessionId, title)
      bindMessagesToSession(sessionId)
    }

    const { escapeHtml } = await import('@/utils/inputFilter')
    const requestedSearchType = 'vector'
    const userMsg = {
      id: msgId(),
      role: 'user',
      content: text,
      contentDisplay: escapeHtml(text)
    }
    const aiMessage = {
      id: msgId(),
      role: 'assistant',
      content: '',
      sources: [],
      error: '',
      searchType: requestedSearchType,
      retrievalMode: resolveRetrievalMode({ requested: requestedSearchType, degraded: false }),
      retrievalDegraded: false
    }
    messages.value.push(userMsg, aiMessage)
    if (MOCK_OPEN()) {
      mockMessagesBySession[String(sessionId)] = messages.value
    }
    schedulePersist()

    streaming.value = true
    sseController = createSSEController()

    // 流式 UI 节流：原始文本先进缓冲，定时刷到 Vue，避免每 token 强制整段重渲染卡死主线程
    let rawContent = ''
    const flushUi = () => {
      if (aiMessage.content !== rawContent) {
        aiMessage.content = rawContent
      }
    }
    const stopUiTimer = () => {
      clearStreamUiTimer()
      flushUi()
    }

    const payload = {
      kb_id: selectedKbId.value,
      query: text,
      search_type: requestedSearchType,
      top_n: 3,
      // 始终带上会话 id，后端才能加载多轮上下文（含 local-*）
      session_id: String(sessionId)
    }

    await streamChat(payload, {
      signal: sseController.signal,
      onStart: (event) => {
        streamStatus.value = '正在检索知识库...'
        if (event?.session_id) {
          const newId = String(event.session_id)
          const oldId = String(currentSessionId.value || sessionId)
          if (oldId !== newId) {
            remapSessionId(oldId, newId, title)
            sessionId = newId
          }
        }
      },
      onStatus: (event) => {
        const msg = event?.message ? String(event.message) : ''
        if (msg) streamStatus.value = msg
        else if (event?.stage === 'generate') streamStatus.value = '正在生成回答...'
        else if (event?.stage === 'retrieve') streamStatus.value = '正在检索知识库...'

        // 向量检索失败降级为关键词：写消息标识 + 供页面弹窗（只设一次）
        if (isDegradeStatusMessage(msg) && !aiMessage.retrievalDegraded) {
          aiMessage.retrievalDegraded = true
          aiMessage.retrievalMode = resolveRetrievalMode({
            requested: requestedSearchType,
            degraded: true
          })
          lastDegradeNotice.value = {
            at: Date.now(),
            message: msg,
            sessionId: String(currentSessionId.value || sessionId),
            docIds: []
          }
        }
      },
      onMessage: (event) => {
        if (!event.content) return
        rawContent += event.content
        if (streamStatus.value) streamStatus.value = ''
        // 首包立即上屏；之后 48ms 节流
        if (streamUiTimer == null) {
          flushUi()
          streamUiTimer = setInterval(flushUi, 48)
        }
      },
      onDone: (event) => {
        if (event?.aborted) {
          stopUiTimer()
          streaming.value = false
          streamStatus.value = ''
          sseController = null
          persistNow()
          return
        }
        stopUiTimer()
        if (event?.sources?.length) {
          aiMessage.sources = event.sources
          // 若后端将来回传 method，可补全降级态
          const allKeyword = event.sources.every((s) => {
            const m = String(s.method || '').toLowerCase()
            return m === 'bm25' || m === 'keyword'
          })
          if (allKeyword && event.sources.some((s) => s.method)) {
            aiMessage.retrievalDegraded = true
            aiMessage.retrievalMode = resolveRetrievalMode({
              requested: requestedSearchType,
              degraded: true
            })
          }
          if (aiMessage.retrievalDegraded && lastDegradeNotice.value) {
            // 原地补 docIds，避免重新赋值触发二次通知
            lastDegradeNotice.value.docIds = [
              ...new Set(
                event.sources.map((s) => s.doc_id).filter(Boolean).map(String)
              )
            ]
          }
        }
        if (event?.content) {
          rawContent += event.content
          aiMessage.content = rawContent
        }
        if (!aiMessage.content) {
          aiMessage.content =
            '当前知识库暂无相关内容，请更换问题或补充文档后重试。'
        }
        aiMessage.retrievalMode = resolveRetrievalMode({
          requested: requestedSearchType,
          degraded: !!aiMessage.retrievalDegraded
        })
        // 写入 QA 缓存与会话历史（userId + kbId 分区）
        void import('@/utils/cacheLifecycle')
          .then(async ({ buildCacheScope }) => {
            const { saveQaCache, saveChatHistory } = await import('@/utils/indexedDbCache')
            const scope = buildCacheScope(selectedKbId.value)
            await saveQaCache(scope, text, {
              question: text,
              answer: aiMessage.content,
              sources: aiMessage.sources || [],
              retrievalMode: aiMessage.retrievalMode,
              retrievalDegraded: !!aiMessage.retrievalDegraded
            })
            await saveChatHistory(scope, String(currentSessionId.value || sessionId), messages.value)
          })
          .catch(() => {})
        const row = sessions.value.find(
          (s) => String(s.session_id) === String(currentSessionId.value)
        )
        if (row) row.updated_at = new Date().toISOString()
        setSessions(sessions.value)
        streaming.value = false
        streamStatus.value = ''
        sseController = null
        persistNow()
      },
      onError: (error) => {
        stopUiTimer()
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
        streaming.value = false
        streamStatus.value = ''
        sseController = null
        persistNow()
      }
    })
    stopUiTimer()
  }

  function resetState() {
    abortCurrentStream()
    if (persistTimer) {
      clearTimeout(persistTimer)
      persistTimer = null
    }
    // 先落盘再清空内存，避免登出丢失未写入的对话
    try {
      persistNow()
    } catch {
      /* ignore */
    }
    sessions.value = []
    currentSessionId.value = null
    messages.value = []
    messageCache.value = {}
    streaming.value = false
    loading.value = false
    selectedKbId.value = null
    streamStatus.value = ''
    lastDegradeNotice.value = null
    kbWarming.value = false
    warmupGeneration += 1
    hydrated = false
  }

  async function warmupSelectedKb() {
    const kbId = selectedKbId.value
    if (!kbId) {
      kbWarming.value = false
      return
    }
    const gen = ++warmupGeneration
    kbWarming.value = true
    try {
      const res = await warmupChat(kbId)
      const data = res?.data || res || {}
      // 后端 accepted 即返回时，徽标再保留短暂窗口，避免闪一下就没
      if (
        gen === warmupGeneration &&
        (data.accepted || data.status === 'warming')
      ) {
        await new Promise((resolve) => setTimeout(resolve, 2200))
      }
    } catch {
      /* 预热失败不阻断对话 */
    } finally {
      if (gen === warmupGeneration) {
        kbWarming.value = false
      }
    }
  }

  return {
    sessions,
    currentSessionId,
    messages,
    streaming,
    loading,
    selectedKbId,
    streamStatus,
    lastDegradeNotice,
    kbWarming,
    loadSessions,
    createSession,
    switchSession,
    removeSession,
    togglePinSession,
    renameSession,
    sendQuestion,
    abortCurrentStream,
    resetState,
    hydrateFromLocal,
    persistNow,
    warmupSelectedKb,
    bindMessagesToSession
  }
})
