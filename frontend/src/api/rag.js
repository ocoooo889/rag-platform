/**
 * 命中率测试（前端 B）— if (MOCK_OPEN()) 双分支
 * 后端 A：POST /api/rag/test_retrieve
 * 入参：kb_id, doc_id, search_type(vector|keyword|hybrid), query, top_n
 * 出参：search_type, total_hits, hits[{ chunk_id, content, score, source_doc, doc_id, method }]
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve, mockReject } from '@/mock/flag'
import { matchMockScenario, mockScenarioReject } from '@/mock/scenarios'
import { buildRetrieveMockData } from '@/mock/rag.mock'
import { mockDocList } from '@/mock/data'
import { DOC_STATUS, normalizeDocStatus } from '@/utils/docStatus'

/**
 * 单文档检索；多文档由 hitTest store 限流循环调用
 */
export async function testRetrieve(data) {
  const body = {
    kb_id: String(data.kb_id),
    doc_id: String(data.doc_id),
    search_type: data.search_type || 'hybrid',
    query: data.query,
    top_n: data.top_n
  }

  if (MOCK_OPEN()) {
    if (!body.kb_id || !body.doc_id || !(body.query || '').trim()) {
      return mockReject(400, '缺少必填参数')
    }
    const searchType = String(body.search_type || '').toLowerCase()
    if (!['vector', 'keyword', 'hybrid'].includes(searchType)) {
      return mockReject(400, 'search_type 必须是 vector / keyword / hybrid')
    }

    const scenario = matchMockScenario(body.query)
    if (scenario && scenario !== 'empty_hits' && scenario !== 'llm_error') {
      return mockScenarioReject(scenario)
    }

    const doc = mockDocList.find((d) => String(d.id) === body.doc_id)
    if (!doc || String(doc.kb_id) !== body.kb_id) {
      return mockReject(404, '文档不存在或不属于该知识库')
    }

    const status = normalizeDocStatus(doc.status)
    if (status !== DOC_STATUS.COMPLETED && status !== DOC_STATUS.DEGRADED) {
      const tip =
        status === DOC_STATUS.FAILED
          ? `文档「${doc.filename}」处理失败，请等待处理完成后再试`
          : `文档「${doc.filename}」未就绪，请等待处理完成后再试`
      return mockReject(4002, tip, { doc_id: body.doc_id, status: doc.status })
    }
    if (status === DOC_STATUS.DEGRADED && searchType === 'vector') {
      return mockReject(
        4004,
        `文档「${doc.filename}」仅关键词可用，请改用关键词或混合检索`,
        { doc_id: body.doc_id, status: doc.status }
      )
    }

    const mockData = buildRetrieveMockData({
      doc_id: body.doc_id,
      search_type: searchType,
      query: body.query,
      top_n: body.top_n
    })
    return mockResolve(
      mockData || { search_type: searchType, total_hits: 0, hits: [] }
    )
  }

  // 真实后端 HTTP
  return request.post('/api/rag/test_retrieve', body)
}
