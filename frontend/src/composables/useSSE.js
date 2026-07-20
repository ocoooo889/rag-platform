/**
 * 通用 SSE 流式钩子（与页面业务解耦）
 *
 * - Mock：定时器分段推送（可由 options.mock 注入文案/异常）
 * - Real：POST → fetch ReadableStream；GET+preferEventSource → EventSource
 *
 * 页面 / store 只依赖 onStart / onMessage / onDone / onError，不感知分支
 */
import { MOCK_OPEN, isMockOpen } from '@/mock/flag'
import { createSSEController, closeSSE } from '@/utils/sse'

export function splitStreamChunks(text, size = 2) {
  const src = String(text || '')
  const chunks = []
  for (let i = 0; i < src.length; i += size) {
    chunks.push(src.slice(i, i + size))
  }
  return chunks.length ? chunks : ['']
}

function runMockSSE(options = {}) {
  const {
    payload = {},
    handlers = {},
    signal,
    answerText = '',
    references = [],
    intervalMs = 45,
    chunkSize = 2,
    /** 模拟异常：timeout | llm_error | 自定义 { code, msg } */
    errorScenario = null,
    sessionIdFactory = () => `s${Date.now()}`,
    requestIdFactory = () => `req${Date.now()}`
  } = options

  const { onStart, onMessage, onDone, onError } = handlers
  let timer = null
  let finished = false

  const cleanup = () => {
    if (timer != null) {
      clearInterval(timer)
      timer = null
    }
  }

  const abortHandler = () => {
    cleanup()
    finished = true
  }

  if (signal) {
    if (signal.aborted) {
      abortHandler()
      return { abort: abortHandler }
    }
    signal.addEventListener('abort', abortHandler, { once: true })
  }

  // 异常场景：不推 chunk，直接 onError
  if (errorScenario === 'timeout') {
    timer = setTimeout(() => {
      if (finished) return
      finished = true
      const err = new Error('timeout of 3000ms exceeded')
      err.code = 'ECONNABORTED'
      onError && onError(err)
    }, 3200)
    return { abort: abortHandler }
  }

  if (errorScenario === 'llm_error' || (errorScenario && errorScenario.code)) {
    const errBody =
      errorScenario === 'llm_error'
        ? { code: 5002, msg: '大模型服务暂时不可用', message: '大模型服务暂时不可用' }
        : errorScenario
    timer = setTimeout(() => {
      if (finished) return
      finished = true
      onError && onError(errBody)
    }, 280)
    return { abort: abortHandler }
  }

  const sessionId = payload.session_id || sessionIdFactory()
  const requestId = requestIdFactory()
  const pieces = splitStreamChunks(answerText, chunkSize)
  let idx = 0
  const query = String(payload.query || payload.question || '')
  const simulateDegrade = /__degrade__/i.test(query)

  try {
    onStart && onStart({ type: 'start', session_id: sessionId, request_id: requestId })
  } catch (e) {
    onError && onError(e)
    return { abort: abortHandler }
  }

  // 模拟向量→关键词降级 status（测试：问题含 __degrade__）
  if (simulateDegrade && handlers.onStatus) {
    try {
      handlers.onStatus({
        type: 'status',
        stage: 'retrieve',
        message: '向量检索加载中，已启用关键词检索兜底'
      })
    } catch {
      /* ignore */
    }
  }

  timer = setInterval(() => {
    if (finished || signal?.aborted) {
      cleanup()
      return
    }
    if (idx < pieces.length) {
      const content = pieces[idx]
      idx += 1
      onMessage && onMessage({ type: 'chunk', content })
      return
    }
    cleanup()
    finished = true
    const refs = (references || []).map((r) =>
      simulateDegrade
        ? { ...r, method: r.method || 'bm25', retrieve_fallback: 'bm25' }
        : r
    )
    const sources = refs.map((r) => ({
      chunk_id: r.chunk_id,
      content: r.content,
      score: r.score,
      source_doc: r.source_doc || '',
      doc_id: r.doc_id || '',
      method: r.method || r.retrieve_fallback || ''
    }))
    onDone &&
      onDone({
        type: 'done',
        content: '',
        references: refs,
        sources
      })
  }, intervalMs)

  return { abort: abortHandler }
}

async function runFetchSSE(options = {}) {
  const { url, method = 'POST', body, headers = {}, handlers = {}, signal } = options
  const { onStart, onMessage, onDone, onError } = handlers

  const response = await fetch(url, {
    method,
    headers: {
      Accept: 'text/event-stream',
      'Cache-Control': 'no-cache',
      ...headers
    },
    body: method.toUpperCase() === 'GET' ? undefined : body,
    signal,
    cache: 'no-store'
  })

  if (!response.ok) {
    let errBody = null
    try {
      errBody = await response.json()
    } catch (e) {
      // ignore
    }
    onError && onError(errBody || { code: response.status, message: '流式请求失败' })
    return
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json') && !contentType.includes('text/event-stream')) {
    const errBody = await response.json()
    if (errBody?.code && errBody.code !== 0) {
      onError && onError(errBody)
      return
    }
  }

  if (!response.body) {
    onError && onError({ code: 500, message: '响应无可读流' })
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finished = false

  const pushContent = (text) => {
    if (!text) return
    onMessage && onMessage({ type: 'chunk', content: text })
  }

  const finish = (event) => {
    if (finished) return
    finished = true
    onDone && onDone(event || { type: 'done' })
  }

  // MessageChannel 让出主线程：一批 SSE 解析时仍能响应侧栏点击/切页
  let scheduleYield = (cb) => setTimeout(cb, 0)
  try {
    const ch = new MessageChannel()
    let pending = null
    ch.port1.onmessage = () => {
      const fn = pending
      pending = null
      if (fn) fn()
    }
    scheduleYield = (cb) => {
      pending = cb
      ch.port2.postMessage(0)
    }
  } catch {
    /* keep setTimeout fallback */
  }

  const yieldToMain = () => new Promise((resolve) => scheduleYield(resolve))

  const handleDataLine = (raw) => {
    if (!raw || raw === '[DONE]') {
      finish()
      return
    }
    try {
      const event = JSON.parse(raw)
      if (event.type === 'start') onStart && onStart(event)
      else if (event.type === 'status') handlers.onStatus && handlers.onStatus(event)
      else if (event.type === 'chunk') pushContent(event.content || '')
      else if (event.type === 'done' || event.done === true) {
        const sources = (event.references || event.sources || []).map((r) => ({
          chunk_id: r.chunk_id,
          content: r.content,
          score: r.score,
          source_doc: r.source_doc || '',
          method: r.method || r.retrieve_fallback || ''
        }))
        finish({ ...event, sources })
      } else if (event.content && !event.type) {
        pushContent(event.content)
      }
    } catch (e) {
      // 非 JSON 的 data 行忽略
    }
  }

  let eventsSinceYield = 0
  while (true) {
    if (signal?.aborted) break
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    buffer = buffer.replace(/\r\n/g, '\n')
    let sep
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      if (signal?.aborted) {
        finished = true
        break
      }
      const part = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      for (const line of part.split('\n')) {
        if (!line.startsWith('data:')) continue
        const raw = line.startsWith('data: ') ? line.slice(6) : line.slice(5).trimStart()
        handleDataLine(raw)
        eventsSinceYield += 1
        if (eventsSinceYield >= 2) {
          eventsSinceYield = 0
          await yieldToMain()
        }
      }
    }
    if (signal?.aborted) break
  }

  if (!signal?.aborted && buffer.trim()) {
    for (const line of buffer.replace(/\r\n/g, '\n').split('\n')) {
      if (!line.startsWith('data:')) continue
      const raw = line.startsWith('data: ') ? line.slice(6) : line.slice(5).trimStart()
      handleDataLine(raw)
    }
  }
  if (signal?.aborted) {
    if (!finished) {
      finished = true
      onDone && onDone({ type: 'done', aborted: true })
    }
  } else {
    finish()
  }
}

function runEventSourceSSE(options = {}) {
  const { url, handlers = {}, signal } = options
  const { onStart, onMessage, onDone, onError } = handlers

  if (typeof EventSource === 'undefined') {
    onError && onError({ code: 500, message: '当前环境不支持 EventSource' })
    return { abort: () => {} }
  }

  const es = new EventSource(url)
  let finished = false
  const abort = () => {
    finished = true
    es.close()
  }

  if (signal) {
    if (signal.aborted) {
      abort()
      return { abort }
    }
    signal.addEventListener('abort', abort, { once: true })
  }

  es.onmessage = (evt) => {
    if (finished) return
    const raw = (evt.data || '').trim()
    if (!raw || raw === '[DONE]') {
      abort()
      onDone && onDone({ type: 'done' })
      return
    }
    try {
      const event = JSON.parse(raw)
      if (event.type === 'start') onStart && onStart(event)
      else if (event.type === 'chunk') onMessage && onMessage({ content: event.content || '', ...event })
      else if (event.type === 'done') {
        const sources = (event.references || event.sources || []).map((r) => ({
          chunk_id: r.chunk_id,
          content: r.content,
          score: r.score,
          source_doc: r.source_doc || '',
          method: r.method || r.retrieve_fallback || ''
        }))
        abort()
        onDone && onDone({ ...event, sources })
      } else if (event.content) onMessage && onMessage(event)
    } catch (e) {
      onMessage && onMessage({ content: raw })
    }
  }

  es.onerror = () => {
    if (finished) return
    abort()
    onError && onError({ code: 500, message: 'EventSource 连接异常' })
  }

  return { abort }
}

/**
 * 统一入口
 * @param {object} options.mock 仅 Mock 使用：{ answerText, references, errorScenario, intervalMs }
 */
export async function runSSE(options = {}) {
  const {
    payload = {},
    url,
    method = 'POST',
    headers = {},
    body,
    signal,
    handlers = {},
    mock = {},
    preferEventSource = false
  } = options

  const controller = signal ? null : createSSEController()
  const activeSignal = signal || controller.signal

  try {
    if (MOCK_OPEN()) {
      runMockSSE({
        payload,
        handlers,
        signal: activeSignal,
        ...mock
      })
      return controller
    }

    const upper = String(method || 'POST').toUpperCase()
    if (upper === 'GET' && preferEventSource) {
      runEventSourceSSE({ url, handlers, signal: activeSignal })
      return controller
    }

    await runFetchSSE({
      url,
      method: upper,
      body: typeof body === 'string' ? body : JSON.stringify(body || {}),
      headers,
      handlers,
      signal: activeSignal
    })
  } catch (error) {
    if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') {
      handlers.onDone && handlers.onDone({ content: '', type: 'done', aborted: true })
      return controller
    }
    handlers.onError && handlers.onError(error)
  }

  return controller
}

/** Vue 组合式：仅管理 abort / streaming 标记，不含业务文案 */
export function useSSE() {
  let controller = null
  const state = { streaming: false }

  function abort() {
    closeSSE(controller)
    controller = null
    state.streaming = false
  }

  async function start(options = {}) {
    abort()
    state.streaming = true
    controller = await runSSE({
      ...options,
      handlers: {
        ...options.handlers,
        onDone: (evt) => {
          state.streaming = false
          controller = null
          options.handlers?.onDone && options.handlers.onDone(evt)
        },
        onError: (err) => {
          state.streaming = false
          controller = null
          options.handlers?.onError && options.handlers.onError(err)
        }
      }
    })
    return controller
  }

  return { state, start, abort, isMockOpen: MOCK_OPEN, MOCK_OPEN }
}

export { createSSEController, closeSSE, isMockOpen, MOCK_OPEN }
