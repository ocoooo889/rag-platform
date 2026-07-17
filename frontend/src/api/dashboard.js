import request from '@/utils/request'
import { isMockOpen, mockResolve } from '@/mock/flag'
import { MOCK_DASHBOARD_STATS } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const getStatsApi = async () => {
  if (isMockOpen()) {
    const data = unwrap(await mockResolve({ ...MOCK_DASHBOARD_STATS })) || {}
    return {
      kb_count: data.kb_count ?? 0,
      doc_count: data.doc_count ?? 0,
      chunk_count: data.chunk_count ?? 0,
      call_count: data.call_count ?? data.chat_count ?? null
    }
  }
  const res = await request.get('/api/dashboard/stats')
  const data = unwrap(res) || {}
  return {
    kb_count: data.kb_count ?? 0,
    doc_count: data.doc_count ?? 0,
    chunk_count: data.chunk_count ?? 0,
    call_count: data.call_count ?? data.chat_count ?? null
  }
}
