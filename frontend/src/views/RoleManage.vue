<template>
  <div class="role-manage">
    <div class="page-header">
      <h2>角色管理</h2>
      <el-button type="primary" @click="openAddDialog">新增角色</el-button>
    </div>
    <el-table :data="roleList" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="角色名称" />
      <el-table-column prop="permissions" label="权限">
        <template #default="scope">
          {{ getPermissionLabel(scope.row.permissions) }}
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button type="text" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button type="text" danger @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑角色' : '新增角色'" 
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="name" label="角色名称">
          <el-input v-model="form.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item prop="permissions" label="权限标识">
          <el-select v-model="form.permissions" placeholder="请选择权限">
            <el-option label="全部权限" value="all" />
            <el-option label="编辑权限" value="edit" />
            <el-option label="查看权限" value="view" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getRolesApi, createRoleApi, updateRoleApi, deleteRoleApi } from '@/api/roles'
import { ElMessage, ElMessageBox } from 'element-plus'

const formRef = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const roleList = ref([])

const permissionMap = {
  'all': '全部权限',
  'edit': '编辑权限',
  'view': '查看权限'
}

const getPermissionLabel = (value) => {
  return permissionMap[value] || value
}

const form = reactive({
  id: null,
  name: '',
  permissions: '',
})

const rules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  permissions: [{ required: true, message: '请选择权限', trigger: 'change' }],
}

const fetchRoles = async () => {
  try {
    const data = await getRolesApi()
    roleList.value = data
  } catch (error) {
    console.error(error)
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.permissions = ''
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.name = row.name
  form.permissions = row.permissions || ''
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      await updateRoleApi(form.id, { name: form.name, permissions: form.permissions })
      ElMessage.success('更新成功')
    } else {
      await createRoleApi({ name: form.name, permissions: form.permissions })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchRoles()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除角色"${row.name}"？`, '提示', { type: 'warning' })
    await deleteRoleApi(row.id)
    ElMessage.success('删除成功')
    fetchRoles()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchRoles()
})
</script>

<style scoped>
.role-manage {
  padding: 10px 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
}
.permission-hint {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}
</style>