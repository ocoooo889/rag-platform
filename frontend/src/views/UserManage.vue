<template>
  <div class="user-manage page-shell">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openAddDialog">新增用户</el-button>
    </div>
    <div class="page-body">
    <div class="search-bar">
      <el-input v-model="searchKeyword" placeholder="请输入账号搜索" clearable style="width: 300px" @keyup.enter="fetchUsers">
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
    <el-table
      v-equal-table
      :data="userList"
      border
      table-layout="fixed"
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" align="center" class-name="col-id" show-overflow-tooltip />
      <el-table-column prop="username" label="账号" show-overflow-tooltip />
      <el-table-column prop="display_name" label="用户名" show-overflow-tooltip />
      <el-table-column prop="role_id" label="角色" :formatter="formatRole" show-overflow-tooltip />
      <el-table-column label="授权知识库" show-overflow-tooltip>
        <template #default="scope">
          <span v-if="!(scope.row.kb_ids || []).length" class="kb-empty">未授权</span>
          <el-tag
            v-for="kid in (scope.row.kb_ids || []).slice(0, 2)"
            :key="kid"
            size="small"
            class="kb-tag"
          >
            {{ kbName(kid) }}
          </el-tag>
          <el-tag v-if="(scope.row.kb_ids || []).length > 2" size="small" type="info">
            +{{ scope.row.kb_ids.length - 2 }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.status === '启用' ? 'success' : 'danger'">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" show-overflow-tooltip>
        <template #default="scope">
          {{ formatDate(scope.row.created_at, 'YYYY/MM/DD') }}
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button text @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="520px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" class="user-form">
        <el-form-item prop="username" :label="spacedLabel('账号')">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item prop="password" v-if="!isEdit" :label="spacedLabel('密码')">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item prop="display_name" :label="spacedLabel('用户名')">
          <el-input v-model="form.display_name" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item prop="role_id" :label="spacedLabel('角色')">
          <el-select v-model="form.role_id" placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roleList" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item prop="status" :label="spacedLabel('状态')">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="启用" value="启用" />
            <el-option label="已停用" value="已停用" />
          </el-select>
        </el-form-item>
        <el-form-item :label="spacedLabel('授权知识库')">
          <el-select
            v-model="form.kb_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="选择该用户可访问的知识库"
            style="width: 100%"
          >
            <el-option
              v-for="kb in kbList"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
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
import { Search } from '@element-plus/icons-vue'
import { getUsersApi, createUserApi, updateUserApi, deleteUserApi } from '@/api/users'
import { getRolesApi } from '@/api/roles'
import { fetchKnowledgeBases } from '@/api/kb'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/format'

const formRef = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const userList = ref([])
const roleList = ref([])
const kbList = ref([])
const searchKeyword = ref('')

const form = reactive({
  id: null,
  username: '',
  password: '',
  display_name: '',
  role_id: null,
  status: '启用',
  kb_ids: []
})

/** 短标签字间插全角空格，与三字等宽；四字及以上不插空，仅右对齐 */
function spacedLabel(text, targetLen = 3) {
  const chars = Array.from(text)
  if (chars.length >= targetLen || chars.length <= 1) return text
  const gaps = chars.length - 1
  const totalSpaces = targetLen - chars.length
  const base = Math.floor(totalSpaces / gaps)
  let extra = totalSpaces % gaps
  let out = ''
  for (let i = 0; i < chars.length; i++) {
    out += chars[i]
    if (i < gaps) {
      const n = base + (extra > 0 ? 1 : 0)
      if (extra > 0) extra -= 1
      out += '\u3000'.repeat(n)
    }
  }
  return out
}

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const formatRole = (row) => {
  const role = roleList.value.find((r) => r.id === row.role_id)
  return role ? role.name : row.role_id
}

const kbName = (id) => {
  const kb = kbList.value.find((k) => k.id === id)
  return kb?.name || id
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

const fetchKbs = async () => {
  try {
    const res = await fetchKnowledgeBases({ page: 1, page_size: 1000 })
    const raw = res?.data
    kbList.value = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
  } catch (error) {
    console.error(error)
    kbList.value = []
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
  form.kb_ids = []
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.username = row.username
  form.display_name = row.display_name
  form.role_id = row.role_id
  form.status = row.status
  form.kb_ids = [...(row.kb_ids || [])]
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      const { id, username, password, ...updateData } = form
      await updateUserApi(id, {
        display_name: updateData.display_name,
        role_id: updateData.role_id,
        status: updateData.status,
        kb_ids: updateData.kb_ids || []
      })
      ElMessage.success('更新成功')
    } else {
      await createUserApi({
        username: form.username,
        password: form.password,
        display_name: form.display_name,
        role_id: form.role_id,
        status: form.status,
        kb_ids: form.kb_ids || []
      })
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
  fetchKbs()
})
</script>

<style scoped>
.user-manage {
  /* page-shell 由 admin.css 统一 */
}
.search-bar {
  margin-bottom: 16px;
}
.kb-empty {
  color: var(--admin-text-dim, rgba(160, 170, 190, 0.42));
  font-size: 12px;
}
.kb-tag {
  margin-right: 4px;
}
</style>
