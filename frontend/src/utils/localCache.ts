/**
 * LocalStorage 轻量缓存（仅配置类数据）
 * 大容量数据请用 indexedDbCache
 */
import type { KbIndexConfig, RuntimeModelConfig } from '@/types'

const PREFIX = 'rag-fe-b:'

function key(name: string): string {
  return `${PREFIX}${name}`
}

export function lsGet<T>(name: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key(name))
    if (raw == null) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function lsSet<T>(name: string, value: T): void {
  try {
    localStorage.setItem(key(name), JSON.stringify(value))
  } catch {
    /* quota / private mode */
  }
}

export function lsRemove(name: string): void {
  try {
    localStorage.removeItem(key(name))
  } catch {
    /* ignore */
  }
}

/** 清除本模块写入的全部 localStorage（不影响 token / 旧会话键，见 clearAllFrontendCache） */
export function lsClearFrontendB(): void {
  try {
    const toRemove: string[] = []
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i)
      if (k && k.startsWith(PREFIX)) toRemove.push(k)
    }
    toRemove.forEach((k) => localStorage.removeItem(k))
  } catch {
    /* ignore */
  }
}

const RUNTIME_MODEL_KEY = 'runtime-model-config'
const UI_PREF_EXTRA_KEY = 'page-prefs'

export function loadRuntimeModelConfig(): RuntimeModelConfig | null {
  return lsGet<RuntimeModelConfig | null>(RUNTIME_MODEL_KEY, null)
}

export function saveRuntimeModelConfig(cfg: RuntimeModelConfig): void {
  lsSet(RUNTIME_MODEL_KEY, cfg)
}

/** @deprecated 切分策略改由 /api/split-strategies 下发；清理旧本地键 */
export function clearLegacyChunkStrategyCache(): void {
  lsRemove('chunk-strategy-config')
}

export function loadPagePrefs<T extends Record<string, unknown>>(fallback: T): T {
  return lsGet(UI_PREF_EXTRA_KEY, fallback)
}

export function savePagePrefs<T extends Record<string, unknown>>(prefs: T): void {
  lsSet(UI_PREF_EXTRA_KEY, prefs)
}

const KB_INDEX_MAP_KEY = 'kb-index-config-map'

export function loadKbIndexConfigMap(): Record<string, KbIndexConfig> {
  return lsGet<Record<string, KbIndexConfig>>(KB_INDEX_MAP_KEY, {})
}

export function loadKbIndexConfig(kbId: string | number | null | undefined): KbIndexConfig | null {
  if (kbId == null || kbId === '') return null
  const map = loadKbIndexConfigMap()
  return map[String(kbId)] || null
}

export function saveKbIndexConfig(kbId: string | number, cfg: KbIndexConfig): void {
  const map = loadKbIndexConfigMap()
  map[String(kbId)] = cfg
  lsSet(KB_INDEX_MAP_KEY, map)
}

export function removeKbIndexConfig(kbId: string | number): void {
  const map = loadKbIndexConfigMap()
  delete map[String(kbId)]
  lsSet(KB_INDEX_MAP_KEY, map)
}

const EVAL_FILTERS_KEY = 'eval-page-filters'
const EVAL_DRAFT_MAP_KEY = 'eval-sample-drafts'

export function loadEvalPageFilters<T extends Record<string, unknown>>(fallback: T): T {
  return lsGet(EVAL_FILTERS_KEY, fallback)
}

export function saveEvalPageFilters<T extends Record<string, unknown>>(prefs: T): void {
  lsSet(EVAL_FILTERS_KEY, prefs)
}

export function loadEvalSampleDraft(taskId: string): {
  question: string
  expected_answer: string
  tags: string
  updated_at: string
} | null {
  if (!taskId) return null
  const map = lsGet<Record<string, {
    question: string
    expected_answer: string
    tags: string
    updated_at: string
  }>>(EVAL_DRAFT_MAP_KEY, {})
  return map[String(taskId)] || null
}

export function saveEvalSampleDraft(
  taskId: string,
  draft: { question: string; expected_answer: string; tags: string }
): void {
  if (!taskId) return
  const map = lsGet<Record<string, unknown>>(EVAL_DRAFT_MAP_KEY, {})
  map[String(taskId)] = { ...draft, updated_at: new Date().toISOString() }
  lsSet(EVAL_DRAFT_MAP_KEY, map)
}

export function clearEvalSampleDraft(taskId: string): void {
  if (!taskId) return
  const map = lsGet<Record<string, unknown>>(EVAL_DRAFT_MAP_KEY, {})
  delete map[String(taskId)]
  lsSet(EVAL_DRAFT_MAP_KEY, map)
}

/** 创建任务事务进行中的临时标记（上传失败回滚后清除） */
const EVAL_PENDING_CREATE_KEY = 'eval-pending-create'

export function loadEvalPendingCreate(): {
  taskId: string
  name: string
  updated_at: string
} | null {
  return lsGet(EVAL_PENDING_CREATE_KEY, null)
}

export function saveEvalPendingCreate(taskId: string, name: string): void {
  lsSet(EVAL_PENDING_CREATE_KEY, {
    taskId: String(taskId),
    name: String(name || ''),
    updated_at: new Date().toISOString()
  })
}

export function clearEvalPendingCreate(): void {
  lsRemove(EVAL_PENDING_CREATE_KEY)
}
