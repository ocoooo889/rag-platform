/**
 * 命中率测试 Mock
 * 三种检索模式返回差异化排序结果，便于前端展示对比
 */
function resolveEnv(query = {}, body = {}) {
  return query.env || body.env || 'dev'
}

function ok(data) {
  return { code: 0, message: 'success', data }
}

/** 基础分片池 */
const CHUNK_POOL = [
  {
    chunk_id: 'c-001',
    content: '知识库支持上传 md、txt 文档，单文件不超过 10MB，后端固定 chunk_size=500。',
    source_doc: '产品介绍.md',
    score: 0.92
  },
  {
    chunk_id: 'c-002',
    content: '命中率测试支持向量、关键词、混合三种检索模式，默认混合检索。',
    source_doc: '产品介绍.md',
    score: 0.81
  },
  {
    chunk_id: 'c-003',
    content: '智能对话采用 SSE 流式输出，切换会话或离开页面需 Abort 中断连接。',
    source_doc: '常见问题.txt',
    score: 0.66
  },
  {
    chunk_id: 'c-004',
    content: '文档状态包含 pending、processing、completed、failed 四种。',
    source_doc: '常见问题.txt',
    score: 0.48
  },
  {
    chunk_id: 'c-005',
    content: '无可用知识库时，下游上传、命中测试、新建会话入口自动隐藏或置灰。',
    source_doc: '值班手册.md',
    score: 0.35
  }
]

/**
 * 按模式差异化排序：
 * - vector：按 score 降序
 * - keyword：按关键词命中偏好重排（模拟）
 * - hybrid：综合分微调后排序
 */
function sortByMode(mode, list, query) {
  const q = (query || '').trim()
  const cloned = list.map((item) => ({ ...item }))
  if (mode === 'keyword') {
    return cloned
      .map((item) => ({
        ...item,
        score: q && item.content.includes(q.slice(0, 2)) ? Math.min(0.99, item.score + 0.08) : item.score * 0.9
      }))
      .sort((a, b) => b.score - a.score)
  }
  if (mode === 'hybrid') {
    return cloned
      .map((item, index) => ({
        ...item,
        score: Math.min(0.99, item.score * 0.7 + (1 - index * 0.05) * 0.3)
      }))
      .sort((a, b) => b.score - a.score)
  }
  // vector 默认按原相似度降序
  return cloned.sort((a, b) => b.score - a.score)
}

export default [
  {
    url: '/api/rag/test_retrieve',
    method: 'post',
    response: ({ body, query }) => {
      const env = resolveEnv(query, body)
      const mode = body.mode || 'hybrid'
      const topN = Number(body.top_n || 3)
      const queryText = body.query || ''

      // 空输入 / 未选文档由前端拦截；此处兜底返回空
      if (!queryText.trim() || !body.doc_ids || !body.doc_ids.length) {
        return ok({ items: [], env, mode })
      }

      const sorted = sortByMode(mode, CHUNK_POOL, queryText).slice(0, topN)
      const items = sorted.map((item, index) => ({
        rank: index + 1,
        score: Number(item.score.toFixed(4)),
        content: item.content,
        source_doc: item.source_doc,
        chunk_id: item.chunk_id,
        env
      }))
      return ok({ items, env, mode })
    }
  }
]
