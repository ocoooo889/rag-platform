/**
 * 文档接口 — Mock / Real 双分支
 * Mock 仅返回契约字段：id/kb_id/filename/file_type/file_size/chunk_count/status/uploaded_at
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { mockDocList, mockKbList, nextMockId } from '@/mock/data'
import { DOC_STATUS } from '@/utils/docStatus'

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

/** 按知识库拉取文档列表 */
export async function fetchDocuments(params = {}) {
  if (isMockOpen()) {
    const kbId = params.kb_id
    let list = mockDocList.map((d) => ({
      id: d.id,
      kb_id: d.kb_id,
      filename: d.filename,
      file_type: d.file_type,
      file_size: d.file_size,
      chunk_count: d.chunk_count,
      status: d.status,
      uploaded_at: d.uploaded_at
    }))
    if (kbId) list = list.filter((d) => String(d.kb_id) === String(kbId))
    // 模拟知识库不存在
    if (kbId && !mockKbList.some((k) => String(k.id) === String(kbId))) {
      return mockReject(404, '知识库不存在')
    }
    return mockResolve(paginate(list, params.page, params.page_size))
  }
  // —— 真实后端请求（保留）——
  if (params.kb_id) {
    try {
      return await request.get(`/api/knowledge-bases/${params.kb_id}/documents`, {
        params: { page: params.page, page_size: params.page_size }
      })
    } catch (e) {
      return request.get('/api/documents', { params })
    }
  }
  return request.get('/api/documents', { params })
}

/**
 * 上传文档
 * @param {FormData} formData 含 kb_id + file
 * @param {Function} onUploadProgress Axios 进度回调
 */
export async function uploadDocument(formData, onUploadProgress) {
  if (isMockOpen()) {
    const kbId = formData.get('kb_id')
    const file = formData.get('file')
    if (!kbId || !file) return mockReject(400, '缺少 kb_id 或 file')
    const name = file.name || '未命名.md'
    const lower = name.toLowerCase()
    if (!lower.endsWith('.md') && !lower.endsWith('.txt')) {
      return mockReject(400, '仅支持 .md / .txt')
    }
    if (typeof onUploadProgress === 'function') {
      onUploadProgress({ loaded: 50, total: 100 })
      onUploadProgress({ loaded: 100, total: 100 })
    }
    const id = nextMockId('doc')
    const row = {
      id,
      kb_id: String(kbId),
      filename: name,
      file_type: lower.endsWith('.txt') ? 'txt' : 'md',
      file_size: file.size || 1024,
      chunk_count: 0,
      status: DOC_STATUS.PENDING,
      uploaded_at: new Date().toISOString()
    }
    mockDocList.unshift(row)
    const kb = mockKbList.find((k) => String(k.id) === String(kbId))
    if (kb) kb.doc_count = (kb.doc_count || 0) + 1
    return mockResolve({
      doc_id: id,
      filename: name,
      status: DOC_STATUS.PENDING
    })
  }
  // —— 真实后端请求（保留）——
  return request.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

/** 删除单条文档 */
export async function deleteDocument(id, kbId) {
  if (isMockOpen()) {
    const idx = mockDocList.findIndex((d) => String(d.id) === String(id))
    if (idx === -1) return mockReject(404, '文档不存在')
    const [removed] = mockDocList.splice(idx, 1)
    const kb = mockKbList.find((k) => String(k.id) === String(removed.kb_id))
    if (kb && kb.doc_count > 0) kb.doc_count -= 1
    return mockResolve(null)
  }
  // —— 真实后端请求（保留）；优先契约路径 ——
  if (kbId) {
    try {
      return await request.delete(`/api/knowledge-bases/${kbId}/documents/${id}`)
    } catch (e) {
      return request.delete(`/api/documents/${id}`)
    }
  }
  return request.delete(`/api/documents/${id}`)
}
