/**
 * Mock 开关（测试报告 LUO-D02）
 * 主开关：VITE_USE_MOCK=true 才开启；兼容历史变量 VITE_MOCK_OPEN
 * 默认关闭，避免误以为已联调真实后端
 */
export function isMockOpen() {
  const useMock = String(import.meta.env.VITE_USE_MOCK || '').toLowerCase() === 'true'
  const legacy = String(import.meta.env.VITE_MOCK_OPEN || '').toLowerCase() === 'true'
  return useMock || legacy
}

/** 统一成功体，对齐契约 { code, msg, data } */
export function mockOk(data, msg = 'success') {
  return { code: 0, msg, data }
}

/** 统一失败体 */
export function mockFail(code, msg, data = null) {
  return { code, msg, data }
}

export function mockDelay(ms = 280) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 模拟 axios 成功返回（与 request 拦截器成功形态一致）
 * 失败时 reject 业务体，便于页面 catch
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

/** 供 SSE Mock 抛出业务错误（同步形态，由调用方决定时机） */
export function mockFailSync(code, msg, data = null) {
  return mockFail(code, msg, data)
}
