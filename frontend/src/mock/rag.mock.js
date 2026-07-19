/**
 * [LUO-A01/R3] 命中测试 Mock 数据结构 — 对齐后端 A 契约
 * 入参：doc_id / search_type / query / top_n
 * 出参：data.hits / data.total_hits / data.search_type
 * （已废弃 vite-plugin-mock 的 items/mode/doc_ids 形态）
 */
import { MOCK_HITS_POOL, mockDocList } from './data'
import { DOC_STATUS, normalizeDocStatus } from '@/utils/docStatus'

/**
 * 构建单文档检索 Mock 响应（与 POST /api/rag/test_retrieve 一致）
 */
export function buildRetrieveMockData({ doc_id, search_type = 'hybrid', query = '', top_n = 3 }) {
  const searchType = String(search_type || 'hybrid').toLowerCase()
  const topN = Math.min(Math.max(Number(top_n) || 3, 1), 10)

  if (/__empty__|无命中|无结果/.test(String(query || ''))) {
    return { search_type: searchType, total_hits: 0, hits: [] }
  }

  const doc = mockDocList.find((d) => String(d.id) === String(doc_id))
  const status = doc ? normalizeDocStatus(doc.status) : null
  if (!doc || (status !== DOC_STATUS.COMPLETED && status !== DOC_STATUS.DEGRADED)) {
    return null
  }
  if (status === DOC_STATUS.DEGRADED && searchType === 'vector') {
    return null
  }

  let hits = MOCK_HITS_POOL.filter((h) => String(h.doc_id) === String(doc_id))
  hits = hits
    .map((h) => {
      let score = h.score
      if (searchType === 'keyword') score = score * 0.92
      if (searchType === 'vector') score = Math.min(0.99, score * 1.02)
      const method =
        h.method ||
        (searchType === 'keyword' ? 'bm25' : searchType === 'hybrid' ? 'hybrid' : 'vector')
      return { ...h, score: Number(score.toFixed(2)), method }
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, topN)

  return {
    search_type: searchType,
    total_hits: hits.length,
    hits
  }
}

export { MOCK_HITS_POOL }
