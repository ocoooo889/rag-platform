/**
 * Mock 异常场景触发器（仅 VITE_MOCK_OPEN=true）
 * 通过 query / 专用文档状态触发，字段与契约异常码一致
 *
 * | 触发词（写入测试问题） | 效果 |
 * | __empty__ / 无命中     | 检索成功但 hits=[] |
 * | __timeout__ / 超时     | 模拟接口超时 |
 * | __404__                | 资源不存在 |
 * | __5001__ / 向量异常    | 向量库异常 5001 |
 * | __5002__ / 大模型异常  | SSE/对话 5002 |
 */
import { mockDelay, mockFail } from '@/mock/flag'

export function matchMockScenario(query = '') {
  const q = String(query || '')
  if (/__timeout__|超时测试/.test(q)) return 'timeout'
  if (/__404__/.test(q)) return 'not_found'
  if (/__5001__|向量异常/.test(q)) return 'vector_error'
  if (/__5002__|大模型异常/.test(q)) return 'llm_error'
  if (/__empty__|无命中|无结果/.test(q)) return 'empty_hits'
  return null
}

/** 模拟超时（不走正常业务码路径，贴近网络超时） */
export async function mockTimeout(ms = 3200) {
  await mockDelay(ms)
  const err = new Error('timeout of 3000ms exceeded')
  err.code = 'ECONNABORTED'
  err.message = 'timeout of 3000ms exceeded'
  return Promise.reject(err)
}

export async function mockScenarioReject(scenario) {
  if (scenario === 'timeout') return mockTimeout()
  if (scenario === 'not_found') {
    await mockDelay(200)
    return Promise.reject(mockFail(404, '资源不存在'))
  }
  if (scenario === 'vector_error') {
    await mockDelay(200)
    return Promise.reject(mockFail(5001, '向量库服务异常: mock chroma down'))
  }
  if (scenario === 'llm_error') {
    await mockDelay(200)
    return Promise.reject(mockFail(5002, '大模型服务暂时不可用'))
  }
  return null
}
