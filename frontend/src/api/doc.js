/**
 * 文档接口封装（对接后端 B）
 * 仅支持 md/txt 上传，列表按知识库隔离
 */
import request from '@/utils/request'

/** 按知识库拉取文档列表 */
export function fetchDocuments(params = {}) {
  return request.get('/api/documents', { params })
}

/**
 * 上传文档
 * @param {FormData} formData 含 kb_id + file
 * @param {Function} onUploadProgress Axios 进度回调
 */
export function uploadDocument(formData, onUploadProgress) {
  return request.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

/** 删除单条文档 */
export function deleteDocument(id) {
  return request.delete(`/api/documents/${id}`)
}
