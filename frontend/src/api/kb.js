/**
 * 知识库 CRUD — Mock / Real 双分支
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
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

/** 获取知识库列表（分页） */
export async function fetchKnowledgeBases(params = {}) {
  if (isMockOpen()) {
    return mockResolve(paginate(mockKbList, params.page, params.page_size))
  }
  return request.get('/api/knowledge-bases', { params })
}

/** 新建知识库 */
export async function createKnowledgeBase(data) {
  if (isMockOpen()) {
    if (!(data?.name || '').trim()) {
      return mockReject(400, '知识库名称不能为空')
    }
    const id = nextMockId('kb')
    mockKbList.unshift({
      id,
      name: data.name,
      description: data.description || '',
      doc_count: 0,
      chunk_count: 0,
      created_at: new Date().toISOString()
    })
    return mockResolve({ kb_id: id })
  }
  return request.post('/api/knowledge-bases', data)
}

/** 编辑知识库 */
export async function updateKnowledgeBase(id, data) {
  if (isMockOpen()) {
    const row = mockKbList.find((k) => String(k.id) === String(id))
    if (!row) return mockReject(404, '知识库不存在')
    Object.assign(row, {
      name: data.name ?? row.name,
      description: data.description ?? row.description
    })
    return mockResolve({ kb_id: row.id })
  }
  return request.put(`/api/knowledge-bases/${id}`, data)
}

/** 删除知识库 */
export async function deleteKnowledgeBase(id) {
  if (isMockOpen()) {
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
