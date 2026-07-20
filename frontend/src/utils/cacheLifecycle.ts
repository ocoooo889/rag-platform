/**
 * 缓存生命周期与请求防抖缓存
 */
import { lsClearFrontendB } from '@/utils/localCache'
import {
  clearAllIndexedDb,
  clearIndexedDbByScope,
  clearIndexedDbByUser
} from '@/utils/indexedDbCache'
import type { CacheScope } from '@/types'

interface DebounceEntry<T> {
  expireAt: number
  value: Promise<T>
}

const debounceMap = new Map<string, DebounceEntry<unknown>>()

/** 默认防抖窗口（毫秒） */
export const REQUEST_DEBOUNCE_MS = 1500

/**
 * 短时间内相同 key 的重复请求复用同一 Promise
 */
export function withRequestDebounceCache<T>(
  cacheKey: string,
  factory: () => Promise<T>,
  ttlMs: number = REQUEST_DEBOUNCE_MS
): Promise<T> {
  const now = Date.now()
  const hit = debounceMap.get(cacheKey) as DebounceEntry<T> | undefined
  if (hit && hit.expireAt > now) {
    return hit.value
  }
  const value = factory().finally(() => {
    /* 保留到 TTL，不立即删除，供并发复用 */
  })
  debounceMap.set(cacheKey, { expireAt: now + ttlMs, value })
  return value
}

export function clearRequestDebounceCache(): void {
  debounceMap.clear()
}

/**
 * 一键清理前端 B 全部本地缓存（LocalStorage 前缀 + IndexedDB + 防抖）
 */
export async function clearAllFrontendCache(): Promise<void> {
  lsClearFrontendB()
  clearRequestDebounceCache()
  await clearAllIndexedDb()
}

export async function onUserSwitch(prevUserId: string | null, nextUserId: string | null): Promise<void> {
  if (prevUserId && prevUserId !== nextUserId) {
    await clearIndexedDbByUser(prevUserId)
  }
  clearRequestDebounceCache()
}

/**
 * 切换知识库：清空上一分区大容量缓存，避免串读；新分区按需写入
 */
export async function onKbSwitch(
  prevScope: CacheScope | null,
  _nextScope?: CacheScope | null
): Promise<void> {
  if (prevScope?.kbId && prevScope.kbId !== 'none') {
    await clearIndexedDbByScope(prevScope)
  }
  clearRequestDebounceCache()
  void _nextScope
}

export async function onLogoutClear(userId: string | null): Promise<void> {
  if (userId) {
    await clearIndexedDbByUser(userId)
  }
  clearRequestDebounceCache()
}

export function readCurrentUserId(): string {
  try {
    const raw = localStorage.getItem('rag_user') || localStorage.getItem('userInfo')
    if (!raw) return 'anon'
    const u = JSON.parse(raw) as {
      id?: string | number
      user_id?: string | number
      username?: string
    }
    // 与对话历史分区键保持同一回退顺序，杜绝 anon/guest 串档
    return String(u.id ?? u.user_id ?? u.username ?? 'anon')
  } catch {
    return 'anon'
  }
}

export function buildCacheScope(kbId: string | number | null | undefined): CacheScope {
  return {
    userId: readCurrentUserId(),
    kbId: kbId == null || kbId === '' ? 'none' : String(kbId)
  }
}

/** 评测样本预览专用分区（非真实知识库，避免与 kbId 串扰） */
export function buildEvalCacheScope(taskPartition = 'eval'): CacheScope {
  return {
    userId: readCurrentUserId(),
    kbId: `__${taskPartition}__`
  }
}
