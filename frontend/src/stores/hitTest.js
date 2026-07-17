/**
 * 命中率测试 Pinia Store
 * UI 状态：loading / empty / error + 三模式 Tab
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { testRetrieve } from '@/api/rag'

export const useHitTestStore = defineStore('hitTest', () => {
  const kbId = ref(null)
  const docIds = ref([])
  const query = ref('')
  /** 检索模式（UI Tab）；请求时映射为契约字段 search_type */
  const searchType = ref('hybrid')
  const topN = ref(3)
  const results = ref([])
  /** 页面请求态（非后端业务字段） */
  const loading = ref(false)
  const hasSearched = ref(false)
  const errorMsg = ref('')

  function setMode(nextMode) {
    searchType.value = nextMode
    results.value = []
    hasSearched.value = false
    errorMsg.value = ''
  }

  function clearResults() {
    results.value = []
    hasSearched.value = false
    errorMsg.value = ''
  }

  function normalizeHits(hits = []) {
    return (hits || []).map((item, index) => ({
      rank: index + 1,
      score: Number(item.score) || 0,
      content: item.content || '',
      source_doc: item.source_doc || '',
      chunk_id: String(item.chunk_id || ''),
      doc_id: item.doc_id
    }))
  }

  async function runTest() {
    loading.value = true
    errorMsg.value = ''
    try {
      const ids = Array.isArray(docIds.value) ? docIds.value.filter(Boolean) : []
      if (!ids.length) {
        results.value = []
        hasSearched.value = true
        return results.value
      }

      const settled = await Promise.allSettled(
        ids.map((docId) =>
          testRetrieve({
            kb_id: kbId.value,
            doc_id: docId,
            search_type: searchType.value,
            query: query.value,
            top_n: topN.value
          })
        )
      )

      let merged = []
      let firstError = null
      for (const item of settled) {
        if (item.status === 'fulfilled') {
          const data = item.value?.data || {}
          merged = merged.concat(data.hits || data.items || [])
        } else if (!firstError) {
          firstError = item.reason
        }
      }

      if (!merged.length && firstError) {
        errorMsg.value =
          firstError?.message || firstError?.msg || '检索失败，请稍后重试'
        hasSearched.value = true
        results.value = []
        throw firstError
      }

      merged.sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0))
      results.value = normalizeHits(merged.slice(0, topN.value))
      hasSearched.value = true
      return results.value
    } catch (e) {
      if (!errorMsg.value) {
        errorMsg.value = e?.message || e?.msg || '检索失败，请稍后重试'
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    kbId,
    docIds,
    query,
    searchType,
    /** 同 searchType，兼容页面旧绑定名 mode */
    mode: searchType,
    topN,
    results,
    loading,
    hasSearched,
    errorMsg,
    setMode,
    clearResults,
    runTest
  }
})
