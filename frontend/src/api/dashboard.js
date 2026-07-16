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
    return (
      unwrap(res) || {
        kb_count: 0,
        doc_count: 0,
        chunk_count: 0,
        call_count: '--'
      }
    )
  } catch (e) {
    return {
      kb_count: 0,
      doc_count: 0,
      chunk_count: 0,
      call_count: '--'
    }
  }
}
