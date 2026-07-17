/**
 * 知识库 CRUD（前端 B）— if (MOCK_OPEN()) 双分支
 * 契约对齐后端 B：
 *   GET/POST /api/knowledge-bases
 *   PUT/DELETE /api/knowledge-bases/{id}
 * data 字段：id, name, description, created_at, document_count
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve, mockReject } from '@/mock/flag'
import { mockKbList, mockDocList, nextMockId } from '@/mock/data'

function paginate(list, page = 1, pageSize = 10) {
  const p = Number(page) || 1
  const size = Number(pageSize) || 10
  const start = (p - 1) * size
  return {
    items: list.slice(start, start + size),
    total: list.length,
    page: p,
    page_size: size
  }
}

/** 对齐后端 kb_to_dict；doc_count 为 UI 兼容别名 */
function normalizeKbRow(row = {}) {
  const document_count = Number(row.document_count ?? row.doc_count ?? 0)
  return {
    id: row.id,
    name: row.name || '',
    description: row.description || '',
    created_at: row.created_at || '',
    document_count,
    doc_count: document_count,
    chunk_count: Number(row.chunk_count ?? 0)
  }
}

function unwrapList(raw) {
  if (Array.isArray(raw)) return raw
  return raw?.items || raw?.list || []
}

/** 获取知识库列表（统一返回 { items, total, page, page_size }） */
export async function fetchKnowledgeBases(params = {}) {
  if (MOCK_OPEN()) {
    // mockResolve 内置定时器延迟，模拟网络耗时
    return mockResolve(
      paginate(mockKbList.map(normalizeKbRow), params.page, params.page_size)
    )
  }

  // 真实：后端返回 data 为数组（无服务端分页）→ 前端归一 + 本地分页
  const res = await request.get('/api/knowledge-bases', { params })
  const mapped = unwrapList(res.data).map(normalizeKbRow)
  return {
    ...res,
    data: paginate(mapped, params.page, params.page_size)
  }
}

/** 新建知识库 */
export async function createKnowledgeBase(data) {
  if (MOCK_OPEN()) {
    if (!(data?.name || '').trim()) {
      return mockReject(400, '知识库名称不能为空')
    }
    const id = nextMockId('kb')
    const row = normalizeKbRow({
      id,
      name: data.name,
      description: data.description || '',
      document_count: 0,
      chunk_count: 0,
      created_at: new Date().toISOString()
    })
    mockKbList.unshift({ ...row })
    // 兼容契约文档 kb_id 与后端全量对象
    return mockResolve({ ...row, kb_id: id })
  }

  const res = await request.post('/api/knowledge-bases', data)
  const row = normalizeKbRow(res.data || {})
  return { ...res, data: { ...row, kb_id: row.id } }
}

/** 编辑知识库 */
export async function updateKnowledgeBase(id, data) {
  if (MOCK_OPEN()) {
    const row = mockKbList.find((k) => String(k.id) === String(id))
    if (!row) return mockReject(404, '知识库不存在')
    Object.assign(row, {
      name: data.name ?? row.name,
      description: data.description ?? row.description
    })
    return mockResolve(normalizeKbRow(row))
  }

  const res = await request.put(`/api/knowledge-bases/${id}`, data)
  return { ...res, data: normalizeKbRow(res.data || {}) }
}

/** 删除知识库 */
export async function deleteKnowledgeBase(id) {
  if (MOCK_OPEN()) {
    const idx = mockKbList.findIndex((k) => String(k.id) === String(id))
    if (idx === -1) return mockReject(404, '知识库不存在')
    mockKbList.splice(idx, 1)
    for (let i = mockDocList.length - 1; i >= 0; i -= 1) {
      if (String(mockDocList[i].kb_id) === String(id)) mockDocList.splice(i, 1)
    }
    return mockResolve(null)
  }
  return request.delete(`/api/knowledge-bases/${id}`)
}
