/**
 * 命中率测试检索接口（对接后端 A）
 * CSV 导出为纯前端能力，无后端依赖
 */
import request from '@/utils/request'

/**
 * 执行检索测试
 * @param {{ kb_id: string|number, doc_ids: Array, query: string, mode: string, top_n: number }} data
 */
export function testRetrieve(data) {
  return request.post('/api/rag/test_retrieve', data)
}
