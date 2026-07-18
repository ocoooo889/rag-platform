<template>
  <div class="role-manage">
    <div class="page-header">
      <h2>角色管理</h2>
      <el-button type="primary" @click="openAddDialog">新增角色</el-button>
    </div>
    <el-table :data="roleList" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="角色名称" min-width="140">
        <template #default="{ row }">
          {{ roleDisplayName(row) }}
        </template>
      </el-table-column>
      <el-table-column label="权限" min-width="280">
        <template #default="{ row }">
          {{ getPermissionLabel(row.permissions) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button type="text" @click="openEditDialog(row)">编辑</el-button>
          <el-button type="text" danger @click="handleDelete(row)">删除</el-button>
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
          <el-input v-model="form.name" placeholder="请输入角色名称（如 admin / user）" />
        </el-form-item>
        <el-form-item prop="permPreset" label="权限标识">
          <el-select v-model="form.permPreset" placeholder="请选择权限" style="width: 100%">
            <el-option label="全部权限" value="all" />
            <el-option label="普通用户权限" value="user" />
            <el-option label="仅查看" value="view" />
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
import { roleCodeToLabel } from '@/utils/role'
import { ElMessage, ElMessageBox } from 'element-plus'

const formRef = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const roleList = ref([])

/** 权限码 → 中文 */
const PERM_LABELS = {
  '*': '全部权限',
  all: '全部权限',
  'kb:view': '查看知识库',
  'kb:edit': '编辑知识库',
  'doc:view': '查看文档',
  'doc:edit': '编辑文档',
  'chat:send': '智能问答',
  'rag:test': '命中测试',
  edit: '编辑权限',
  view: '查看权限'
}

const PRESET_PERMS = {
  all: ['*'],
  user: ['kb:view', 'doc:view', 'chat:send', 'rag:test'],
  view: ['kb:view', 'doc:view']
}

function roleDisplayName(row) {
  const code = row?.name || ''
  const label = roleCodeToLabel(code)
  return label !== code ? `${label}（${code}）` : code
}

function normalizePermList(value) {
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    const s = value.trim()
    if (!s) return []
    if (s.startsWith('[')) {
      try {
        const parsed = JSON.parse(s)
        return Array.isArray(parsed) ? parsed : [s]
      } catch {
        return [s]
      }
    }
    if (s.includes(',')) return s.split(',').map((x) => x.trim()).filter(Boolean)
    return [s]
  }
  return []
}

function getPermissionLabel(value) {
  const list = normalizePermList(value)
  if (!list.length) return '—'
  if (list.includes('*') || list.includes('all')) return '全部权限'
  return list.map((p) => PERM_LABELS[p] || p).join('、')
}

function inferPreset(permissions) {
  const list = normalizePermList(permissions)
  if (list.includes('*') || list.includes('all')) return 'all'
  const joined = [...list].sort().join(',')
  if (joined === [...PRESET_PERMS.user].sort().join(',')) return 'user'
  if (joined === [...PRESET_PERMS.view].sort().join(',')) return 'view'
  return 'user'
}

const form = reactive({
  id: null,
  name: '',
  permPreset: 'user'
})

const rules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  permPreset: [{ required: true, message: '请选择权限', trigger: 'change' }]
}

const fetchRoles = async () => {
  try {
    const data = await getRolesApi()
    roleList.value = Array.isArray(data) ? data : data?.items || []
  } catch (error) {
    console.error(error)
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.permPreset = 'user'
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.name = row.name
  form.permPreset = inferPreset(row.permissions)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  const permissions = PRESET_PERMS[form.permPreset] || PRESET_PERMS.user
  try {
    if (isEdit.value) {
      await updateRoleApi(form.id, { name: form.name, permissions })
      ElMessage.success('更新成功')
    } else {
      await createRoleApi({ name: form.name, permissions })
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
    await ElMessageBox.confirm(`确定删除角色「${roleDisplayName(row)}」？`, '提示', {
      type: 'warning'
    })
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
</style>
