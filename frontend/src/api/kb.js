/**
 * 知识库 CRUD 接口封装（对接后端 B：/api/knowledge-bases）
 * Token + env 由全局 axios 拦截器自动携带
 */
import request from '@/utils/request'

/** 获取知识库列表（分页） */
export function fetchKnowledgeBases(params = {}) {
  return request.get('/api/knowledge-bases', { params })
}

/** 新建知识库 */
export function createKnowledgeBase(data) {
  return request.post('/api/knowledge-bases', data)
}

/** 编辑知识库 */
export function updateKnowledgeBase(id, data) {
  return request.put(`/api/knowledge-bases/${id}`, data)
}

/** 删除知识库（级联文档与向量不可恢复） */
export function deleteKnowledgeBase(id) {
  return request.delete(`/api/knowledge-bases/${id}`)
}
