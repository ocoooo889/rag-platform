/**
 * 文档接口（前端 B）— if (MOCK_OPEN()) 双分支
 * Real:
 *   GET    /api/knowledge-bases/{kb_id}/documents
 *   POST   /api/knowledge-bases/{kb_id}/documents/upload
 *   DELETE /api/documents/{doc_id}
 * 枚举 status: pending | processing | completed | degraded | failed
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve, mockReject } from '@/mock/flag'
import { mockDocList, mockKbList, nextMockId } from '@/mock/data'
import { DOC_STATUS, normalizeDocStatus } from '@/utils/docStatus'

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

/** 对齐后端 doc_to_dict */
function normalizeDocRow(d = {}) {
  const created = d.created_at || d.uploaded_at || ''
  return {
    id: d.id,
    kb_id: d.kb_id,
    filename: d.filename || '',
    file_type: d.file_type || '',
    file_size: Number(d.file_size || 0),
    chunk_count: Number(d.chunk_count || 0),
    status: normalizeDocStatus(d.status),
    error_message: d.error_message || d.error || '',
    split_strategy: d.split_strategy || '',
    chunk_size: d.chunk_size ?? null,
    chunk_overlap: d.chunk_overlap ?? null,
    created_at: created,
    updated_at: d.updated_at || '',
    uploaded_at: d.uploaded_at || created
  }
}

function unwrapList(raw) {
  if (Array.isArray(raw)) return raw
  return raw?.items || raw?.list || []
}

/** 按知识库拉取文档列表 */
export async function fetchDocuments(params = {}) {
  if (MOCK_OPEN()) {
    const kbId = params.kb_id
    if (kbId && !mockKbList.some((k) => String(k.id) === String(kbId))) {
      return mockReject(404, '知识库不存在')
    }
    let list = mockDocList.map(normalizeDocRow)
    if (kbId) list = list.filter((d) => String(d.kb_id) === String(kbId))
    // 空库场景：kb002 若无文档则 items=[]
    return mockResolve(paginate(list, params.page, params.page_size))
  }

  const kbId = params.kb_id
  if (!kbId) {
    return Promise.reject({ code: 400, msg: '缺少 kb_id' })
  }
  const res = await request.get(`/api/knowledge-bases/${kbId}/documents`, {
    params: { page: params.page, page_size: params.page_size }
  })
  const mapped = unwrapList(res.data).map(normalizeDocRow)
  return {
    ...res,
    data: paginate(mapped, params.page, params.page_size)
  }
}

/**
 * 上传文档
 * @param {FormData} formData 含 kb_id + file + 可选切分参数
 * @param {Function} onUploadProgress Axios 进度回调
 */
export async function uploadDocument(formData, onUploadProgress) {
  if (MOCK_OPEN()) {
    const kbId = formData.get('kb_id')
    const file = formData.get('file')
    if (!kbId || !file) return mockReject(400, '缺少 kb_id 或 file')
    const name = file.name || '未命名.md'
    const lower = name.toLowerCase()
    const okExt = ['.md', '.markdown', '.txt', '.pdf', '.docx', '.html', '.htm', '.csv'].some(
      (ext) => lower.endsWith(ext)
    )
    if (!okExt) {
      return mockReject(400, '仅支持 .md / .txt / .pdf / .docx / .html / .csv')
    }
    if (typeof onUploadProgress === 'function') {
      onUploadProgress({ loaded: 50, total: 100 })
      onUploadProgress({ loaded: 100, total: 100 })
    }
    const id = nextMockId('doc')
    const now = new Date().toISOString()
    const ext = lower.includes('.') ? lower.split('.').pop() : 'md'
    const row = normalizeDocRow({
      id,
      kb_id: String(kbId),
      filename: name,
      file_type: ext === 'markdown' ? 'md' : ext,
      file_size: file.size || 1024,
      chunk_count: 0,
      status: DOC_STATUS.PENDING,
      split_strategy: formData.get('split_strategy') || 'recursive',
      chunk_size: Number(formData.get('chunk_size') || 500),
      chunk_overlap: Number(formData.get('chunk_overlap') || 50),
      created_at: now
    })
    mockDocList.unshift({ ...row })
    const kb = mockKbList.find((k) => String(k.id) === String(kbId))
    if (kb) {
      const n = (kb.document_count || kb.doc_count || 0) + 1
      kb.document_count = n
      kb.doc_count = n
    }
    // 兼容契约 { doc_id } 与后端全量 DocumentOut
    return mockResolve({ ...row, doc_id: id })
  }

  const kbId = formData.get('kb_id')
  if (!kbId) {
    return Promise.reject({ code: 400, msg: '缺少 kb_id' })
  }
  // 勿手动设置 Content-Type，否则缺少 boundary 会导致上传失败
  const res = await request.post(
    `/api/knowledge-bases/${kbId}/documents/upload`,
    formData,
    { onUploadProgress }
  )
  const row = normalizeDocRow(res.data || {})
  return { ...res, data: { ...row, doc_id: row.id } }
}

/** 切分策略列表 — 统一走 /api/split-strategies（见 api/splitStrategies.ts） */
export { fetchSplitStrategies, clearSplitStrategiesCache, labelOfStrategy } from '@/api/splitStrategies'

/** 删除单条文档 */
export async function deleteDocument(id) {
  if (MOCK_OPEN()) {
    const idx = mockDocList.findIndex((d) => String(d.id) === String(id))
    if (idx === -1) return mockReject(404, '文档不存在')
    const [removed] = mockDocList.splice(idx, 1)
    const kb = mockKbList.find((k) => String(k.id) === String(removed.kb_id))
    if (kb) {
      const n = Math.max(0, (kb.document_count || kb.doc_count || 0) - 1)
      kb.document_count = n
      kb.doc_count = n
    }
    return mockResolve(null)
  }
  return request.delete(`/api/documents/${id}`)
}

/** 批量删除文档 */
export async function batchDeleteDocuments(ids = []) {
  const list = (ids || []).map((id) => String(id)).filter(Boolean)
  if (!list.length) {
    return Promise.reject({ code: 400, msg: '请选择要删除的文档' })
  }
  if (MOCK_OPEN()) {
    let deleted = 0
    for (const id of list) {
      const idx = mockDocList.findIndex((d) => String(d.id) === String(id))
      if (idx === -1) continue
      const [removed] = mockDocList.splice(idx, 1)
      deleted += 1
      const kb = mockKbList.find((k) => String(k.id) === String(removed.kb_id))
      if (kb) {
        const n = Math.max(0, (kb.document_count || kb.doc_count || 0) - 1)
        kb.document_count = n
        kb.doc_count = n
      }
    }
    return mockResolve({ deleted })
  }
  return request.post('/api/documents/batch-delete', { ids: list })
}

/** 重新向量化 / 重新入库 */
export async function reprocessDocument(id) {
  if (MOCK_OPEN()) {
    const doc = mockDocList.find((d) => String(d.id) === String(id))
    if (!doc) return mockReject(404, '文档不存在')
    doc.status = DOC_STATUS.PENDING
    doc.error_message = ''
    doc.chunk_count = 0
    setTimeout(() => {
      doc.status = DOC_STATUS.PROCESSING
      doc.error_message = '向量化中 1/3'
    }, 400)
    setTimeout(() => {
      doc.error_message = '向量化中 2/3'
    }, 900)
    setTimeout(() => {
      doc.error_message = '向量化中 3/3'
    }, 1400)
    setTimeout(() => {
      doc.status = DOC_STATUS.COMPLETED
      doc.error_message = ''
      doc.chunk_count = 3
    }, 2000)
    return mockResolve(normalizeDocRow(doc))
  }
  return request.post(`/api/documents/${id}/reprocess`)
}
