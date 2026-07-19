<template>
  <div class="model-manage page-shell">
    <div class="page-header">
      <h2>大模型管理</h2>
      <el-button type="primary" @click="openAddDialog">新增模型配置</el-button>
    </div>
    <div class="page-body">
    <el-table
      v-equal-table
      :data="modelList"
      border
      table-layout="fixed"
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" align="center" class-name="col-id" show-overflow-tooltip />
      <el-table-column prop="model_type" label="模型类型" :formatter="formatType" show-overflow-tooltip />
      <el-table-column prop="model_name" label="模型名称" show-overflow-tooltip />
      <el-table-column prop="api_base_url" label="API地址" show-overflow-tooltip />
      <el-table-column prop="dimension" label="向量维度" show-overflow-tooltip />
      <el-table-column prop="is_active" label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button text @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑模型配置' : '新增模型配置'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="model_type" label="模型类型">
          <el-select v-model="form.model_type" placeholder="请选择模型类型">
            <el-option label="聊天模型" value="chat" />
            <el-option label="嵌入模型" value="embedding" />
          </el-select>
        </el-form-item>
        <el-form-item prop="model_name" label="模型名称">
          <el-input v-model="form.model_name" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item prop="api_base_url" label="API地址">
          <el-input v-model="form.api_base_url" placeholder="请输入API地址" />
        </el-form-item>
        <el-form-item prop="dimension" label="向量维度">
          <div class="dimension-field">
            <el-select
              v-model="form.dimension"
              class="dimension-select"
              placeholder="请选择标准维度"
              style="width: 200px"
              popper-class="dimension-select-dropdown"
            >
              <el-option
                v-for="dim in DIMENSION_OPTIONS"
                :key="dim"
                :label="String(dim)"
                :value="dim"
              />
            </el-select>
            <span class="dimension-hint">数值越高能承载的语义细节越多。</span>
          </div>
        </el-form-item>
        <el-form-item prop="is_active" label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getModelsApi, createModelApi, updateModelApi, deleteModelApi } from '@/api/models'
import { ElMessage, ElMessageBox } from 'element-plus'

const formRef = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const modelList = ref([])

/** 向量维度仅允许标准档位，禁止随意填数 */
const DIMENSION_OPTIONS = [384, 768, 1024, 1536]

const form = reactive({
  id: null,
  model_type: '',
  model_name: '',
  api_base_url: '',
  dimension: null,
  is_active: true,
})

const rules = {
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  api_base_url: [{ required: true, message: '请输入API地址', trigger: 'blur' }],
  dimension: [{ required: true, message: '请选择向量维度', trigger: 'change' }],
}

const formatType = (row) => {
  return row.model_type === 'chat' ? '聊天模型' : '嵌入模型'
}

const fetchModels = async () => {
  try {
    const data = await getModelsApi()
    modelList.value = data
  } catch (error) {
    console.error(error)
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.id = null
  form.model_type = ''
  form.model_name = ''
  form.api_base_url = ''
  form.dimension = null
  form.is_active = true
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.model_type = row.model_type
  form.model_name = row.model_name
  form.api_base_url = row.api_base_url
  const dim = Number(row.dimension)
  form.dimension = DIMENSION_OPTIONS.includes(dim) ? dim : null
  form.is_active = row.is_active
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      const { id, ...updateData } = form
      await updateModelApi(id, updateData)
      ElMessage.success('更新成功')
    } else {
      await createModelApi(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchModels()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除模型配置"${row.model_name}"？`, '提示', { type: 'warning' })
    await deleteModelApi(row.id)
    ElMessage.success('删除成功')
    fetchModels()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.model-manage {
  /* page-shell 由 admin.css 统一 */
}

.dimension-field {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.dimension-hint {
  font-size: 12px;
  line-height: 1.4;
  color: var(--admin-text-muted, rgba(200, 205, 220, 0.58));
}

.dimension-select :deep(.el-select__wrapper) {
  justify-content: center;
}

.dimension-select :deep(.el-select__selection),
.dimension-select :deep(.el-select__placeholder),
.dimension-select :deep(.el-select__selected-item) {
  text-align: center;
  justify-content: center;
}
</style>

<!-- 下拉层 teleport 到 body，需非 scoped -->
<style>
.dimension-select-dropdown .el-select-dropdown__item {
  text-align: center;
  justify-content: center;
}
</style>