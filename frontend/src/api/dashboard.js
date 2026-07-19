/**
 * Dashboard 统计 — 仅展示后端真实聚合字段
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve } from '@/mock/flag'
import { MOCK_DASHBOARD_STATS } from '@/mock/data'

function unwrap(res) {
  if (
    res &&
    typeof res === 'object' &&
    'data' in res &&
    ('code' in res || 'message' in res || 'msg' in res)
  ) {
    return res.data
  }
  return res
}

function normalizeStats(data = {}) {
  return {
    kb_count: data.kb_count ?? 0,
    doc_count: data.doc_count ?? 0,
    user_count: data.user_count ?? 0,
    group_count: data.group_count ?? 0,
    chunk_total: data.chunk_total ?? data.chunk_count ?? 0,
    avg_chunks_per_kb: data.avg_chunks_per_kb ?? 0,
    docs_by_status: data.docs_by_status || {},
    docs_by_file_type: data.docs_by_file_type || {},
    today_new_docs: data.today_new_docs ?? 0,
    failed_doc_count: data.failed_doc_count ?? 0,
    failed_docs: Array.isArray(data.failed_docs) ? data.failed_docs : [],
    question_count: data.question_count ?? data.call_count ?? 0,
    message_count: data.message_count ?? 0,
    session_count: data.session_count ?? 0,
    today_question_count: data.today_question_count ?? 0,
    avg_session_rounds: data.avg_session_rounds ?? 0,
    max_session_rounds: data.max_session_rounds ?? 0,
    call_count: data.call_count ?? data.question_count ?? 0,
    services: Array.isArray(data.services) ? data.services : [],
    alerts: Array.isArray(data.alerts) ? data.alerts : [],
    generated_at: data.generated_at || ''
  }
}

export const getStatsApi = async () => {
  if (isMockOpen()) {
    const data = unwrap(await mockResolve({ ...MOCK_DASHBOARD_STATS })) || {}
    return normalizeStats(data)
  }
  const res = await request.get('/api/dashboard/stats')
  const data = unwrap(res) || {}
  return normalizeStats(data)
}
