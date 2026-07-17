/**
 * 命中率测试 Pinia Store
 * [LUO-A01/R3] 多选文档时循环调用单 doc_id 接口，合并 data.hits
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { testRetrieve } from '@/api/rag'

export const useHitTestStore = defineStore('hitTest', () => {
  const kbId = ref(null)
  const docIds = ref([])
  const query = ref('')
  /** UI Tab 模式，请求字段为 search_type（非 mode） */
  const searchType = ref('hybrid')
  const topN = ref(3)
  const results = ref([])
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

      // [LUO-A01] 后端仅支持单个 doc_id：前端循环调用后按 score 合并
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
          // 契约主字段 hits；items 仅作历史兼容兜底
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
    /** @deprecated 使用 searchType；保留别名避免页面破坏 */
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
