/**
 * 知识库 Mock（vite-plugin-mock）
 * 自动识别全局 env 参数，返回数据携带 env 字段供页面标签渲染
 */
const ENV_NAME_MAP = {
  dev: 'dev - 罗玥',
  test: 'test - 罗玥',
  prod: 'prod - 罗玥'
}

let kbStore = [
  {
    id: 1,
    name: '产品手册知识库',
    description: '标准产品说明与 FAQ',
    doc_count: 2,
    chunk_count: 18,
    env: 'dev'
  },
  {
    id: 2,
    name: '运维规范知识库',
    description: '值班与故障处理规范',
    doc_count: 1,
    chunk_count: 8,
    env: 'dev'
  }
]
let seq = 3

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
    url: '/api/knowledge-bases',
    method: 'get',
    response: ({ query }) => {
      const env = resolveEnv(query)
      const page = Number(query.page || 1)
      const pageSize = Number(query.page_size || 10)
      const items = kbStore.map((item) => withEnv(item, env))
      const start = (page - 1) * pageSize
      return ok({
        items: items.slice(start, start + pageSize),
        total: items.length,
        env
      })
    }
  },
  {
    url: '/api/knowledge-bases',
    method: 'post',
    response: ({ body, query }) => {
      const env = resolveEnv(query, body)
      const item = {
        id: seq++,
        name: body.name,
        description: body.description || '',
        doc_count: 0,
        chunk_count: 0,
        env
      }
      kbStore.unshift(item)
      return ok(withEnv(item, env))
    }
  },
  {
    url: /\/api\/knowledge-bases\/\d+/,
    method: 'put',
    response: ({ body, query, url }) => {
      const env = resolveEnv(query, body)
      const id = Number(String(url).split('/').pop())
      const target = kbStore.find((item) => item.id === id)
      if (!target) {
        return { code: 404, message: '知识库不存在', data: null }
      }
      target.name = body.name ?? target.name
      target.description = body.description ?? target.description
      return ok(withEnv(target, env))
    }
  },
  {
    url: /\/api\/knowledge-bases\/\d+/,
    method: 'delete',
    response: ({ query, url }) => {
      const id = Number(String(url).split('/').pop())
      kbStore = kbStore.filter((item) => item.id !== id)
      return ok({ id, env: resolveEnv(query) })
    }
  }
]
