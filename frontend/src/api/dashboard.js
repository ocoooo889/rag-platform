/**
 * Dashboard 统计 — Mock / Real 双分支
 * Real fields: kb_count, doc_count, user_count, group_count
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve } from '@/mock/flag'
import { MOCK_DASHBOARD_STATS } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
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
    // 兼容旧 Dashboard UI（若仍展示）
    chunk_count: data.chunk_count ?? data.user_count ?? 0,
    call_count: data.call_count ?? data.group_count ?? data.chat_count ?? null
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
