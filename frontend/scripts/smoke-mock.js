/**
 * 前端 B Mock 双分支冒烟（mode=mock）
 * 覆盖：KB / Doc / 命中 / 会话 / SSE；正常、空数据、4002、延迟
 * 用法：npm run smoke:mock
 */
import { MOCK_OPEN } from '../src/mock/flag.js'
import {
  fetchKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase
} from '../src/api/kb.js'
import { fetchDocuments } from '../src/api/doc.js'
import { testRetrieve } from '../src/api/rag.js'
import {
  fetchChatSessions,
  createChatSession,
  streamChat
} from '../src/api/chat.js'
import { loginApi } from '../src/api/auth.js'

function assert(cond, msg) {
  if (!cond) throw new Error(msg)
}

async function main() {
  console.log('[smoke] MOCK_OPEN =>', MOCK_OPEN())
  assert(MOCK_OPEN() === true, '请使用 npm run smoke:mock（.env.mock / VITE_USE_MOCK=true）')

  // 1) 登录（共用 auth Mock，本脚本不改 auth.js）
  const login = await loginApi({ username: 'admin', password: 'admin123' })
  assert(login.token && login.user?.username === 'admin', 'login 失败')
  console.log('[ok] login', login.user.username)

  // 2) 知识库列表 + 字段 document_count
  const t0 = Date.now()
  const kbRes = await fetchKnowledgeBases({ page: 1, page_size: 10 })
  const kbDelay = Date.now() - t0
  assert(kbRes.code === 0 && kbRes.data.items?.length > 0, 'kb list 应有数据')
  assert(kbDelay >= 200, `kb list 应有 Mock 延迟，实际 ${kbDelay}ms`)
  const kb = kbRes.data.items[0]
  assert(
    typeof (kb.document_count ?? kb.doc_count) === 'number',
    'kb 应含 document_count/doc_count'
  )
  const kbId = kb.id
  console.log('[ok] kb list', kbRes.data.items.length, 'delay=', kbDelay, 'ms')

  // 3) 文档列表（有数据）
  const docRes = await fetchDocuments({ kb_id: kbId, page: 1, page_size: 20 })
  assert(docRes.code === 0, 'doc list code')
  const docs = docRes.data.items || []
  assert(docs.length > 0, 'doc list 应有数据')
  docs.forEach((d) => {
    assert(
      ['pending', 'processing', 'completed', 'failed'].includes(d.status),
      `非法 status=${d.status}`
    )
  })
  const completed = docs.find((d) => d.status === 'completed')
  const processing = docs.find((d) => d.status === 'processing' || d.status === 'pending')
  console.log('[ok] doc list', docs.length, 'completed=', completed?.id)

  // 4) 空文档列表（无此库文档或空库）
  const emptyDoc = await fetchDocuments({ kb_id: 'kb_empty_smoke', page: 1, page_size: 10 }).catch(
    (e) => e
  )
  if (emptyDoc?.code === 404) {
    console.log('[ok] doc list 404 未知库')
  } else {
    const emptyKbDocs = await fetchDocuments({ kb_id: 'kb002', page: 1, page_size: 10 })
    // kb002 可能仅 1 条；再测 page 很大导致 items 空
    const pageFar = await fetchDocuments({ kb_id: kbId, page: 99, page_size: 10 })
    assert(pageFar.code === 0 && pageFar.data.items.length === 0, '超页应空 items')
    console.log('[ok] doc list empty page', emptyKbDocs.data?.total)
  }

  // 5) 命中检索正常
  assert(completed, '需要 completed 文档做命中')
  const hit = await testRetrieve({
    kb_id: kbId,
    doc_id: completed.id,
    search_type: 'hybrid',
    query: '年假有几天',
    top_n: 3
  })
  assert(
    hit.code === 0 &&
      Array.isArray(hit.data.hits) &&
      hit.data.total_hits > 0 &&
      hit.data.hits.length > 0,
    'retrieve 应有 hits'
  )
  console.log('[ok] retrieve hits=', hit.data.total_hits)

  // 6) 空命中
  const empty = await testRetrieve({
    kb_id: kbId,
    doc_id: completed.id,
    search_type: 'hybrid',
    query: '__empty__',
    top_n: 3
  })
  assert(empty.code === 0 && empty.data.total_hits === 0 && empty.data.hits.length === 0, 'empty hits')
  console.log('[ok] retrieve empty')

  // 7) 文档未就绪 4002
  if (processing) {
    try {
      await testRetrieve({
        kb_id: kbId,
        doc_id: processing.id,
        search_type: 'hybrid',
        query: '任意问题',
        top_n: 3
      })
      throw new Error('未就绪文档应 4002')
    } catch (e) {
      assert(e.code === 4002, `期望 4002，得到 ${e.code}`)
      console.log('[ok] retrieve 4002 未就绪')
    }
  } else {
    console.log('[skip] 无 processing/pending 文档，跳过 4002')
  }

  // 8) 会话 CRUD（Mock）
  const sess = await createChatSession({ kb_id: kbId })
  assert(sess.code === 0 && sess.data.session_id, 'create session')
  const listSess = await fetchChatSessions({ kb_id: kbId })
  assert(listSess.code === 0 && listSess.data.items?.length > 0, 'session list')
  console.log('[ok] chat sessions', listSess.data.items.length)

  // 9) SSE 流式（Mock 定时器分段）
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

  // 10) 创建知识库
  const created = await createKnowledgeBase({
    name: `smoke-${Date.now()}`,
    description: 'smoke'
  })
  assert(created.code === 0 && (created.data.kb_id || created.data.id), 'create kb')
  const newId = created.data.kb_id || created.data.id
  console.log('[ok] create kb', newId)

  // 清理冒烟库，避免污染后续运行
  await deleteKnowledgeBase(newId)
  console.log('[ok] delete kb', newId)

  console.log('\n前端 B Mock 冒烟全部通过')
}

main().catch((e) => {
  console.error('[fail]', e)
  process.exit(1)
})
