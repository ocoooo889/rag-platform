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

const SELECTED_KB_KEY = 'rag_selected_kb_id'

function readSelectedKb() {
  const raw = localStorage.getItem(SELECTED_KB_KEY)
  if (!raw) return null
  const num = Number(raw)
  return Number.isNaN(num) ? raw : num
}

export const useKbStore = defineStore('kb', () => {
  const list = ref([])
  const total = ref(0)
  const selectedKbId = ref(readSelectedKb())
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
      const raw = res.data
      // [LUO-A02] 兼容 Mock items / yulin list / 直接数组
      list.value = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
      total.value = Array.isArray(raw) ? raw.length : raw?.total || list.value.length
      // 当前选中知识库不存在时，回退到首个知识库
      if (list.value.length === 0) {
        setSelectedKb(null)
      } else if (
        selectedKbId.value == null ||
        !list.value.some((item) => String(item.id) === String(selectedKbId.value))
      ) {
        setSelectedKb(list.value[0].id)
      }
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
        setSelectedKb(null)
      }
      await loadList()
    } finally {
      loading.value = false
    }
  }

  function setSelectedKb(id) {
    selectedKbId.value = id
    if (id == null || id === '') {
      localStorage.removeItem(SELECTED_KB_KEY)
      return
    }
    localStorage.setItem(SELECTED_KB_KEY, String(id))
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
