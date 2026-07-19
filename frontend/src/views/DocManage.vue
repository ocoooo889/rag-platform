<template>
  <div class="doc-manage page-shell" v-loading="docStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>知识文档库</h2>
    </div>

    <div class="page-body">
      <div class="filter-bar">
        <el-select
          v-model="selectedKbId"
          placeholder="请选择知识库"
          style="width: 280px"
          :disabled="!hasKb"
          @change="onKbChange"
        >
          <el-option
            v-for="kb in kbStore.list"
            :key="kb.id"
            :label="kb.name"
            :value="kb.id"
          />
        </el-select>
      </div>

      <EmptyState
        v-if="!hasKb && !kbStore.loading"
        type="kb"
        tip="暂无知识库，请先在知识库管理中新建"
      />

      <template v-else-if="hasKb">
        <div class="upload-area">
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

        <EmptyState
          v-if="selectedKbId && !docStore.list.length && !docStore.loading"
          type="doc"
        />

        <template v-else-if="selectedKbId && docStore.list.length">
          <AppTable
            ref="tableRef"
            selectable
            :data="docStore.list"
            :loading="docStore.loading"
            @selection-change="onSelectionChange"
          >
            <el-table-column label="文件名" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.filename || row.file_name || row.id }}
              </template>
            </el-table-column>
            <el-table-column prop="file_type" label="文件类型" show-overflow-tooltip />
            <el-table-column label="文件大小" show-overflow-tooltip>
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分片数量" show-overflow-tooltip />
            <el-table-column label="上传时间" show-overflow-tooltip>
              <template #default="{ row }">
                {{ formatDate(row.uploaded_at || row.created_at, 'YYYY/MM/DD') }}
              </template>
            </el-table-column>
            <el-table-column label="状态" show-overflow-tooltip>
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
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button text type="danger" @click="openDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </AppTable>

          <div class="table-footer">
            <el-button
              type="primary"
              :disabled="!selectedRows.length"
              @click="openBatchDelete"
            >
              批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}
            </el-button>
            <AppPagination
              :total="docStore.total"
              v-model:page="docStore.page"
              v-model:page-size="docStore.pageSize"
              @change="reloadDocs"
            />
          </div>
        </template>
      </template>

      <ConfirmDialog
        v-model="deleteVisible"
        :title="batchMode ? '批量删除文档' : '删除文档'"
        :message="deleteMessage"
        :loading="deleting"
        @confirm="confirmDelete"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { formatFileSize, formatDate } from '@/utils/format'
import { getDocStatusLabel, getDocStatusClassSuffix } from '@/utils/docStatus'
import AppTable from '@/components/AppTable.vue'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import FileUploader from '@/components/FileUploader.vue'

const kbStore = useKbStore()
const docStore = useDocStore()

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
    const preferred = kbStore.selectedKbId
    const exists =
      preferred != null && kbStore.list.some((k) => String(k.id) === String(preferred))
    selectedKbId.value = exists ? preferred : kbStore.list[0].id
    kbStore.setSelectedKb(selectedKbId.value)
    await reloadDocs()
  } catch (e) {
    // 全局 axios 处理；失败时不要误清空其它页依赖的知识库列表
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
  // 禁止清空全局选中，避免命中测试/对话等页被连带打成「无知识库」
  if (kbId == null || kbId === '') return
  kbStore.setSelectedKb(kbId)
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
  // 避免离开页面时 loading 残留遮罩影响其它视图
  docStore.loading = false
})
</script>

<style scoped>
.doc-manage {
  /* page-shell 由 admin.css 统一 */
}

.page-header {
  /* 标题样式由 admin.css 统一 */
}

.page-header h2 {
  /* 由 admin.css 统一 */
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: transparent;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.table-footer :deep(.app-pagination) {
  margin-top: 0;
  margin-left: auto;
}

.upload-area {
  margin-bottom: 20px;
  padding: 18px;
  background: color-mix(in srgb, var(--el-color-primary) 8%, var(--bg-color-card));
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
