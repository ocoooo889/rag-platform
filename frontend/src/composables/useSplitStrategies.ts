/**
 * 切分策略共享状态：下拉 / 默认参数 / 区间一律来自 GET /api/split-strategies
 */
import { computed, ref } from 'vue'
import {
  clearSplitStrategiesCache,
  fetchSplitStrategies,
  pickDefaultStrategy,
  type SplitStrategyItem
} from '@/api/splitStrategies'

const loading = ref(false)
const error = ref('')
const items = ref<SplitStrategyItem[]>([])
const loaded = ref(false)

export function useSplitStrategies() {
  const defaultItem = computed(() => pickDefaultStrategy(items.value))

  async function load(force = false) {
    loading.value = true
    error.value = ''
    try {
      const payload = await fetchSplitStrategies({ force })
      items.value = payload.items
      loaded.value = true
      if (!payload.items.length) {
        error.value = '后端未返回可用切分策略'
      }
      return payload
    } catch (e: unknown) {
      items.value = []
      loaded.value = false
      const msg =
        (e as { msg?: string; message?: string })?.msg ||
        (e as Error)?.message ||
        '拉取切分策略失败'
      error.value = String(msg)
      throw e
    } finally {
      loading.value = false
    }
  }

  function applyDefaultsTo(target: {
    split_strategy?: string
    chunk_mode?: string
    chunk_size?: number
    chunk_overlap?: number
    parent_chunk_size?: number
    parent_chunk_overlap?: number
    semantic_threshold?: number
  }) {
    const d = defaultItem.value
    if (!d) return
    if ('split_strategy' in target) target.split_strategy = d.value
    if ('chunk_mode' in target) target.chunk_mode = d.value
    target.chunk_size = d.default_chunk_size
    target.chunk_overlap = d.default_chunk_overlap
    if (d.default_parent_chunk_size != null) {
      target.parent_chunk_size = d.default_parent_chunk_size
    }
    if (d.default_parent_chunk_overlap != null) {
      target.parent_chunk_overlap = d.default_parent_chunk_overlap
    }
    if (d.default_semantic_threshold != null) {
      target.semantic_threshold = d.default_semantic_threshold
    }
  }

  function findByValue(value: string | null | undefined): SplitStrategyItem | undefined {
    if (!value) return undefined
    return items.value.find((i) => i.value === value)
  }

  function resetCache() {
    clearSplitStrategiesCache()
    items.value = []
    loaded.value = false
  }

  return {
    loading,
    error,
    items,
    loaded,
    defaultItem,
    load,
    applyDefaultsTo,
    findByValue,
    resetCache
  }
}
