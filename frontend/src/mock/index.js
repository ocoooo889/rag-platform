/**
 * Mock 模块入口（非 vite-plugin-mock）
 * 开关：VITE_MOCK_OPEN；数据：./data；异常场景：./scenarios
 */
export { isMockOpen, mockOk, mockFail, mockDelay, mockResolve, mockReject } from './flag'
export { matchMockScenario, mockTimeout, mockScenarioReject } from './scenarios'
export * from './data'
