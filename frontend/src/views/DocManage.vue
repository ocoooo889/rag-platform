<template>
  <div class="doc-manage" v-loading="docStore.loading" element-loading-text="加载中...">
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

        <!-- 文档列表卡片 -->
        <section class="list-card">
          <EmptyState
            v-if="!filteredList.length && !docStore.loading"
            type="doc"
            tip="暂无文档，请点击右上角上传"
          />

          <template v-else>
            <div class="list-head">
              <span class="col-name">文档名称</span>
              <span class="col-time">上传时间</span>
              <span class="col-action">操作</span>
            </div>

            <ul class="list-body">
              <li v-for="row in filteredList" :key="row.id" class="list-row">
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
              v-if="docStore.total > 0"
              class="list-pagination"
              :total="docStore.total"
              v-model:page="docStore.page"
              v-model:page-size="docStore.pageSize"
              @change="reloadDocs"
            />
          </template>
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
      title="删除文档"
      message="确认删除该文档？删除后向量数据不可恢复。"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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
  await reloadDocs()
}

async function onUploadSuccess() {
  await reloadDocs()
  uploadProgress.value = 0
  uploadVisible.value = false
}

function onUploadFail() {
  uploadProgress.value = 0
}

function openDelete(row) {
  deletingId.value = row.id
  deleteVisible.value = true
}

async function confirmDelete() {
  if (!deletingId.value) return
  deleting.value = true
  try {
    await docStore.remove(deletingId.value)
    deleteVisible.value = false
    await reloadDocs()
  } catch (e) {
    // 全局 axios 处理
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadKb()
})
</script>

<style scoped>
.doc-manage {
  min-height: 100%;
  padding: 8px 4px 24px;
  background: var(--bg-color-page);
}

.doc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.doc-top__title {
  margin: 0;
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
  grid-template-columns: minmax(0, 2fr) minmax(140px, 1fr) minmax(200px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px 20px;
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
</style>
