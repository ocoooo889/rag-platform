/**
 * 创建 SSE AbortController，统一管理流式连接生命周期
 * @returns {AbortController}
 */
export function createSSEController() {
  return new AbortController()
}

/**
 * 统一终止 fetch 流式请求
 * 仅中断当前 AI 打字流，不影响后端历史会话数据
 * @param {AbortController|null} controller
 */
export function closeSSE(controller) {
  if (controller && typeof controller.abort === 'function') {
    try {
      controller.abort()
    } catch (e) {
      // abort 幂等，忽略重复终止异常
    }
  }
}
