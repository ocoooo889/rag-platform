<template>
  <div class="kb-manage" v-loading="kbStore.loading" element-loading-text="加载中...">
    <!-- 顶栏：搜索 + 筛选 + 新建（对齐参考稿排版） -->
    <div class="kb-toolbar">
      <el-input
        v-model="searchKeyword"
        class="kb-toolbar__search"
        placeholder="请输入知识库名称"
        clearable
        :prefix-icon="Search"
      />
      <div class="kb-toolbar__filters">
        <button
          v-for="opt in filterOptions"
          :key="opt.value"
          type="button"
          class="filter-chip"
          :class="{ 'filter-chip--active': statusFilter === opt.value }"
          @click="statusFilter = opt.value"
        >
          <span class="filter-chip__box" />
          {{ opt.label }}
        </button>
      </div>
      <AppButton type="primary" class="kb-toolbar__create" text="新建知识库" @click="openCreate" />
    </div>

    <h2 class="kb-title">知识库管理</h2>

    <EmptyState v-if="!displayList.length && !kbStore.loading" type="kb" />

    <div v-else class="kb-list">
      <article
        v-for="item in displayList"
        :key="item.id"
        class="kb-row"
        :class="{ 'kb-row--active': String(kbStore.selectedKbId) === String(item.id) }"
        @click="selectKb(item)"
      >
        <div class="kb-row__icon">
          <el-icon :size="22"><Folder /></el-icon>
        </div>
        <div class="kb-row__body">
          <div class="kb-row__title">{{ item.name }}</div>
          <div class="kb-row__desc">{{ item.description || '暂无描述' }}</div>
        </div>
        <div class="kb-row__status">
          <span class="status-badge" :class="statusClass(item)">
            <el-icon v-if="kbStatus(item) === 'ready'" :size="14"><CircleCheck /></el-icon>
            <el-icon v-else :size="14"><Loading /></el-icon>
            {{ statusLabel(item) }}
          </span>
        </div>
        <div class="kb-row__actions" @click.stop>
          <AppButton type="primary" class="action-btn" text="查看" @click="viewKb(item)" />
          <AppButton type="primary" link text="编辑" @click="openEdit(item)" />
          <AppButton type="danger" link text="删除" @click="openDelete(item)" />
        </div>
      </article>

      <AppPagination
        class="kb-pagination"
        :total="kbStore.total"
        v-model:page="kbStore.page"
        v-model:page-size="kbStore.pageSize"
        @change="loadData"
      />
    </div>

    <el-dialog
      v-model="formVisible"
      :title="editingId ? '编辑知识库' : '新建知识库'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="50" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="200"
            placeholder="请输入描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <AppButton type="default" text="取消" @click="formVisible = false" />
        <AppButton
          type="primary"
          :loading="submitting"
          loading-mode="normal"
          text="保存"
          @click="submitForm"
        />
      </template>
    </el-dialog>

    <ConfirmDialog
      v-model="deleteVisible"
      title="删除知识库"
      message="删除后文档、向量数据不可恢复，确认删除？"
      :loading="submitting"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheck, Folder, Loading, Search } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import AppButton from '@/components/AppButton.vue'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const kbStore = useKbStore()
const router = useRouter()

const searchKeyword = ref('')
const statusFilter = ref('all')
const formVisible = ref(false)
const deleteVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const deletingId = ref(null)
const formRef = ref(null)

const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '已就绪', value: 'ready' },
  { label: '解析中', value: 'processing' }
]

const form = reactive({
  name: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }]
}

/** 当前页列表 + 搜索/筛选（仅排版层过滤，不改接口） */
const displayList = computed(() => {
  let rows = kbStore.list || []
  const kw = searchKeyword.value.trim().toLowerCase()
  if (kw) {
    rows = rows.filter((item) => String(item.name || '').toLowerCase().includes(kw))
  }
  if (statusFilter.value === 'ready') {
    rows = rows.filter((item) => kbStatus(item) === 'ready')
  } else if (statusFilter.value === 'processing') {
    rows = rows.filter((item) => kbStatus(item) === 'processing')
  }
  return rows
})

function docCount(item) {
  return Number(item.document_count ?? item.doc_count ?? 0)
}

function kbStatus(item) {
  return docCount(item) > 0 ? 'ready' : 'processing'
}

function statusLabel(item) {
  return kbStatus(item) === 'ready' ? '已就绪' : '解析中'
}

function statusClass(item) {
  return kbStatus(item) === 'ready' ? 'status-badge--ready' : 'status-badge--processing'
}

async function loadData() {
  try {
    await kbStore.loadList()
  } catch (e) {
    // 全局 axios 处理
  }
}

function selectKb(item) {
  kbStore.setSelectedKb(item.id)
}

function viewKb(item) {
  kbStore.setSelectedKb(item.id)
  router.push('/documents')
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.description = ''
  formVisible.value = true
}

function openEdit(item) {
  editingId.value = item.id
  form.name = item.name
  form.description = item.description || ''
  formVisible.value = true
}

function openDelete(item) {
  deletingId.value = item.id
  deleteVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await kbStore.updateKb(editingId.value, {
        name: form.name,
        description: form.description
      })
    } else {
      await kbStore.createKb({
        name: form.name,
        description: form.description
      })
    }
    formVisible.value = false
  } catch (e) {
    // 全局拦截已弹窗
  } finally {
    submitting.value = false
  }
}

async function confirmDelete() {
  if (!deletingId.value) return
  submitting.value = true
  try {
    await kbStore.removeKb(deletingId.value)
    deleteVisible.value = false
  } catch (e) {
    // 全局拦截已弹窗
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.kb-manage {

  padding: 4px 0;

  min-height: 100%;
  padding: 8px 4px 24px;
  background: var(--bg-color-page);
}

.kb-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.kb-toolbar__search {
  flex: 1;
  min-width: 220px;
  max-width: 360px;
}

.kb-toolbar__search :deep(.el-input__wrapper) {
  border-radius: 20px;
  box-shadow: 0 0 0 1px var(--border-color) inset;

}

.kb-toolbar__filters {
  display: flex;
  align-items: center;

  justify-content: space-between;
  margin-bottom: 20px;
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

.kb-card {
  position: relative;
  min-height: 178px;
  margin-bottom: 18px;
  padding: 18px;
  overflow: hidden;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);

  gap: 20px;
  flex-wrap: wrap;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-color-regular);
  cursor: pointer;
}

.filter-chip__box {
  width: 14px;
  height: 14px;
  border: 1px solid #c0c4cc;
  border-radius: 2px;
  background: #fff;
}

.filter-chip--active {
  color: var(--color-primary);
  font-weight: 500;
}

.filter-chip--active .filter-chip__box {
  border-color: var(--color-primary);
  background: var(--color-primary);
  box-shadow: inset 0 0 0 2px #fff;
}

.kb-toolbar__create {
  margin-left: auto;
}

.kb-toolbar__create :deep(.el-button) {
  border-radius: 20px;
  padding: 10px 22px;
}

.kb-title {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kb-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;

  background: var(--bg-color-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;

  box-shadow: var(--shadow-card);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.kb-card::after {
  position: absolute;
  right: -32px;
  top: -32px;
  width: 96px;
  height: 96px;
  content: '';
  background: radial-gradient(circle, rgba(74, 122, 255, 0.16), rgba(74, 122, 255, 0));
  pointer-events: none;
}

.kb-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-color-primary);
  box-shadow: var(--shadow-card-hover);

  transition: border-color 0.2s, box-shadow 0.2s;
}

.kb-row:hover {
  border-color: #c6e2ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.08);

}

.kb-row--active {
  border-color: var(--color-primary);

  box-shadow: 0 0 0 1px rgba(74, 122, 255, 0.16) inset, var(--shadow-card-hover);

  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.2);

}

.kb-row__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;

  justify-content: space-between;
  gap: 8px;
  font-size: 16px;

  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--bg-color-hover);
  color: var(--color-primary);
}

.kb-row__body {
  flex: 1;
  min-width: 0;
}

.kb-row__title {
  font-size: 15px;

  font-weight: 600;
  color: var(--text-color-primary);
  margin-bottom: 4px;
}


.kb-card__desc {
  min-height: 40px;
  margin: 14px 0;
  color: var(--text-color-regular);

.kb-row__desc {
  font-size: 13px;
  color: var(--text-color-secondary);

  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}


.kb-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
  background: #f8fbff;
  border-radius: var(--radius-base);

.kb-row__status {
  flex-shrink: 0;
  min-width: 88px;
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;

}

.status-badge--ready {
  color: var(--status-completed-text);
}

.status-badge--processing {
  color: #e6a23c;
}

.kb-row__actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;

  margin-top: 12px;

}

.action-btn :deep(.el-button) {
  border-radius: 18px;
  padding: 8px 20px;
}

.kb-pagination {
  margin-top: 8px;

}
</style>
