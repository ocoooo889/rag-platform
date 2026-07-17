import request from '@/utils/request'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const getStatsApi = async () => {
  try {
    const res = await request.get('/api/dashboard/stats')
    const data = unwrap(res) || {}
    return {
      kb_count: data.kb_count ?? 0,
      doc_count: data.doc_count ?? 0,
      chunk_count: data.chunk_count ?? 0,
      call_count: data.call_count ?? data.chat_count ?? '--'
    }
  } catch (e) {
    return {
      kb_count: 0,
      doc_count: 0,
      chunk_count: 0,
      call_count: '--'
    }
  }
}
