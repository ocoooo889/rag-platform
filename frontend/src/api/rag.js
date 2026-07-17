/**
 * 命中率测试检索接口
 * [LUO-A01/R3] 方案1：前端适配后端 A 契约
 *   入参：kb_id + 单个 doc_id + search_type + query + top_n
 *   出参：data.hits / data.total_hits（不再使用 doc_ids / mode / items）
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { matchMockScenario, mockScenarioReject } from '@/mock/scenarios'
import { buildRetrieveMockData } from '@/mock/rag.mock'
import { mockDocList } from '@/mock/data'
import { DOC_STATUS, normalizeDocStatus } from '@/utils/docStatus'

/**
 * 单文档检索（后端 A：POST /api/rag/test_retrieve）
 * 多文档由 store 循环调用本方法后合并 hits
 * @param {{ kb_id: string, doc_id: string, search_type: string, query: string, top_n: number }} data
 */
export async function testRetrieve(data) {
  // 契约字段强制归一：禁止再传 doc_ids / mode
  const body = {
    kb_id: String(data.kb_id),
    doc_id: String(data.doc_id),
    search_type: data.search_type || 'hybrid',
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

    const scenario = matchMockScenario(body.query)
    if (scenario && scenario !== 'empty_hits' && scenario !== 'llm_error') {
      return mockScenarioReject(scenario)
    }

    const doc = mockDocList.find((d) => String(d.id) === body.doc_id)
    if (!doc || String(doc.kb_id) !== body.kb_id) {
      return mockReject(404, '文档不存在或不属于该知识库')
    }

    const status = normalizeDocStatus(doc.status)
    if (status !== DOC_STATUS.COMPLETED) {
      const tip =
        status === DOC_STATUS.FAILED
          ? `文档「${doc.filename}」处理失败，请等待处理完成后再试`
          : `文档「${doc.filename}」未就绪，请等待处理完成后再试`
      return mockReject(4002, tip, { doc_id: body.doc_id, status: doc.status })
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

  // 真实后端 HTTP（保留完整请求，关 Mock 联调）
  return request.post('/api/rag/test_retrieve', body)
}
