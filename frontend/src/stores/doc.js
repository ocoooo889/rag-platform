/**
 * 文档 Pinia Store
 * 当前库文档、上传进度、文档状态
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument } from '@/api/doc'

export const useDocStore = defineStore('doc', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const currentKbId = ref(null)
  const page = ref(1)
  const pageSize = ref(10)

  /** 清空当前文档列表（切换到空知识库时） */
  function clearList() {
    list.value = []
    total.value = 0
    currentKbId.value = null
  }

  /** 按知识库隔离加载文档 */
  async function loadList(kbId, extra = {}) {
    if (!kbId) {
      clearList()
      return []
    }
    currentKbId.value = kbId
    loading.value = true
    try {
      const res = await fetchDocuments({
        kb_id: kbId,
        page: page.value,
        page_size: pageSize.value,
        ...extra
      })
      const raw = res.data
      // [LUO-A02] 兼容 Mock items / yulin list / 直接数组
      list.value = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
      total.value = Array.isArray(raw) ? raw.length : raw?.total || list.value.length
      return list.value
    } finally {
      loading.value = false
    }
  }

  /**
   * 上传文档并回写进度
   * @param {FormData} formData
   */
  async function upload(formData) {
    uploading.value = true
    uploadProgress.value = 0
    try {
      const res = await uploadDocument(formData, (evt) => {
        if (!evt.total) return
        uploadProgress.value = Math.round((evt.loaded / evt.total) * 100)
      })
      // 上传完成后刷新当前库文档列表
      if (currentKbId.value) {
        await loadList(currentKbId.value)
      }
      return res.data
    } finally {
      uploading.value = false
    }
  }

  async function remove(id) {
    loading.value = true
    try {
      await deleteDocument(id)
      if (currentKbId.value) {
        await loadList(currentKbId.value)
      }
    } finally {
      loading.value = false
    }
  }

  function resetUploadProgress() {
    uploadProgress.value = 0
  }

  return {
    list,
    total,
    loading,
    uploading,
    uploadProgress,
    currentKbId,
    page,
    pageSize,
    clearList,
    loadList,
    upload,
    remove,
    resetUploadProgress
  }
})
