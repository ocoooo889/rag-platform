<template>
  <div class="doc-manage" v-loading="docStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>文档管理</h2>
      <!-- 无知识库时隐藏上传入口 -->
      <el-tag v-if="envLabel" type="info" size="small">{{ envLabel }}</el-tag>
    </div>

    <!-- 顶部知识库级联筛选：切换后自动隔离无关文档 -->
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
    </div>

    <!-- 无知识库：隐藏上传区 -->
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

      <AppTable v-else-if="selectedKbId" :data="docStore.list" :loading="docStore.loading">
        <el-table-column prop="file_name" label="文件名" min-width="160" />
        <el-table-column prop="file_type" label="文件类型" width="100" />
        <el-table-column label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分片数量" width="100" />
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at, 'datetime') }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :class="statusClass(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="环境" width="140">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.env_label || row.env || envTag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <!-- 仅单条删除，无批量操作 / 导出按钮 -->
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
      title="删除文档"
      message="确认删除该文档？删除后向量数据不可恢复。"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { formatFileSize, formatDate } from '@/utils/format'
import { getEnvTag } from '@/utils/request'
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

const hasKb = computed(() => kbStore.list.length > 0)
const envLabel = computed(() => {
  const first = docStore.list[0]
  return first?.env_label || (hasKb.value ? envTag : '')
})

const STATUS_MAP = {
  pending: '待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败'
}

function statusLabel(status) {
  return STATUS_MAP[status] || status
}

/** 状态色使用全局 CSS 变量 class，禁止硬编码色值 */
function statusClass(status) {
  return `doc-status doc-status--${status || 'pending'}`
}

async function loadKb() {
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (kbStore.selectedKbId) {
      selectedKbId.value = kbStore.selectedKbId
      await reloadDocs()
    }
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
  await reloadDocs()
}

async function onUploadSuccess() {
  // 上传完成自动刷新列表同步最新状态
  await reloadDocs()
  uploadProgress.value = 0
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
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  color: var(--text-color-primary);
}

.filter-bar {
  margin-bottom: 16px;
}

.upload-area {
  margin-bottom: 20px;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

/* 文档状态标签：颜色全部走全局 CSS 变量 */
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
</style>
