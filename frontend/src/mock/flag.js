/**
 * Mock 开关（前端 B 双分支）
 * 环境变量：VITE_USE_MOCK=true 开启（兼容旧名 VITE_MOCK_OPEN）
 * 对外统一使用 MOCK_OPEN()；isMockOpen 为同义别名
 */
export function isMockOpen() {
  const useMock = String(import.meta.env.VITE_USE_MOCK || '').toLowerCase() === 'true'
  const legacy = String(import.meta.env.VITE_MOCK_OPEN || '').toLowerCase() === 'true'
  return useMock || legacy
}

/** 任务约定命名：if (MOCK_OPEN()) { ... } else { 真实 HTTP/SSE } */
export const MOCK_OPEN = isMockOpen

/** 统一成功体，对齐契约 { code, msg, data } */
export function mockOk(data, msg = 'success') {
  return { code: 0, msg, data }
}

/** 统一失败体 */
export function mockFail(code, msg, data = null) {
  return { code, msg, data }
}

/** 模拟网络延迟（默认 280ms） */
export function mockDelay(ms = 280) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 模拟 axios 成功返回（与 request 拦截器成功形态一致）
 */
export async function mockResolve(data, options = {}) {
  const { delay = 280, msg = 'success' } = options
  await mockDelay(delay)
  return mockOk(data, msg)
}

export async function mockReject(code, msg, data = null, delay = 200) {
  await mockDelay(delay)
  return Promise.reject(mockFail(code, msg, data))
}

/** 供 SSE Mock 抛出业务错误 */
export function mockFailSync(code, msg, data = null) {
  return mockFail(code, msg, data)
}
