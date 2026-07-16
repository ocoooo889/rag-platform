/**
 * Mock 聚合入口
 * 由 vite-plugin-mock 在 vite 配置中引用（本模块不修改 vite.config）
 */
import kbMock from './kb.mock'
import docMock from './doc.mock'
import ragMock from './rag.mock'
import chatMock from './chat.mock'

export default [...kbMock, ...docMock, ...ragMock, ...chatMock]
