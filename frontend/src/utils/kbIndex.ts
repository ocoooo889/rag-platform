/**
 * 知识库索引配置（展示默认值对齐后端全局 config）
 * 后端当前为全局 CHUNK_SIZE/CHUNK_OVERLAP/EMBEDDING_MODEL，按库配置接口待对接。
 */
import type { KbChunkMode, KbIndexConfig, KbSyncMode } from '@/types'
import { loadKbIndexConfig } from '@/utils/localCache'

/** 与 backend/app/config.py 默认一致（.env 可能覆盖 embedding） */
export const KB_INDEX_DEFAULTS: KbIndexConfig = {
  chunk_size: 500,
  chunk_overlap: 50,
  chunk_mode: 'recursive',
  separators: '\\n## |\\n### |\\n|。|.',
  clean_enabled: true,
  embedding_model: 'text-embedding-v4',
  create_snapshot: true,
  sync_mode: 'pending'
}

export const CHUNK_MODE_OPTIONS: Array<{
  value: KbChunkMode
  label: string
  tip: string
  disabled?: boolean
}> = [
  {
    value: 'recursive',
    label: '递归分块（Recursive）',
    tip: '按标题/段落/句子递归切分，当前后端默认方式'
  },
  {
    value: 'fixed',
    label: '固定长度',
    tip: '按固定字符窗口切分（需后端支持）',
    disabled: true
  }
]

export const CHUNK_MODE_LABEL: Record<string, string> = Object.fromEntries(
  CHUNK_MODE_OPTIONS.map((o) => [o.value, o.label])
)

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

export function normalizeKbIndexConfig(raw: Partial<KbIndexConfig> | null | undefined): KbIndexConfig {
  const src = raw || {}
  const chunk_size = Math.max(50, Number(src.chunk_size) || KB_INDEX_DEFAULTS.chunk_size)
  let chunk_overlap = Math.max(0, Number(src.chunk_overlap) || KB_INDEX_DEFAULTS.chunk_overlap)
  if (chunk_overlap >= chunk_size) chunk_overlap = Math.max(0, chunk_size - 1)
  const mode = String(src.chunk_mode || KB_INDEX_DEFAULTS.chunk_mode).toLowerCase()
  const chunk_mode: KbChunkMode = mode === 'fixed' ? 'fixed' : 'recursive'
  const sync = String(src.sync_mode || KB_INDEX_DEFAULTS.sync_mode).toLowerCase()
  const sync_mode: KbSyncMode = sync === 'force_all' ? 'force_all' : 'pending'
  const separators =
    src.separators != null && String(src.separators).trim() !== ''
      ? String(src.separators)
      : KB_INDEX_DEFAULTS.separators
  return {
    chunk_size,
    chunk_overlap,
    chunk_mode,
    separators,
    clean_enabled: src.clean_enabled !== false,
    embedding_model: String(src.embedding_model || KB_INDEX_DEFAULTS.embedding_model).trim(),
    create_snapshot: src.create_snapshot !== false,
    sync_mode
  }
}

export function formatKbIndexSummary(cfg: KbIndexConfig): string {
  const mode = CHUNK_MODE_LABEL[cfg.chunk_mode] || cfg.chunk_mode
  return `${cfg.chunk_size}/${cfg.chunk_overlap} · ${mode} · ${cfg.embedding_model}`
}

export function validateKbIndexConfig(cfg: KbIndexConfig): string | null {
  if (cfg.chunk_overlap >= cfg.chunk_size) {
    return '切片重叠必须小于文本块大小'
  }
  if (!cfg.embedding_model) return '请选择向量模型'
  if (cfg.chunk_mode === 'fixed') {
    return '固定长度分块后端尚未支持，请使用递归分块'
  }
  return null
}

/**
 * 解析某知识库索引配置（同步读缓存，仅作展示加速）
 * 优先使用调用方传入的 apiRow（通常来自 GET 回写），其次 LocalStorage，最后默认值。
 * 页面初始化 / 切库应主动调用 fetchKbIndexConfig，勿仅依赖本函数。
 */
export function resolveKbIndexConfig(
  kbId: string | number | null | undefined,
  apiRow?: Partial<KbIndexConfig> | null
): { config: KbIndexConfig; fromLocal: boolean } {
  if (kbId == null || kbId === '') {
    return { config: normalizeKbIndexConfig(KB_INDEX_DEFAULTS), fromLocal: false }
  }
  try {
    if (apiRow && (apiRow.chunk_size != null || apiRow.embedding_model || apiRow.separators != null)) {
      return { config: normalizeKbIndexConfig(apiRow), fromLocal: false }
    }
    const local = loadKbIndexConfig(kbId)
    if (local) return { config: normalizeKbIndexConfig(local), fromLocal: true }
  } catch {
    /* localStorage 异常时回退默认 */
  }
  return { config: normalizeKbIndexConfig(KB_INDEX_DEFAULTS), fromLocal: false }
}
