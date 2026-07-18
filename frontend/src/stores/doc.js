/**
 * 文档 Pinia Store
 * 当前库文档、上传进度、文档状态轮询
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument, batchDeleteDocuments } from '@/api/doc'

export const useDocStore = defineStore('doc', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const currentKbId = ref(null)
  const page = ref(1)
  const pageSize = ref(10)

  let pollingTimer = null

  function stopPolling() {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  function startPolling(kbId) {
    stopPolling()
    if (!kbId) return
    pollingTimer = setInterval(async () => {
      await loadList(kbId, { silent: true })
      const allDone = list.value.every(
        (d) => d.status === 'completed' || d.status === 'failed'
      )
      if (allDone) stopPolling()
    }, 3000)
  }

  function clearList() {
    stopPolling()
    list.value = []
    total.value = 0
    currentKbId.value = null
  }

  async function loadList(kbId, extra = {}) {
    if (!kbId) {
      clearList()
      return []
    }
    currentKbId.value = kbId
    if (!extra.silent) loading.value = true
    try {
      const res = await fetchDocuments({
        kb_id: kbId,
        page: page.value,
        page_size: pageSize.value,
        ...extra
      })
      const raw = res.data
      list.value = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
      total.value = Array.isArray(raw) ? raw.length : raw?.total || list.value.length

      const hasPending = list.value.some(
        (d) => d.status === 'pending' || d.status === 'processing'
      )
      if (hasPending) {
        if (!pollingTimer) startPolling(kbId)
      } else if (!extra.silent) {
        stopPolling()
      }
      return list.value
    } finally {
      if (!extra.silent) loading.value = false
    }
  }

  async function upload(formData) {
    uploading.value = true
    uploadProgress.value = 0
    try {
      const res = await uploadDocument(formData, (evt) => {
        if (!evt.total) return
        uploadProgress.value = Math.round((evt.loaded / evt.total) * 100)
      })
      if (currentKbId.value) {
        await loadList(currentKbId.value)
        startPolling(currentKbId.value)
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
        // 当前页删空时回退一页，避免空白页无数据
        if (list.value.length <= 1 && page.value > 1) {
          page.value -= 1
        }
        await loadList(currentKbId.value)
      }
    } finally {
      loading.value = false
    }
  }


  async function removeBatch(ids) {
    loading.value = true
    try {
      await batchDeleteDocuments(ids)
      if (currentKbId.value) {
        await loadList(currentKbId.value)
      }

  /** 批量删除：逐个调用单删接口，最后刷新一次列表 */
  async function removeBatch(ids = []) {
    const idList = [...new Set((ids || []).map((id) => String(id)).filter(Boolean))]
    if (!idList.length) return { ok: 0, fail: 0 }
    loading.value = true
    let ok = 0
    let fail = 0
    try {
      for (const id of idList) {
        try {
          await deleteDocument(id)
          ok += 1
        } catch (e) {
          fail += 1
        }
      }
      if (currentKbId.value) {
        if (ok >= list.value.length && page.value > 1) {
          page.value = 1
        }
        await loadList(currentKbId.value)
      }
      return { ok, fail }

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
    removeBatch,

    resetUploadProgress,
    startPolling,
    stopPolling

    resetUploadProgress

  }
})
