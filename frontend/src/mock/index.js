/**
 * Mock 模块入口（应用层双分支，非 vite-plugin-mock）
 * 开关：VITE_USE_MOCK（兼容 VITE_MOCK_OPEN）
 */
export { isMockOpen, mockOk, mockFail, mockDelay, mockResolve, mockReject } from './flag'
export { matchMockScenario, mockTimeout, mockScenarioReject } from './scenarios'
export { buildRetrieveMockData } from './rag.mock'
export * from './data'
