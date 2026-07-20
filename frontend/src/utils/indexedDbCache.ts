/**
 * IndexedDB 大容量缓存
 * 分区：userId + kbId 双维度，杜绝串扰
 */
import { openDB, type DBSchema, type IDBPDatabase } from 'idb'
import type { CacheScope, ChatCacheMessage, ChatQaCacheEntry, EvalSample } from '@/types'

interface RagFeBDB extends DBSchema {
  chat_history: {
    key: string
    value: {
      scopeKey: string
      userId: string
      kbId: string
      sessionId: string
      messages: ChatCacheMessage[]
      updated_at: string
    }
    indexes: { 'by-scope': string }
  }
  qa_cache: {
    key: string
    value: ChatQaCacheEntry & {
      scopeKey: string
      questionKey: string
      retrievalMode?: string
      retrievalDegraded?: boolean
    }
    indexes: { 'by-scope': string }
  }
  kb_preview: {
    key: string
    value: { scopeKey: string; docId: string; preview: string; updated_at: string }
    indexes: { 'by-scope': string }
  }
  eval_samples_preview: {
    key: string
    value: { scopeKey: string; taskId: string; samples: EvalSample[]; updated_at: string }
    indexes: { 'by-scope': string }
  }
}

const DB_NAME = 'rag-frontend-b'
const DB_VERSION = 1

let dbPromise: Promise<IDBPDatabase<RagFeBDB>> | null = null

function getDb(): Promise<IDBPDatabase<RagFeBDB>> {
  if (!dbPromise) {
    dbPromise = openDB<RagFeBDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('chat_history')) {
          const store = db.createObjectStore('chat_history', { keyPath: 'scopeKey' })
          store.createIndex('by-scope', 'scopeKey')
        }
        if (!db.objectStoreNames.contains('qa_cache')) {
          const store = db.createObjectStore('qa_cache', { keyPath: 'questionKey' })
          store.createIndex('by-scope', 'scopeKey')
        }
        if (!db.objectStoreNames.contains('kb_preview')) {
          const store = db.createObjectStore('kb_preview', { keyPath: 'scopeKey' })
          store.createIndex('by-scope', 'scopeKey')
        }
        if (!db.objectStoreNames.contains('eval_samples_preview')) {
          const store = db.createObjectStore('eval_samples_preview', { keyPath: 'scopeKey' })
          store.createIndex('by-scope', 'scopeKey')
        }
      }
    })
  }
  return dbPromise
}

export function buildScopeKey(scope: CacheScope, extra = ''): string {
  const base = `${scope.userId || 'anon'}::${scope.kbId || 'none'}`
  return extra ? `${base}::${extra}` : base
}

function normalizeQuestionKey(q: string): string {
  return String(q || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

export async function saveChatHistory(
  scope: CacheScope,
  sessionId: string,
  messages: ChatCacheMessage[]
): Promise<void> {
  const db = await getDb()
  const scopeKey = buildScopeKey(scope, `session:${sessionId}`)
  await db.put('chat_history', {
    scopeKey,
    userId: scope.userId,
    kbId: scope.kbId,
    sessionId,
    messages,
    updated_at: new Date().toISOString()
  })
}

export async function loadChatHistory(
  scope: CacheScope,
  sessionId: string
): Promise<ChatCacheMessage[] | null> {
  const db = await getDb()
  const row = await db.get('chat_history', buildScopeKey(scope, `session:${sessionId}`))
  return row?.messages ?? null
}

export async function saveQaCache(
  scope: CacheScope,
  question: string,
  entry: Omit<ChatQaCacheEntry, 'updated_at'> & { updated_at?: string }
): Promise<void> {
  const db = await getDb()
  const scopeKey = buildScopeKey(scope)
  const qk = `${scopeKey}::qa::${normalizeQuestionKey(question)}`
  await db.put('qa_cache', {
    scopeKey,
    questionKey: qk,
    question: entry.question,
    answer: entry.answer,
    sources: entry.sources,
    retrievalMode: entry.retrievalMode,
    retrievalDegraded: entry.retrievalDegraded,
    updated_at: entry.updated_at || new Date().toISOString()
  })
}

export async function loadQaCache(
  scope: CacheScope,
  question: string
): Promise<ChatQaCacheEntry | null> {
  const db = await getDb()
  const scopeKey = buildScopeKey(scope)
  const qk = `${scopeKey}::qa::${normalizeQuestionKey(question)}`
  const row = await db.get('qa_cache', qk)
  if (!row) return null
  return {
    question: row.question,
    answer: row.answer,
    sources: row.sources,
    retrievalMode: row.retrievalMode,
    retrievalDegraded: row.retrievalDegraded,
    updated_at: row.updated_at
  }
}

export async function saveKbPreview(
  scope: CacheScope,
  docId: string,
  preview: string
): Promise<void> {
  const db = await getDb()
  await db.put('kb_preview', {
    scopeKey: buildScopeKey(scope, `doc:${docId}`),
    docId,
    preview,
    updated_at: new Date().toISOString()
  })
}

export async function loadKbPreview(scope: CacheScope, docId: string): Promise<string | null> {
  const db = await getDb()
  const row = await db.get('kb_preview', buildScopeKey(scope, `doc:${docId}`))
  return row?.preview ?? null
}

export async function saveEvalSamplesPreview(
  scope: CacheScope,
  taskId: string,
  samples: EvalSample[]
): Promise<void> {
  const db = await getDb()
  await db.put('eval_samples_preview', {
    scopeKey: buildScopeKey(scope, `eval:${taskId}`),
    taskId,
    samples,
    updated_at: new Date().toISOString()
  })
}

export async function loadEvalSamplesPreview(
  scope: CacheScope,
  taskId: string
): Promise<EvalSample[] | null> {
  const db = await getDb()
  const row = await db.get('eval_samples_preview', buildScopeKey(scope, `eval:${taskId}`))
  return row?.samples ?? null
}

/** 清除某任务的评测样本预览缓存（创建回滚用） */
export async function clearEvalSamplesPreview(scope: CacheScope, taskId: string): Promise<void> {
  const db = await getDb()
  await db.delete('eval_samples_preview', buildScopeKey(scope, `eval:${taskId}`))
}

/** 清空某用户全部分区 */
export async function clearIndexedDbByUser(userId: string): Promise<void> {
  const db = await getDb()
  const prefix = `${userId || 'anon'}::`
  for (const storeName of [
    'chat_history',
    'qa_cache',
    'kb_preview',
    'eval_samples_preview'
  ] as const) {
    const tx = db.transaction(storeName, 'readwrite')
    const store = tx.store
    let cursor = await store.openCursor()
    while (cursor) {
      const k = String(cursor.key)
      if (k.startsWith(prefix)) {
        await cursor.delete()
      }
      cursor = await cursor.continue()
    }
    await tx.done
  }
}

/** 清空某用户 + 某知识库分区 */
export async function clearIndexedDbByScope(scope: CacheScope): Promise<void> {
  const db = await getDb()
  const prefix = buildScopeKey(scope)
  for (const storeName of [
    'chat_history',
    'qa_cache',
    'kb_preview',
    'eval_samples_preview'
  ] as const) {
    const tx = db.transaction(storeName, 'readwrite')
    const store = tx.store
    let cursor = await store.openCursor()
    while (cursor) {
      const k = String(cursor.key)
      if (k === prefix || k.startsWith(`${prefix}::`)) {
        await cursor.delete()
      }
      cursor = await cursor.continue()
    }
    await tx.done
  }
}

/** 清空整个前端 B IndexedDB */
export async function clearAllIndexedDb(): Promise<void> {
  const db = await getDb()
  for (const storeName of [
    'chat_history',
    'qa_cache',
    'kb_preview',
    'eval_samples_preview'
  ] as const) {
    await db.clear(storeName)
  }
}
