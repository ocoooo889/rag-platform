/**
 * 命中率测试检索接口
 * POST /api/rag/test_retrieve — 契约字段 1:1；真实请求逻辑完整保留
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { matchMockScenario, mockScenarioReject } from '@/mock/scenarios'
import { MOCK_HITS_POOL, mockDocList } from '@/mock/data'
import { DOC_STATUS, normalizeDocStatus } from '@/utils/docStatus'

/**
 * @param {{ kb_id: string, doc_id: string, search_type: string, query: string, top_n: number }} data
 */
export async function testRetrieve(data) {
  const body = {
    kb_id: String(data.kb_id),
    doc_id: String(data.doc_id),
    search_type: data.search_type || data.mode || 'hybrid',
    query: data.query,
    top_n: data.top_n
  }

  if (isMockOpen()) {
    if (!body.kb_id || !body.doc_id || !(body.query || '').trim()) {
      return mockReject(400, '缺少必填参数')
    }
    const searchType = String(body.search_type || '').toLowerCase()
    if (!['vector', 'keyword', 'hybrid'].includes(searchType)) {
      return mockReject(400, 'search_type 必须是 vector / keyword / hybrid')
    }

    // 异常场景：超时 / 404 / 5001 / 空命中
    const scenario = matchMockScenario(body.query)
    if (scenario && scenario !== 'empty_hits' && scenario !== 'llm_error') {
      return mockScenarioReject(scenario)
    }

    const doc = mockDocList.find((d) => String(d.id) === body.doc_id)
    if (!doc || String(doc.kb_id) !== body.kb_id) {
      return mockReject(404, '文档不存在或不属于该知识库')
    }

    const status = normalizeDocStatus(doc.status)
    // 文档未就绪（含 failed 解析失败）→ 4002
    if (status !== DOC_STATUS.COMPLETED) {
      const tip =
        status === DOC_STATUS.FAILED
          ? `文档「${doc.filename}」处理失败，请等待处理完成后再试`
          : `文档「${doc.filename}」未就绪，请等待处理完成后再试`
      return mockReject(4002, tip, { doc_id: body.doc_id, status: doc.status })
    }

    const topN = Math.min(Math.max(Number(body.top_n) || 3, 1), 10)

    // 无命中：成功体但 hits 为空（对齐契约）
    if (scenario === 'empty_hits') {
      return mockResolve({
        search_type: searchType,
        total_hits: 0,
        hits: []
      })
    }

    let hits = MOCK_HITS_POOL.filter((h) => String(h.doc_id) === body.doc_id)
    hits = hits
      .map((h) => {
        let score = h.score
        if (searchType === 'keyword') score = score * 0.92
        if (searchType === 'vector') score = Math.min(0.99, score * 1.02)
        return { ...h, score: Number(score.toFixed(2)) }
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, topN)

    return mockResolve({
      search_type: searchType,
      total_hits: hits.length,
      hits
    })
  }

  // —— 真实后端请求（保留，勿删）——
  return request.post('/api/rag/test_retrieve', body)
}
