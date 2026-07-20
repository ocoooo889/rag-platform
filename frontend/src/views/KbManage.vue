<template>
  <div class="kb-manage page-shell" v-loading="kbStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="openCreate">新建知识库</el-button>
    </div>

    <div class="page-body">
    <!-- 无知识库：统一空状态，并隐藏下游入口按钮 -->
    <EmptyState v-if="!kbStore.list.length && !kbStore.loading" type="kb" />

    <div v-else class="kb-card-list">
      <el-row :gutter="16">
        <el-col
          v-for="item in kbStore.list"
          :key="item.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <div
            class="kb-card"
            :class="{ 'kb-card--active': String(kbStore.selectedKbId) === String(item.id) }"
            @click="selectKb(item)"
          >
            <div class="kb-card__title">
              <span>{{ item.name }}</span>
            </div>
            <p class="kb-card__desc">{{ item.description || '暂无描述' }}</p>
            <div class="kb-card__meta">
              <!-- 后端字段 document_count；doc_count 为兼容别名 -->
              <span>文档总数：{{ item.document_count ?? item.doc_count ?? 0 }}</span>
              <span>分片总数：{{ item.chunk_count ?? 0 }}</span>
            </div>
            <div class="kb-card__index">
              <span class="kb-card__index-text" :title="indexSummary(item)">
                {{ indexSummary(item) }}
              </span>
              <el-tag v-if="!hasLocalIndex(item.id)" size="small" type="info" effect="plain">
                全局默认
              </el-tag>
              <el-tag v-else size="small" type="success" effect="plain">本地配置</el-tag>
            </div>
            <div class="kb-card__actions" @click.stop>
              <el-button text type="primary" @click="openIndexSettings(item)">索引配置</el-button>
              <el-button text @click="openEdit(item)">编辑</el-button>
              <el-button text type="danger" @click="openDelete(item)">删除</el-button>
            </div>
          </div>
        </el-col>
      </el-row>

      <AppPagination
        :total="kbStore.total"
        v-model:page="kbStore.page"
        v-model:page-size="kbStore.pageSize"
        @change="loadData"
      />
    </div>

    <!-- 新增 / 编辑弹窗：仅名称 + 描述 -->
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
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <ConfirmDialog
      v-model="deleteVisible"
      title="删除知识库"
      message="删除后文档、向量数据不可恢复，确认删除？"
      :loading="submitting"
      @confirm="confirmDelete"
    />

    <KbIndexSettingsDialog
      v-model="indexVisible"
      :kb-id="indexKb?.id || ''"
      :kb-name="indexKb?.name || ''"
      :api-index="indexApiMap[String(indexKb?.id || '')] || null"
      @saved="onIndexSaved"
      @rebuild="onIndexRebuild"
      @synced="onIndexSynced"
    />

    <RebuildProgressDialog
      v-model="rebuildVisible"
      :kb-id="indexKb?.id || ''"
      :kb-name="indexKb?.name || ''"
      :config="rebuildConfig"
      @done="onRebuildDone"
    />
    </div>
  </div>
</template>

<script setup>
import { defineAsyncComponent, onMounted, reactive, ref } from 'vue'
import { useKbStore } from '@/stores/kb'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { fetchKbIndexConfig } from '@/api/kbIndex'
import { formatKbIndexSummary, resolveKbIndexConfig } from '@/utils/kbIndex'
import { loadKbIndexConfig, removeKbIndexConfig } from '@/utils/localCache'

const KbIndexSettingsDialog = defineAsyncComponent(
  () => import('@/components/KbIndexSettingsDialog.vue')
)
const RebuildProgressDialog = defineAsyncComponent(
  () => import('@/components/RebuildProgressDialog.vue')
)

const kbStore = useKbStore()

const formVisible = ref(false)
const deleteVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const deletingId = ref(null)
const formRef = ref(null)

const indexVisible = ref(false)
const rebuildVisible = ref(false)
const indexKb = ref(null)
const rebuildConfig = ref(null)
/** 后端 GET 回写后的配置（按 kbId） */
const indexApiMap = reactive({})
/** 触发卡片索引摘要刷新 */
const indexTick = ref(0)

const form = reactive({
  name: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }]
}

function indexOf(kbId) {
  void indexTick.value
  const api = indexApiMap[String(kbId)]
  return resolveKbIndexConfig(kbId, api).config
}

function hasLocalIndex(kbId) {
  void indexTick.value
  try {
    return !!loadKbIndexConfig(kbId)
  } catch {
    return false
  }
}

function indexSummary(item) {
  try {
    return formatKbIndexSummary(indexOf(item?.id))
  } catch {
    return '索引配置暂不可用'
  }
}

/** 强制从后端拉取并覆盖本地缓存 */
async function syncIndexFromServer(kbId) {
  if (kbId == null || kbId === '') return null
  try {
    const cfg = await fetchKbIndexConfig(kbId)
    indexApiMap[String(kbId)] = cfg
    indexTick.value += 1
    return cfg
  } catch {
    return null
  }
}

async function syncListedIndexes() {
  const list = kbStore.list || []
  await Promise.all(list.map((kb) => syncIndexFromServer(kb.id)))
}

async function openIndexSettings(item) {
  indexKb.value = item
  indexVisible.value = true
  await syncIndexFromServer(item?.id)
}

function onIndexSaved(cfg) {
  if (indexKb.value?.id != null && cfg) {
    indexApiMap[String(indexKb.value.id)] = cfg
  }
  indexTick.value += 1
}

function onIndexSynced(cfg) {
  if (indexKb.value?.id != null && cfg) {
    indexApiMap[String(indexKb.value.id)] = cfg
  }
  indexTick.value += 1
}

function onIndexRebuild(cfg) {
  rebuildConfig.value = cfg
  rebuildVisible.value = true
  indexTick.value += 1
}

function onRebuildDone() {
  indexTick.value += 1
  loadData()
}

async function loadData() {
  try {
    await kbStore.loadList()
    // 列表就绪后强制拉各库索引配置（后端覆盖本地）
    await syncListedIndexes()
  } catch (e) {
    // 异常交由全局 axios 统一处理，页面仅维持 loading 状态
  }
}

async function selectKb(item) {
  kbStore.setSelectedKb(item.id)
  await syncIndexFromServer(item.id)
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
    const id = deletingId.value
    await kbStore.removeKb(id)
    try {
      removeKbIndexConfig(id)
    } catch {
      /* ignore */
    }
    indexTick.value += 1
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
  /* page-shell 由 admin.css 统一 */
}

.page-header {
  /* 标题样式由 admin.css 统一 */
}

.page-header h2 {
  /* 由 admin.css 统一 */
}

.kb-card {
  position: relative;
  min-height: 178px;
  margin-bottom: 18px;
  padding: 18px;
  overflow: hidden;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  background: transparent;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.kb-card:hover {
  transform: translateY(-3px);
}

.kb-card--active {
  /* 选中态交给指针邻近高亮，避免实色描边抢戏 */
}

.kb-card__title {
  position: relative;
  z-index: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
  line-height: 1.4;
  word-break: break-word;
}

.kb-card__desc {
  min-height: 40px;
  margin: 14px 0;
  color: var(--text-color-regular);
  line-height: 1.5;
}

.kb-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
  background: rgba(255, 255, 255, 0.04);
  border-radius: var(--radius-base);
}

.kb-card__index {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  min-width: 0;
}

.kb-card__index-text {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
