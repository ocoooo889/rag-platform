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

    <EmptyState v-if="!hasKb" type="kb" tip="暂无知识库，请先在知识库管理中新建" />

    <template v-else>
      <!-- 顶栏：标题 + 上传 -->
      <div class="doc-top">
        <h2 class="doc-top__title">上传文档</h2>
        <div class="doc-top__actions">
          <el-button text :icon="Refresh" :disabled="!selectedKbId" @click="reloadDocs">
            同步状态
          </el-button>
          <el-button
            type="danger"
            plain
            :disabled="!selectedKbId || !selectedIds.length"
            :loading="batchDeleting"
            @click="openBatchDelete"
          >
            批量删除{{ selectedIds.length ? `（${selectedIds.length}）` : '' }}
          </el-button>
          <el-button
            type="primary"
            class="doc-top__upload-btn"
            :disabled="!selectedKbId"
            @click="openUploadDialog"
          >
            上传文档
          </el-button>
        </div>
      </div>

      <!-- 筛选：知识库 + 搜索 -->
      <div class="doc-filters">
        <el-select
          v-model="selectedKbId"
          class="doc-filters__kb"
          placeholder="请选择知识库"
          clearable
          @change="onKbChange"
        >
          <el-option
            v-for="kb in kbStore.list"
            :key="kb.id"
            :label="kb.name"
            :value="kb.id"
          />
        </el-select>
        <el-input
          v-model="searchKeyword"
          class="doc-filters__search"
          placeholder="搜索文档名称"
          clearable
          :prefix-icon="Search"
        />
      </div>

      <p v-if="!selectedKbId" class="hint">请先选择知识库后再管理文档</p>

      <template v-else>
        <!-- 统计卡片 -->
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-card__num">{{ stats.total }}</div>
            <div class="stat-card__label">全部</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__num stat-card__num--ok">{{ stats.ready }}</div>
            <div class="stat-card__label">已就绪</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__num stat-card__num--proc">{{ stats.vectorizing }}</div>
            <div class="stat-card__label">向量化中</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__num stat-card__num--fail">{{ stats.failed }}</div>
            <div class="stat-card__label">解析失败</div>
          </div>
        </div>

        <!-- 文档列表卡片：空列表时仍保留表头 + 分页 -->
        <section class="list-card">
          <div class="list-head">
            <span class="col-check">
              <el-checkbox
                :model-value="isAllSelected"
                :indeterminate="isIndeterminate"
                :disabled="!filteredList.length"
                @change="toggleSelectAll"
              />
            </span>
            <span class="col-name">文档名称</span>
            <span class="col-time">上传时间</span>
            <span class="col-action">操作</span>
          </div>

          <EmptyState
            v-if="!filteredList.length && !docStore.loading"
            type="doc"
            tip="暂无文档，请点击右上角上传"
          />

          <ul v-else class="list-body">
            <li v-for="row in filteredList" :key="row.id" class="list-row">
              <div class="col-check">
                <el-checkbox
                  :model-value="selectedIds.includes(String(row.id))"
                  @change="(val) => toggleSelect(row.id, val)"
                />
              </div>
              <div class="col-name">
                <el-icon
                  class="status-icon"
                  :class="[statusIconClass(row.status), { 'is-loading': !isCompleted(row.status) && !isFailed(row.status) }]"
                  :size="16"
                >
                  <CircleCheck v-if="isCompleted(row.status)" />
                  <WarningFilled v-else-if="isFailed(row.status)" />
                  <Loading v-else />
                </el-icon>
                <span class="file-name" :title="row.filename || row.file_name">
                  {{ row.filename || row.file_name || row.id }}
                </span>
              </div>
              <div class="col-time">
                {{ formatDate(row.uploaded_at || row.created_at, 'datetime') }}
              </div>
              <div class="col-action">
                <el-button
                  class="ghost-btn"
                  size="small"
                  @click="openPreview(row)"
                >
                  查看
                </el-button>
                <el-button
                  v-if="isFailed(row.status)"
                  class="ghost-btn ghost-btn--danger"
                  size="small"
                  disabled
                >
                  解析失败
                </el-button>
                <el-button
                  class="ghost-btn ghost-btn--danger"
                  size="small"
                  @click="openDelete(row)"
                >
                  删除
                </el-button>
              </div>
            </li>
          </ul>

          <AppPagination
            class="list-pagination"
            show-empty
            :total="docStore.total"
            v-model:page="docStore.page"
            v-model:page-size="docStore.pageSize"
            @change="reloadDocs"
          />
        </section>
      </template>
    </template>

    <!-- 上传弹窗（无命中测试） -->
    <el-dialog
      v-model="uploadVisible"
      title="上传文档"
      width="520px"
      destroy-on-close
      :close-on-click-modal="!uploading"
      class="upload-dialog"
      @closed="onUploadDialogClosed"
    >

      <FileUploader
        v-if="uploadVisible"
        :kb-id="selectedKbId"
        :disabled="!selectedKbId"
        v-model:uploading="uploading"
        v-model:progress="uploadProgress"
        @success="onUploadSuccess"
        @fail="onUploadFail"
        @cancel="uploadVisible = false"
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

    </el-dialog>

    <!-- 查看详情弹窗（仅元数据，无命中测试） -->
    <el-dialog
      v-model="previewVisible"
      title="文档详情"
      width="420px"
      destroy-on-close
    >
      <dl v-if="previewDoc" class="preview-meta">
        <div class="preview-meta__row">
          <dt>文件名</dt>
          <dd>{{ previewDoc.filename || previewDoc.file_name || previewDoc.id }}</dd>
        </div>
        <div class="preview-meta__row">
          <dt>文件大小</dt>
          <dd>{{ formatFileSize(previewDoc.file_size) }}</dd>
        </div>
        <div class="preview-meta__row">
          <dt>分片数量</dt>
          <dd>{{ previewDoc.chunk_count ?? 0 }}</dd>
        </div>
        <div class="preview-meta__row">
          <dt>文档状态</dt>
          <dd>{{ displayStatusLabel(previewDoc.status) }}</dd>
        </div>
        <div class="preview-meta__row">
          <dt>上传时间</dt>
          <dd>{{ formatDate(previewDoc.uploaded_at || previewDoc.created_at, 'datetime') }}</dd>
        </div>
      </dl>
    </el-dialog>


    <ConfirmDialog
      v-model="deleteVisible"
      :title="batchMode ? '批量删除文档' : '删除文档'"
      :message="deleteMessage"

      :loading="deleting"

      :loading="deleting || batchDeleting"

      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck,
  Loading,
  Refresh,
  Search,
  WarningFilled
} from '@element-plus/icons-vue'

import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { formatFileSize, formatDate } from '@/utils/format'
import { normalizeDocStatus, DOC_STATUS } from '@/utils/docStatus'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import FileUploader from '@/components/FileUploader.vue'

const kbStore = useKbStore()
const docStore = useDocStore()

const selectedKbId = ref(null)
const searchKeyword = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadVisible = ref(false)
const previewVisible = ref(false)
const previewDoc = ref(null)
const deleteVisible = ref(false)
const deleting = ref(false)
const deletingId = ref(null)

const batchMode = ref(false)
const selectedRows = ref([])
const tableRef = ref(null)

const selectedIds = ref([])
const batchMode = ref(false)
const batchDeleting = ref(false)


const hasKb = computed(() => kbStore.list.length > 0)

const filteredList = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  let rows = docStore.list || []
  if (kw) {
    rows = rows.filter((row) =>
      String(row.filename || row.file_name || '').toLowerCase().includes(kw)
    )
  }
  return rows
})

const filteredIds = computed(() =>
  filteredList.value.map((row) => String(row.id))
)

const isAllSelected = computed(
  () =>
    filteredIds.value.length > 0 &&
    filteredIds.value.every((id) => selectedIds.value.includes(id))
)

const isIndeterminate = computed(() => {
  const n = filteredIds.value.filter((id) => selectedIds.value.includes(id)).length
  return n > 0 && n < filteredIds.value.length
})

const deleteMessage = computed(() => {
  if (batchMode.value) {
    return `确认删除选中的 ${selectedIds.value.length} 个文档？删除后向量数据不可恢复。`
  }
  return '确认删除该文档？删除后向量数据不可恢复。'
})

watch(filteredList, () => {
  const valid = new Set(filteredIds.value)
  selectedIds.value = selectedIds.value.filter((id) => valid.has(id))
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

const stats = computed(() => {
  const rows = docStore.list || []
  let ready = 0
  let vectorizing = 0
  let failed = 0
  for (const row of rows) {
    const s = normalizeDocStatus(row.status)
    if (s === DOC_STATUS.COMPLETED) ready += 1
    else if (s === DOC_STATUS.FAILED) failed += 1
    else vectorizing += 1
  }
  return {
    total: docStore.total || rows.length,
    ready,
    vectorizing,
    failed
  }
})

function isCompleted(status) {
  return normalizeDocStatus(status) === DOC_STATUS.COMPLETED
}

function isFailed(status) {
  return normalizeDocStatus(status) === DOC_STATUS.FAILED
}

function displayStatusLabel(status) {
  const s = normalizeDocStatus(status)
  const map = {
    [DOC_STATUS.COMPLETED]: '已就绪',
    [DOC_STATUS.PROCESSING]: '向量化中',
    [DOC_STATUS.PENDING]: '等待中',
    [DOC_STATUS.FAILED]: '解析失败'
  }
  return map[s] || '等待中'
}

function statusIconClass(status) {
  if (isCompleted(status)) return 'status-icon--ok'
  if (isFailed(status)) return 'status-icon--fail'
  return 'status-icon--proc'
}

function openUploadDialog() {
  if (!selectedKbId.value) return
  uploadVisible.value = true
}

function onUploadDialogClosed() {
  uploadProgress.value = 0
}

function openPreview(row) {
  previewDoc.value = row
  previewVisible.value = true

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
  searchKeyword.value = ''
  selectedIds.value = []
  await reloadDocs()
}

async function onUploadSuccess() {
  await reloadDocs()
  uploadProgress.value = 0
  uploadVisible.value = false
}

function onUploadFail() {
  uploadProgress.value = 0
  reloadDocs()
}

function toggleSelect(id, checked) {
  const sid = String(id)
  if (checked) {
    if (!selectedIds.value.includes(sid)) selectedIds.value.push(sid)
  } else {
    selectedIds.value = selectedIds.value.filter((x) => x !== sid)
  }
}

function toggleSelectAll(checked) {
  if (checked) {
    selectedIds.value = [...new Set([...selectedIds.value, ...filteredIds.value])]
  } else {
    const removeSet = new Set(filteredIds.value)
    selectedIds.value = selectedIds.value.filter((id) => !removeSet.has(id))
  }
}

function openDelete(row) {
  batchMode.value = false
  deletingId.value = row.id
  deleteVisible.value = true
}

function openBatchDelete() {

  if (!selectedRows.value.length) {

  if (!selectedIds.value.length) {

    ElMessage.warning('请先勾选要删除的文档')
    return
  }
  batchMode.value = true
  deletingId.value = null
  deleteVisible.value = true
}

async function confirmDelete() {
  deleting.value = true
  batchDeleting.value = batchMode.value
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

      const ids = [...selectedIds.value]
      const result = await docStore.removeBatch(ids)
      selectedIds.value = []
      deleteVisible.value = false
      if (result.fail) {
        ElMessage.warning(`成功删除 ${result.ok} 个，失败 ${result.fail} 个`)
      } else {
        ElMessage.success(`已删除 ${result.ok} 个文档`)
      }
      // 删光后回到第 1 页，分页栏仍显示 Total 0
      if (docStore.total === 0) {
        docStore.page = 1
      }
    } else {
      if (!deletingId.value) return
      await docStore.remove(deletingId.value)
      selectedIds.value = selectedIds.value.filter(
        (id) => id !== String(deletingId.value)
      )
      deleteVisible.value = false
      if (docStore.total === 0) {
        docStore.page = 1
      }
    }

  } catch (e) {
    // 全局 axios 处理
  } finally {
    deleting.value = false

    batchDeleting.value = false

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

  min-height: 100%;
  padding: 8px 4px 24px;
  background: var(--bg-color-page);

}

.doc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;

  margin-bottom: 18px;
  padding: 20px 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);

  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;

}

.doc-top__title {
  margin: 0;

  font-size: 24px;
  color: var(--text-color-primary);
}

.filter-bar {

  font-size: 20px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.doc-top__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-top__upload-btn {
  border-radius: 20px;
  padding: 10px 22px;
}

.doc-filters {

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

  flex-wrap: wrap;
}

.doc-filters__kb {
  width: 240px;
}

.doc-filters__search {
  width: 280px;
  max-width: 100%;
}

.doc-filters__search :deep(.el-input__wrapper) {
  border-radius: 18px;

}

.hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-color-secondary);
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-color-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stat-card__num {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color-primary);
  line-height: 1.2;
}

.stat-card__num--ok {
  color: var(--status-completed-text);
}

.stat-card__num--proc {
  color: var(--color-primary);
}

.stat-card__num--fail {
  color: var(--status-failed-text);
}

.stat-card__label {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-color-secondary);
}

.list-card {
  background: var(--bg-color-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 8px 0 12px;
  overflow: hidden;
}

.list-head,
.list-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 2fr) minmax(140px, 1fr) minmax(200px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px 20px;
}

.col-check {
  display: flex;
  align-items: center;
  justify-content: center;
}

.list-head {
  font-size: 13px;
  color: var(--text-color-secondary);
  border-bottom: 1px solid var(--border-color);
}

.list-body {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list-row {
  border-bottom: 1px solid var(--border-color);
}

.list-row:last-child {
  border-bottom: none;
}


:deep(.app-table),
:deep(.el-table) {
  box-shadow: var(--shadow-card);
}

.doc-status {
  border: none;

.list-row:hover {
  background: var(--bg-color-page);

}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: var(--text-color-primary);
}

.col-time {
  font-size: 13px;
  color: var(--text-color-regular);
}

.col-action {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.status-icon--ok {
  color: var(--status-completed-text);
}

.status-icon--fail {
  color: var(--status-failed-text);
}

.status-icon--proc {
  color: var(--color-primary);
  animation: doc-status-spin 1s linear infinite;
}

@keyframes doc-status-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.ghost-btn {
  border-radius: 16px;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  background: #fff;
}

.ghost-btn--danger {
  border-color: var(--status-failed-text);
  color: var(--status-failed-text);
}

.list-pagination {
  padding: 8px 16px 0;
}

.preview-meta {
  margin: 0;
}

.preview-meta__row {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.preview-meta__row:last-child {
  border-bottom: none;
}

.preview-meta__row dt {
  width: 72px;
  margin: 0;
  flex-shrink: 0;
  color: var(--text-color-secondary);
  font-size: 13px;
}

.preview-meta__row dd {
  margin: 0;
  font-size: 14px;
  color: var(--text-color-primary);
  word-break: break-all;
}

@media (max-width: 900px) {
  .stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .list-head,
  .list-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .col-action {
    justify-content: flex-start;
  }
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
