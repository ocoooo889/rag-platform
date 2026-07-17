/**
 * Mock 双分支冒烟：在 Vite 环境下跑通关键 API（正常 / 空数据 / 延迟）
 * 用法：在 frontend 目录执行
 *   npx --yes vite-node scripts/smoke-mock.js
 */
import { isMockOpen } from '../src/mock/flag.js'
import { fetchKnowledgeBases, createKnowledgeBase } from '../src/api/kb.js'
import { fetchDocuments } from '../src/api/doc.js'
import { testRetrieve } from '../src/api/rag.js'
import { loginApi } from '../src/api/auth.js'
import { getStatsApi } from '../src/api/dashboard.js'
import { streamChat } from '../src/api/chat.js'

function assert(cond, msg) {
  if (!cond) throw new Error(msg)
}

async function main() {
  console.log('[smoke] VITE_USE_MOCK/isMockOpen =>', isMockOpen())
  assert(isMockOpen() === true, '请确保 .env.development 中 VITE_USE_MOCK=true')

  // 1) 登录
  const login = await loginApi({ username: 'admin', password: 'admin123' })
  assert(login.token && login.user?.username === 'admin', 'login 失败')
  console.log('[ok] login', login.user.username)

  // 2) 知识库列表（有数据）
  const kbRes = await fetchKnowledgeBases({ page: 1, page_size: 10 })
  assert(kbRes.code === 0 && kbRes.data.items?.length > 0, 'kb list 应有数据')
  const kbId = kbRes.data.items[0].id
  console.log('[ok] kb list', kbRes.data.items.length, 'first=', kbId)

  // 3) 文档列表
  const docRes = await fetchDocuments({ kb_id: kbId, page: 1, page_size: 20 })
  assert(docRes.code === 0, 'doc list code')
  const docs = docRes.data.items || []
  assert(docs.length > 0, 'doc list 应有数据')
  const completed = docs.find((d) => d.status === 'completed')
  console.log('[ok] doc list', docs.length, 'completed=', completed?.id)

  // 4) 命中检索正常
  const hit = await testRetrieve({
    kb_id: kbId,
    doc_id: completed.id,
    search_type: 'hybrid',
    query: '年假有几天',
    top_n: 3
  })
  assert(hit.code === 0 && hit.data.total_hits > 0 && hit.data.hits.length > 0, 'retrieve 应有命中')
  console.log('[ok] retrieve hits=', hit.data.total_hits)

  // 5) 空命中
  const empty = await testRetrieve({
    kb_id: kbId,
    doc_id: completed.id,
    search_type: 'hybrid',
    query: '__empty__',
    top_n: 3
  })
  assert(empty.code === 0 && empty.data.total_hits === 0 && empty.data.hits.length === 0, 'empty hits')
  console.log('[ok] retrieve empty')

  // 6) Dashboard
  const stats = await getStatsApi()
  assert(typeof stats.kb_count === 'number', 'stats.kb_count')
  console.log('[ok] dashboard', stats)

  // 7) SSE 流式（Mock 定时器）
  let chunks = 0
  let done = false
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('SSE timeout')), 8000)
    streamChat(
      { kb_id: kbId, query: '年假怎么申请' },
      {
        onStart: (e) => {
          assert(e.session_id, 'SSE start.session_id')
        },
        onMessage: (e) => {
          if (e.content) chunks += 1
        },
        onDone: (e) => {
          done = true
          clearTimeout(timer)
          assert(Array.isArray(e.sources || e.references), 'SSE done references')
          resolve()
        },
        onError: (err) => {
          clearTimeout(timer)
          reject(err)
        }
      }
    )
  })
  assert(done && chunks > 0, 'SSE 应有分段内容')
  console.log('[ok] SSE chunks=', chunks)

  // 8) 创建知识库（写路径）
  const created = await createKnowledgeBase({ name: `smoke-${Date.now()}`, description: 'smoke' })
  assert(created.code === 0 && (created.data.kb_id || created.data.id), 'create kb')
  console.log('[ok] create kb', created.data)

  console.log('\n全部 Mock 冒烟通过')
}

main().catch((e) => {
  console.error('[fail]', e)
  process.exit(1)
})
