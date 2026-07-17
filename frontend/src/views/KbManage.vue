<template>
  <div class="kb-manage" v-loading="kbStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>知识库管理</h2>
      <AppButton type="primary" text="新建知识库" @click="openCreate" />
    </div>

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
              <el-tag size="small" type="info">{{ item.env_label || item.env || envTag }}</el-tag>
            </div>
            <p class="kb-card__desc">{{ item.description || '暂无描述' }}</p>
            <div class="kb-card__meta">
              <span>文档总数：{{ item.doc_count ?? 0 }}</span>
              <span>分片总数：{{ item.chunk_count ?? 0 }}</span>
            </div>
            <div class="kb-card__actions" @click.stop>
              <AppButton type="primary" text="编辑" link @click="openEdit(item)" />
              <AppButton type="danger" text="删除" link @click="openDelete(item)" />
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
import { onMounted, reactive, ref } from 'vue'
import { useKbStore } from '@/stores/kb'
import { getEnvTag } from '@/utils/request'
import AppButton from '@/components/AppButton.vue'
import AppPagination from '@/components/AppPagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const kbStore = useKbStore()
const envTag = getEnvTag()

const formVisible = ref(false)
const deleteVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const deletingId = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }]
}

async function loadData() {
  try {
    await kbStore.loadList()
  } catch (e) {
    // 异常交由全局 axios 统一处理，页面仅维持 loading 状态
  }
}

function selectKb(item) {
  kbStore.setSelectedKb(item.id)
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

.kb-card {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-color-card);
  cursor: pointer;
  transition: border-color 0.2s;
}

.kb-card:hover {
  border-color: var(--color-primary);
}

.kb-card--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.kb-card__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.kb-card__desc {
  min-height: 40px;
  margin: 10px 0;
  color: var(--text-color-regular);
  line-height: 1.5;
}

.kb-card__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.kb-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
