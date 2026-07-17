/**
 * 命中率测试 Pinia Store
 * 检索参数、测试问题、命中结果缓存（供 CSV 导出读取）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { testRetrieve } from '@/api/rag'

export const useHitTestStore = defineStore('hitTest', () => {
  const kbId = ref(null)
  const docIds = ref([])
  const query = ref('')
  // 默认混合检索
  const mode = ref('hybrid')
  const topN = ref(3)
  const results = ref([])
  const loading = ref(false)
  const hasSearched = ref(false)

  /** 切换检索模式时清空历史结果，保证三种模式排序差异可视化 */
  function setMode(nextMode) {
    mode.value = nextMode
    results.value = []
    hasSearched.value = false
  }

  function clearResults() {
    results.value = []
    hasSearched.value = false
  }

  async function runTest() {
    loading.value = true
    try {
      const res = await testRetrieve({
        kb_id: kbId.value,
        doc_ids: docIds.value,
        query: query.value,
        mode: mode.value,
        top_n: topN.value
      })
      const data = res.data || {}
      results.value = data.items || data.results || []
      hasSearched.value = true
      return results.value
    } finally {
      loading.value = false
    }
  }

  return {
    kbId,
    docIds,
    query,
    mode,
    topN,
    results,
    loading,
    hasSearched,
    setMode,
    clearResults,
    runTest
  }
})
