/**
 * 对话会话 Mock（vite-plugin-mock）
 * session_id 使用 UUID v4 字符串；消息列表模拟后端 10 轮截断结果
 */
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function resolveEnv(query = {}, body = {}) {
  return query.env || body.env || 'dev'
}

function ok(data) {
  return { code: 0, message: 'success', data }
}

/** sessions: { session_id, title, kb_id, updated_at } */
let sessionStore = []
/** messagesMap: session_id -> [{role, content, sources}] */
const messagesMap = {}

export default [
  {
    url: '/api/chat/sessions',
    method: 'get',
    response: ({ query }) => {
      const env = resolveEnv(query)
      return ok({
        items: sessionStore.map((item) => ({ ...item, env })),
        total: sessionStore.length,
        env
      })
    }
  },
  {
    url: '/api/chat/session',
    method: 'post',
    response: ({ body, query }) => {
      const env = resolveEnv(query, body)
      const sessionId = uuidv4()
      const item = {
        session_id: sessionId,
        title: body.title || '新会话',
        kb_id: body.kb_id || null,
        updated_at: new Date().toISOString(),
        env
      }
      sessionStore.unshift(item)
      messagesMap[sessionId] = []
      return ok(item)
    }
  },
  {
    url: /\/api\/chat\/[0-9a-fA-F-]{36}\/messages/,
    method: 'get',
    response: ({ query, url }) => {
      const env = resolveEnv(query)
      const parts = String(url).split('/')
      const sessionId = parts[parts.length - 2]
      // 模拟后端已截断：最多返回 20 条消息（10 轮）
      const list = (messagesMap[sessionId] || []).slice(-20)
      return ok({ items: list, env })
    }
  },
  {
    url: /\/api\/chat\/[0-9a-fA-F-]{36}$/,
    method: 'delete',
    response: ({ query, url }) => {
      const sessionId = String(url).split('/').pop()
      sessionStore = sessionStore.filter((item) => item.session_id !== sessionId)
      delete messagesMap[sessionId]
      return ok({ session_id: sessionId, env: resolveEnv(query) })
    }
  },
  {
    url: '/api/chat/stream',
    method: 'post',
    rawResponse: async (req, res) => {
      let raw = ''
      await new Promise((resolve) => {
        req.on('data', (chunk) => {
          raw += chunk
        })
        req.on('end', resolve)
      })
      let body = {}
      try {
        body = JSON.parse(raw || '{}')
      } catch (e) {
        body = {}
      }
      const sessionId = String(body.session_id || '')
      const question = body.question || ''

      if (!messagesMap[sessionId]) {
        messagesMap[sessionId] = []
      }
      messagesMap[sessionId].push({ role: 'user', content: question })

      const answer =
        '根据知识库内容：文档支持 md/txt 上传，命中测试可验证检索效果，对话采用流式输出。'
      const sources = [
        {
          chunk_id: 'c-001',
          content: '知识库支持上传 md、txt 文档，单文件不超过 10MB。',
          source_doc: '产品介绍.md',
          score: 0.91
        }
      ]

      res.writeHead(200, {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive'
      })

      // 模拟逐字流式输出
      for (const ch of answer) {
        res.write(`data: ${JSON.stringify({ content: ch, done: false })}\n\n`)
        await new Promise((r) => setTimeout(r, 15))
      }
      res.write(`data: ${JSON.stringify({ content: '', done: true, sources })}\n\n`)
      res.write('data: [DONE]\n\n')
      res.end()

      messagesMap[sessionId].push({
        role: 'assistant',
        content: answer,
        sources
      })
      // 模拟后端 10 轮截断（20 条消息）
      if (messagesMap[sessionId].length > 20) {
        messagesMap[sessionId] = messagesMap[sessionId].slice(-20)
      }
      const session = sessionStore.find((item) => item.session_id === sessionId)
      if (session) {
        session.updated_at = new Date().toISOString()
        session.title = question.slice(0, 20) || session.title
      }
    }
  }
]
