/**
 * 文档 Mock（vite-plugin-mock）
 * 按 kb_id 隔离返回，携带 env 字段
 */
const ENV_NAME_MAP = {
  dev: 'dev - 罗玥',
  test: 'test - 罗玥',
  prod: 'prod - 罗玥'
}

let docStore = [
  {
    id: 101,
    kb_id: 1,
    file_name: '产品介绍.md',
    file_type: 'md',
    file_size: 24576,
    chunk_count: 10,
    status: 'completed',
    created_at: '2026-07-15T10:00:00',
    env: 'dev'
  },
  {
    id: 102,
    kb_id: 1,
    file_name: '常见问题.txt',
    file_type: 'txt',
    file_size: 8192,
    chunk_count: 8,
    status: 'completed',
    created_at: '2026-07-15T11:20:00',
    env: 'dev'
  },
  {
    id: 201,
    kb_id: 2,
    file_name: '值班手册.md',
    file_type: 'md',
    file_size: 16384,
    chunk_count: 8,
    status: 'processing',
    created_at: '2026-07-16T09:00:00',
    env: 'dev'
  }
]
let seq = 300

function resolveEnv(query = {}, body = {}) {
  return query.env || body.env || 'dev'
}

function withEnv(item, env) {
  return {
    ...item,
    env,
    env_label: ENV_NAME_MAP[env] || `${env} - 罗玥`
  }
}

function ok(data) {
  return { code: 0, message: 'success', data }
}

export default [
  {
    url: '/api/documents',
    method: 'get',
    response: ({ query }) => {
      const env = resolveEnv(query)
      const kbId = Number(query.kb_id)
      const page = Number(query.page || 1)
      const pageSize = Number(query.page_size || 10)
      // 跨库隔离：仅返回当前知识库文档
      const filtered = docStore
        .filter((item) => item.kb_id === kbId)
        .map((item) => withEnv(item, env))
      const start = (page - 1) * pageSize
      return ok({
        items: filtered.slice(start, start + pageSize),
        total: filtered.length,
        env
      })
    }
  },
  {
    url: '/api/documents/upload',
    method: 'post',
    rawResponse: async (req, res) => {
      // 兼容 multipart；Mock 侧模拟成功入库
      let body = ''
      await new Promise((resolve) => {
        req.on('data', (chunk) => {
          body += chunk
        })
        req.on('end', resolve)
      })
      const envMatch = String(req.url || '').match(/[?&]env=([^&]+)/)
      const env = envMatch ? decodeURIComponent(envMatch[1]) : 'dev'
      const kbMatch = body.match(/name="kb_id"\r?\n\r?\n([^\r\n]+)/)
      const nameMatch = body.match(/filename="([^"]+)"/)
      const kbId = Number(kbMatch?.[1] || 1)
      const fileName = nameMatch?.[1] || 'upload.md'
      const ext = fileName.includes('.') ? fileName.split('.').pop().toLowerCase() : 'md'
      const item = {
        id: seq++,
        kb_id: kbId,
        file_name: fileName,
        file_type: ext,
        file_size: body.length,
        chunk_count: 0,
        status: 'pending',
        created_at: new Date().toISOString(),
        env
      }
      docStore.unshift(item)
      res.setHeader('Content-Type', 'application/json')
      res.statusCode = 200
      res.end(JSON.stringify(ok(withEnv(item, env))))
    }
  },
  {
    url: /\/api\/documents\/\d+/,
    method: 'delete',
    response: ({ query, url }) => {
      const id = Number(String(url).split('/').pop())
      docStore = docStore.filter((item) => item.id !== id)
      return ok({ id, env: resolveEnv(query) })
    }
  }
]
