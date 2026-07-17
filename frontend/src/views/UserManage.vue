<template>
  <div class="user-manage">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openAddDialog">新增用户</el-button>
    </div>
    <div class="search-bar">
      <el-input v-model="searchKeyword" placeholder="请输入用户名搜索" clearable style="width: 300px" @keyup.enter="fetchUsers">
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
    <el-table :data="userList" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="显示名" />
      <el-table-column prop="role_id" label="角色" :formatter="formatRole" />
      <el-table-column prop="status" label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.status === '启用' ? 'success' : 'danger'">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作">
        <template #default="scope">
          <el-button type="text" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button type="text" danger @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username" label="用户名">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item prop="password" v-if="!isEdit" label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item prop="display_name" label="显示名">
          <el-input v-model="form.display_name" placeholder="请输入显示名" />
        </el-form-item>
        <el-form-item prop="role_id" label="角色">
          <el-select v-model="form.role_id" placeholder="请选择角色">
            <el-option v-for="role in roleList" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item prop="status" label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="启用" value="启用" />
            <el-option label="已停用" value="已停用" />
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
import { Search } from '@element-plus/icons-vue'
import { getUsersApi, createUserApi, updateUserApi, deleteUserApi } from '@/api/users'
import { getRolesApi } from '@/api/roles'
import { ElMessage, ElMessageBox } from 'element-plus'

const formRef = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const userList = ref([])
const roleList = ref([])
const searchKeyword = ref('')

const form = reactive({
  id: null,
  username: '',
  password: '',
  display_name: '',
  role_id: null,
  status: '启用',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const formatRole = (row) => {
  const role = roleList.value.find(r => r.id === row.role_id)
  return role ? role.name : row.role_id
}

const fetchUsers = async () => {
  try {
    const params = searchKeyword.value ? { keyword: searchKeyword.value } : {}
    const data = await getUsersApi(params)
    userList.value = data
  } catch (error) {
    console.error(error)
  }
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
  form.username = ''
  form.password = ''
  form.display_name = ''
  form.role_id = null
  form.status = '启用'
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.username = row.username
  form.display_name = row.display_name
  form.role_id = row.role_id
  form.status = row.status
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      const { id, username, password, ...updateData } = form
      await updateUserApi(id, updateData)
      ElMessage.success('更新成功')
    } else {
      await createUserApi(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户"${row.username}"？`, '提示', { type: 'warning' })
    await deleteUserApi(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>

<style scoped>
.user-manage {
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
.search-bar {
  margin-bottom: 20px;
}
</style>