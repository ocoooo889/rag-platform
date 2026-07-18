<template>
  <div class="doc-manage" v-loading="docStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>文档管理</h2>
      <el-tag v-if="envLabel" type="info" size="small">{{ envLabel }}</el-tag>
    </div>

    <div class="filter-bar">
      <el-select
        v-model="selectedKbId"
        placeholder="请选择知识库"
        clearable
        style="width: 280px"
        @change="onKbChange"
      >
        <el-option
          v-for="kb in kbStore.list"
          :key="kb.id"
          :label="kb.name"
          :value="kb.id"
        />
      </el-select>
      <el-button
        v-if="selectedKbId"
        type="danger"
        plain
        :disabled="!selectedRows.length"
        @click="openBatchDelete"
      >
        批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}
      </el-button>
    </div>

    <div v-if="hasKb" class="upload-area">
      <FileUploader
        :kb-id="selectedKbId"
        :disabled="!selectedKbId"
        v-model:uploading="uploading"
        v-model:progress="uploadProgress"
        @success="onUploadSuccess"
        @fail="onUploadFail"
      />
      <p v-if="!selectedKbId" class="hint">请先选择知识库后再上传文档</p>
    </div>

    <EmptyState v-if="!hasKb" type="kb" tip="暂无知识库，请先在知识库管理中新建" />

    <template v-else>
      <EmptyState v-if="!docStore.list.length && !docStore.loading && selectedKbId" type="doc" />

      <AppTable
        v-else-if="selectedKbId"
        ref="tableRef"
        selectable
        :data="docStore.list"
        :loading="docStore.loading"
        @selection-change="onSelectionChange"
      >
        <el-table-column label="文件名" min-width="160">
          <template #default="{ row }">
            {{ row.filename || row.file_name || row.id }}
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="文件类型" width="100" />
        <el-table-column label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分片数量" width="100" />
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.uploaded_at || row.created_at, 'datetime') }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="200">
          <template #default="{ row }">
            <el-tag :class="statusClass(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
            <div
              v-if="row.error_message"
              :class="row.status === 'failed' ? 'fail-reason' : 'warn-reason'"
            >
              {{ row.error_message }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="环境" width="140">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.env_label || row.env || envTag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <AppButton type="danger" text="删除" link @click="openDelete(row)" />
          </template>
        </el-table-column>
      </AppTable>

      <AppPagination
        v-if="selectedKbId"
        :total="docStore.total"
        v-model:page="docStore.page"
        v-model:page-size="docStore.pageSize"
        @change="reloadDocs"
      />
    </template>

    <ConfirmDialog
      v-model="deleteVisible"
      :title="batchMode ? '批量删除文档' : '删除文档'"
      :message="deleteMessage"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { formatFileSize, formatDate } from '@/utils/format'
import { getEnvTag } from '@/utils/request'
import { getDocStatusLabel, getDocStatusClassSuffix } from '@/utils/docStatus'
import AppButton from '@/components/AppButton.vue'
import AppTable from '@/components/AppTable.vue'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import FileUploader from '@/components/FileUploader.vue'

const kbStore = useKbStore()
const docStore = useDocStore()
const envTag = getEnvTag()

const selectedKbId = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const deleteVisible = ref(false)
const deleting = ref(false)
const deletingId = ref(null)
const batchMode = ref(false)
const selectedRows = ref([])
const tableRef = ref(null)

const hasKb = computed(() => kbStore.list.length > 0)
const envLabel = computed(() => {
  const first = docStore.list[0]
  return first?.env_label || (hasKb.value ? envTag : '')
})

const deleteMessage = computed(() => {
  if (batchMode.value) {
    return `确认删除选中的 ${selectedRows.value.length} 个文档？删除后向量数据不可恢复。`
  }
  return '确认删除该文档？删除后向量数据不可恢复。'
})

function statusLabel(status) {
  return getDocStatusLabel(status)
}

function statusClass(status) {
  return `doc-status doc-status--${getDocStatusClassSuffix(status)}`
}

function onSelectionChange(rows) {
  selectedRows.value = rows || []
}

async function loadKb() {
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (!kbStore.list.length) {
      selectedKbId.value = null
      docStore.clearList()
      return
    }
    selectedKbId.value = kbStore.selectedKbId || kbStore.list[0].id
    kbStore.setSelectedKb(selectedKbId.value)
    await reloadDocs()
  } catch (e) {
    // 全局 axios 处理
  }
}

async function reloadDocs() {
  selectedRows.value = []
  tableRef.value?.clearSelection?.()
  if (!selectedKbId.value) {
    docStore.clearList()
    return
  }
  try {
    await docStore.loadList(selectedKbId.value)
  } catch (e) {
    // 全局 axios 处理
  }
}

async function onKbChange(kbId) {
  kbStore.setSelectedKb(kbId || null)
  docStore.page = 1
  await reloadDocs()
}

async function onUploadSuccess() {
  await reloadDocs()
  uploadProgress.value = 0
}

function onUploadFail() {
  uploadProgress.value = 0
  reloadDocs()
}

function openDelete(row) {
  batchMode.value = false
  deletingId.value = row.id
  deleteVisible.value = true
}

function openBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先勾选要删除的文档')
    return
  }
  batchMode.value = true
  deletingId.value = null
  deleteVisible.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    if (batchMode.value) {
      const ids = selectedRows.value.map((r) => r.id)
      await docStore.removeBatch(ids)
      ElMessage.success(`成功删除 ${ids.length} 个文档`)
      selectedRows.value = []
      tableRef.value?.clearSelection?.()
    } else {
      if (!deletingId.value) return
      await docStore.remove(deletingId.value)
      ElMessage.success('删除成功')
    }
    deleteVisible.value = false
  } catch (e) {
    // 全局 axios 处理
  } finally {
    deleting.value = false
    batchMode.value = false
    deletingId.value = null
  }
}

onMounted(() => {
  loadKb()
})

onUnmounted(() => {
  docStore.stopPolling()
})
</script>

<style scoped>
.doc-manage {
  padding: 4px 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 20px 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: var(--text-color-primary);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-color-card);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.upload-area {
  margin-bottom: 20px;
  padding: 18px;
  background:
    linear-gradient(135deg, rgba(74, 122, 255, 0.07) 0%, rgba(255, 255, 255, 0.96) 46%),
    var(--bg-color-card);
  border: 1px dashed var(--border-color-primary);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

:deep(.app-table),
:deep(.el-table) {
  box-shadow: var(--shadow-card);
}

.doc-status {
  border: none;
}

.doc-status--pending {
  color: var(--status-pending-text);
  background: var(--status-pending-bg);
}

.doc-status--processing {
  color: var(--status-processing-text);
  background: var(--status-processing-bg);
}

.doc-status--completed {
  color: var(--status-completed-text);
  background: var(--status-completed-bg);
}

.doc-status--failed {
  color: var(--status-failed-text);
  background: var(--status-failed-bg);
}

.fail-reason {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--status-failed-text);
  max-width: 280px;
  word-break: break-all;
}

.warn-reason {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--status-pending-text, #b88230);
  max-width: 280px;
  word-break: break-all;
}
</style>
