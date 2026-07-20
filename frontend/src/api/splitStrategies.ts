/**
 * 切分策略 API — 统一契约 GET /api/split-strategies
 * （后端同时保留 /api/documents/split-strategies，载荷相同）
 *
 * 禁止：本地静态策略列表兜底、写死默认策略名 / chunk_size。
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import type { ApiResponse } from '@/types'

/** 后端 split-strategies 条目（归一化后） */
export interface SplitStrategyItem {
  value: string
  label: string
  desc: string
  is_default: boolean
  default_chunk_size: number
  default_chunk_overlap: number
  chunk_size_min: number
  chunk_size_max: number
  chunk_overlap_min: number
  default_parent_chunk_size?: number
  default_parent_chunk_overlap?: number
  parent_chunk_size_min?: number
  parent_chunk_size_max?: number
  default_semantic_threshold?: number
  semantic_threshold_min?: number
  semantic_threshold_max?: number
}

export interface SplitStrategiesPayload {
  items: SplitStrategyItem[]
}

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

function asNum(v: unknown, fallback: number): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function asBool(v: unknown): boolean {
  if (typeof v === 'boolean') return v
  if (typeof v === 'string') return ['1', 'true', 'yes', 'on'].includes(v.toLowerCase())
  return Boolean(v)
}

/**
 * 字段映射：兼容旧 chunk-strategy 思维与 BE 多种命名
 * raw: value|key|strategy|id / label|name / desc|description / is_default|default
 */
export function mapSplitStrategyItem(raw: Record<string, unknown> | null | undefined): SplitStrategyItem | null {
  if (!raw || typeof raw !== 'object') return null
  const value = String(
    raw.value ?? raw.key ?? raw.strategy ?? raw.id ?? ''
  ).trim()
  if (!value) return null

  const label = String(raw.label ?? raw.name ?? value).trim() || value
  const desc = String(raw.desc ?? raw.description ?? raw.tip ?? '').trim()

  const sizeMin = asNum(raw.chunk_size_min ?? raw.min_chunk_size, 100)
  const sizeMax = asNum(raw.chunk_size_max ?? raw.max_chunk_size, 2000)
  let defaultSize = asNum(
    raw.default_chunk_size ?? raw.chunk_size ?? raw.recommended_chunk_size,
    Number.NaN
  )
  if (!Number.isFinite(defaultSize)) {
    // 无推荐值时不写死 500：取区间中位偏小，仍由后端补齐为佳
    defaultSize = Math.min(sizeMax, Math.max(sizeMin, sizeMin))
  }
  defaultSize = Math.min(sizeMax, Math.max(sizeMin, Math.round(defaultSize)))

  let defaultOverlap = asNum(
    raw.default_chunk_overlap ?? raw.chunk_overlap ?? raw.recommended_chunk_overlap,
    0
  )
  defaultOverlap = Math.max(0, Math.min(defaultOverlap, Math.max(defaultSize - 1, 0)))

  const item: SplitStrategyItem = {
    value,
    label,
    desc,
    is_default: asBool(raw.is_default ?? raw.default ?? raw.isDefault),
    default_chunk_size: defaultSize,
    default_chunk_overlap: defaultOverlap,
    chunk_size_min: sizeMin,
    chunk_size_max: sizeMax,
    chunk_overlap_min: asNum(raw.chunk_overlap_min, 0)
  }

  if (raw.default_parent_chunk_size != null || value === 'parent_child') {
    item.default_parent_chunk_size = asNum(raw.default_parent_chunk_size, Number.NaN)
    item.default_parent_chunk_overlap = asNum(raw.default_parent_chunk_overlap, 0)
    item.parent_chunk_size_min = asNum(raw.parent_chunk_size_min, 300)
    item.parent_chunk_size_max = asNum(raw.parent_chunk_size_max, 8000)
    if (!Number.isFinite(item.default_parent_chunk_size as number)) {
      delete item.default_parent_chunk_size
    }
  }
  if (raw.default_semantic_threshold != null || value === 'semantic') {
    item.default_semantic_threshold = asNum(raw.default_semantic_threshold, Number.NaN)
    item.semantic_threshold_min = asNum(raw.semantic_threshold_min, 0.1)
    item.semantic_threshold_max = asNum(raw.semantic_threshold_max, 0.95)
    if (!Number.isFinite(item.default_semantic_threshold as number)) {
      delete item.default_semantic_threshold
    }
  }
  return item
}

export function normalizeSplitStrategiesPayload(data: unknown): SplitStrategiesPayload {
  let list: unknown[] = []
  if (Array.isArray(data)) {
    list = data
  } else if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    if (Array.isArray(obj.items)) list = obj.items
    else if (Array.isArray(obj.list)) list = obj.list
    else if (Array.isArray(obj.strategies)) list = obj.strategies
  }
  const items = list
    .map((row) => mapSplitStrategyItem(row as Record<string, unknown>))
    .filter((x): x is SplitStrategyItem => !!x)
  return { items }
}

export function pickDefaultStrategy(items: SplitStrategyItem[]): SplitStrategyItem | null {
  if (!items.length) return null
  return items.find((i) => i.is_default) || items[0] || null
}

let _cache: SplitStrategiesPayload | null = null
let _inflight: Promise<SplitStrategiesPayload> | null = null

/** 清缓存（保存配置 / 退出登录时可调，规避浏览器旧策略） */
export function clearSplitStrategiesCache(): void {
  _cache = null
  _inflight = null
}

/**
 * 拉取全量切分策略。失败抛错，不回落静态列表。
 * Mock 模式返回空列表（仍不造假策略名），避免与真实联调混淆。
 */
export async function fetchSplitStrategies(options?: {
  force?: boolean
}): Promise<SplitStrategiesPayload> {
  if (!options?.force && _cache?.items?.length) {
    return _cache
  }
  if (_inflight) return _inflight

  _inflight = (async () => {
    if (MOCK_OPEN()) {
      // Mock 不提供写死业务策略；页面应提示开启真实后端
      const empty = { items: [] as SplitStrategyItem[] }
      _cache = empty
      return empty
    }
    const res = (await request.get('/api/split-strategies')) as ApiResponse<unknown>
    const payload = normalizeSplitStrategiesPayload(unwrap(res))
    if (!payload.items.length) {
      throw new Error('split-strategies 返回空列表')
    }
    _cache = payload
    return payload
  })().finally(() => {
    _inflight = null
  })

  return _inflight
}

export function getCachedSplitStrategies(): SplitStrategiesPayload | null {
  return _cache
}

export function labelOfStrategy(value: string | null | undefined): string {
  if (!value) return '—'
  const hit = _cache?.items?.find((i) => i.value === value)
  return hit?.label || value
}
