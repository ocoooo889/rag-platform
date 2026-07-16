/**
 * 知识库 Pinia Store
 * 存储列表、选中项、加载状态
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase
} from '@/api/kb'

export const useKbStore = defineStore('kb', () => {
  const list = ref([])
  const total = ref(0)
  const selectedKbId = ref(null)
  const loading = ref(false)
  const page = ref(1)
  const pageSize = ref(10)

  /** 拉取知识库分页列表 */
  async function loadList(extra = {}) {
    loading.value = true
    try {
      const res = await fetchKnowledgeBases({
        page: page.value,
        page_size: pageSize.value,
        ...extra
      })
      const data = res.data || {}
      list.value = data.items || data.list || []
      total.value = data.total || list.value.length
      return list.value
    } finally {
      loading.value = false
    }
  }

  async function createKb(payload) {
    loading.value = true
    try {
      const res = await createKnowledgeBase(payload)
      await loadList()
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function updateKb(id, payload) {
    loading.value = true
    try {
      const res = await updateKnowledgeBase(id, payload)
      await loadList()
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function removeKb(id) {
    loading.value = true
    try {
      await deleteKnowledgeBase(id)
      if (selectedKbId.value === id) {
        selectedKbId.value = null
      }
      await loadList()
    } finally {
      loading.value = false
    }
  }

  function setSelectedKb(id) {
    selectedKbId.value = id
  }

  return {
    list,
    total,
    selectedKbId,
    loading,
    page,
    pageSize,
    loadList,
    createKb,
    updateKb,
    removeKb,
    setSelectedKb
  }
})
