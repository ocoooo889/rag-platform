/**
 * 知识库索引配置 — 对齐 backend KbIndexConfigOut / 校验区间
 * 分块策略名称/默认块大小：请用 GET /api/split-strategies，勿在此写死。
 */
import type { KbIndexConfig, KbSearchType, KbSyncMode } from '@/types'
import { loadKbIndexConfig } from '@/utils/localCache'
import { getCachedSplitStrategies, pickDefaultStrategy } from '@/api/splitStrategies'

/** 与 backend/app/api/kb.py 校验一致；数值仅作区间钳制兜底，默认值优先取 split-strategies */
export const KB_CHUNK_SIZE_MIN = 100
export const KB_CHUNK_SIZE_MAX = 2000

function serverPreferredChunkDefaults(): Pick<KbIndexConfig, 'chunk_size' | 'chunk_overlap'> {
  const d = pickDefaultStrategy(getCachedSplitStrategies()?.items || [])
  if (d) {
    return {
      chunk_size: d.default_chunk_size,
      chunk_overlap: d.default_chunk_overlap
    }
  }
  // 缓存未就绪时的中性占位（仍落在后端合法区间），页面应尽快拉取 split-strategies / index-config
  return {
    chunk_size: KB_CHUNK_SIZE_MIN,
    chunk_overlap: 0
  }
}

export function getKbIndexDefaults(): KbIndexConfig {
  const chunk = serverPreferredChunkDefaults()
  return {
    chunk_size: chunk.chunk_size,
    chunk_overlap: chunk.chunk_overlap,
    hybrid_alpha: 0.7,
    default_search_type: 'hybrid',
    enable_rerank: false,
    default_top_n: 3,
    create_snapshot: true,
    sync_mode: 'pending'
  }
}

/** @deprecated 使用 getKbIndexDefaults()；模块常量会在首次 import 时冻结，请勿依赖其 chunk 数值 */
export const KB_INDEX_DEFAULTS: KbIndexConfig = getKbIndexDefaults()

export const SEARCH_TYPE_OPTIONS: Array<{ value: KbSearchType; label: string }> = [
  { value: 'hybrid', label: '混合检索' },
  { value: 'vector', label: '向量检索' },
  { value: 'keyword', label: '关键词检索' }
]

export const SYNC_MODE = {
  PENDING: 'pending' as KbSyncMode,
  FORCE_ALL: 'force_all' as KbSyncMode
}

export const SYNC_MODE_OPTIONS: Array<{ value: KbSyncMode; label: string; tip: string }> = [
  {
    value: SYNC_MODE.PENDING,
    label: '同步规则到待处理文档',
    tip: '仅对 pending / 新上传文档应用新切分与向量配置'
  },
  {
    value: SYNC_MODE.FORCE_ALL,
    label: '强制全部重新向量化',
    tip: '对库内已有文档全部重新入库（耗时更长）'
  }
]

function clampChunkSize(n: number): number {
  const fallback = serverPreferredChunkDefaults().chunk_size
  if (!Number.isFinite(n)) return fallback
  return Math.min(KB_CHUNK_SIZE_MAX, Math.max(KB_CHUNK_SIZE_MIN, Math.round(n)))
}

export function normalizeKbIndexConfig(raw: Partial<KbIndexConfig> | null | undefined): KbIndexConfig {
  const defaults = getKbIndexDefaults()
  const src = raw || {}
  const chunk_size = clampChunkSize(Number(src.chunk_size) || defaults.chunk_size)
  let chunk_overlap = Math.max(0, Number(src.chunk_overlap))
  if (!Number.isFinite(Number(src.chunk_overlap))) {
    chunk_overlap = defaults.chunk_overlap
  }
  if (chunk_overlap >= chunk_size) chunk_overlap = Math.max(0, chunk_size - 1)

  const st = String(src.default_search_type || defaults.default_search_type).toLowerCase()
  const default_search_type: KbSearchType =
    st === 'vector' || st === 'keyword' || st === 'hybrid' ? st : 'hybrid'

  let hybrid_alpha = Number(src.hybrid_alpha)
  if (!Number.isFinite(hybrid_alpha)) hybrid_alpha = defaults.hybrid_alpha
  hybrid_alpha = Math.min(1, Math.max(0, hybrid_alpha))

  let default_top_n = Number(src.default_top_n)
  if (!Number.isFinite(default_top_n) || default_top_n < 1) {
    default_top_n = defaults.default_top_n
  }
  default_top_n = Math.min(10, Math.max(1, Math.round(default_top_n)))

  const sync = String(src.sync_mode || defaults.sync_mode || 'pending').toLowerCase()
  const sync_mode: KbSyncMode = sync === 'force_all' ? 'force_all' : 'pending'

  return {
    kb_id: src.kb_id,
    chunk_size,
    chunk_overlap,
    hybrid_alpha,
    default_search_type,
    enable_rerank: src.enable_rerank === true,
    default_top_n,
    updated_at: src.updated_at ?? null,
    create_snapshot: src.create_snapshot !== false,
    sync_mode
  }
}

/** PUT 只提交后端接受的字段 */
export function toKbIndexConfigPayload(cfg: KbIndexConfig): Record<string, unknown> {
  return {
    chunk_size: cfg.chunk_size,
    chunk_overlap: cfg.chunk_overlap,
    hybrid_alpha: cfg.hybrid_alpha,
    default_search_type: cfg.default_search_type,
    enable_rerank: cfg.enable_rerank,
    default_top_n: cfg.default_top_n
  }
}

export function formatKbIndexSummary(cfg: KbIndexConfig): string {
  const st =
    SEARCH_TYPE_OPTIONS.find((o) => o.value === cfg.default_search_type)?.label ||
    cfg.default_search_type
  const rerank = cfg.enable_rerank ? 'rerank开' : 'rerank关'
  return `${cfg.chunk_size}/${cfg.chunk_overlap} · ${st} · α${cfg.hybrid_alpha} · top${cfg.default_top_n} · ${rerank}`
}

export function validateKbIndexConfig(cfg: KbIndexConfig): string | null {
  if (cfg.chunk_size < KB_CHUNK_SIZE_MIN || cfg.chunk_size > KB_CHUNK_SIZE_MAX) {
    return `文本块大小须在 ${KB_CHUNK_SIZE_MIN}~${KB_CHUNK_SIZE_MAX} 之间`
  }
  if (cfg.chunk_overlap < 0 || cfg.chunk_overlap >= cfg.chunk_size) {
    return '切片重叠必须小于文本块大小且 ≥ 0'
  }
  if (cfg.hybrid_alpha < 0 || cfg.hybrid_alpha > 1) {
    return '混合检索权重 hybrid_alpha 须在 0~1 之间'
  }
  if (cfg.default_top_n < 1 || cfg.default_top_n > 10) {
    return 'default_top_n 须在 1~10 之间'
  }
  return null
}

export function resolveKbIndexConfig(
  kbId: string | number | null | undefined,
  apiRow?: Partial<KbIndexConfig> | null
): { config: KbIndexConfig; fromLocal: boolean } {
  if (kbId == null || kbId === '') {
    return { config: normalizeKbIndexConfig(getKbIndexDefaults()), fromLocal: false }
  }
  try {
    if (apiRow && (apiRow.chunk_size != null || apiRow.default_search_type != null)) {
      return { config: normalizeKbIndexConfig(apiRow), fromLocal: false }
    }
    const local = loadKbIndexConfig(kbId)
    if (local) return { config: normalizeKbIndexConfig(local), fromLocal: true }
  } catch {
    /* localStorage 异常时回退默认 */
  }
  return { config: normalizeKbIndexConfig(getKbIndexDefaults()), fromLocal: false }
}
