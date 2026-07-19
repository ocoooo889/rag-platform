<template>
  <div class="user-group-manage page-shell">
    <div class="page-header">
      <h2>用户组管理</h2>
      <el-button type="primary" @click="openAddDialog">新增用户组</el-button>
    </div>
    <div class="page-body">
    <el-table
      class="table-cols-auto"
      :data="groupList"
      border
      table-layout="auto"
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="72" align="center" class-name="col-id" />
      <el-table-column prop="name" label="用户组名称" min-width="120" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="member_count" label="成员数" width="88" />
      <el-table-column prop="kb_count" label="授权知识库数" width="120" />
      <el-table-column label="创建时间" width="120">
        <template #default="{ row }">
          {{ formatDate(row.created_at, 'YYYY/MM/DD') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="320">
        <template #default="scope">
          <el-button text @click="openMembersDialog(scope.row)">成员管理</el-button>
          <el-button text @click="openKbAccessDialog(scope.row)">知识库授权</el-button>
          <el-button text @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑用户组' : '新增用户组'" 
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="name" label="用户组名称">
          <el-input v-model="form.name" placeholder="请输入用户组名称" />
        </el-form-item>
        <el-form-item prop="description" label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="请输入用户组描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="membersDialogVisible" 
      title="成员管理" 
      width="720px"
      class="transfer-dialog"
      :close-on-click-modal="false"
    >
      <div class="transfer-dialog__body">
        <el-transfer
          v-model="selectedMembers"
          :data="userList"
          :titles="['可选用户', '已选成员']"
          :button-texts="['移除', '添加']"
          :format="{
            noChecked: '${total}',
            hasChecked: '${checked}/${total}'
          }"
          :props="{
            key: 'id',
            label: 'username',
            disabled: 'disabled'
          }"
        />
      </div>
      <template #footer>
        <el-button @click="membersDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveMembers">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="kbAccessDialogVisible" 
      title="知识库授权" 
      width="720px"
      class="transfer-dialog"
      :close-on-click-modal="false"
    >
      <div class="transfer-dialog__body">
        <el-transfer
          v-model="selectedKbs"
          :data="kbList"
          :titles="['可选知识库', '已授权知识库']"
          :button-texts="['取消授权', '授权']"
          :format="{
            noChecked: '${total}',
            hasChecked: '${checked}/${total}'
          }"
          :props="{
            key: 'id',
            label: 'name',
            disabled: 'disabled'
          }"
        />
      </div>
      <template #footer>
        <el-button @click="kbAccessDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveKbAccess">确定</el-button>
      </template>
    </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  getUserGroupsApi,
  createUserGroupApi,
  updateUserGroupApi,
  deleteUserGroupApi,
  updateGroupMembersApi,
  updateGroupKbAccessApi
} from '@/api/userGroups'
import { getUsersApi } from '@/api/users'
import { fetchKnowledgeBases } from '@/api/kb'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/format'

const formRef = ref(null)
const dialogVisible = ref(false)
const membersDialogVisible = ref(false)
const kbAccessDialogVisible = ref(false)
const isEdit = ref(false)
const groupList = ref([])
const userList = ref([])
const kbList = ref([])
const selectedMembers = ref([])
const selectedKbs = ref([])
const currentGroup = ref(null)

const form = reactive({
  id: null,
  name: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入用户组名称', trigger: 'blur' }]
}

const fetchGroups = async () => {
  try {
    const data = await getUserGroupsApi()
    groupList.value = data
  } catch (error) {
    console.error(error)
  }
}

const fetchUsers = async () => {
  try {
    const data = await getUsersApi()
    const list = Array.isArray(data) ? data : data?.items || []
    userList.value = list.map((u) => ({
      id: u.id,
      username: u.display_name || u.username,
      disabled: false
    }))
  } catch (error) {
    console.error(error)
  }
}

const fetchKbs = async () => {
  try {
    const res = await fetchKnowledgeBases({ page: 1, page_size: 1000 })
    const raw = res?.data
    const list = Array.isArray(raw) ? raw : raw?.items || []
    kbList.value = list.map((kb) => ({
      id: kb.id,
      name: kb.name,
      disabled: false
    }))
  } catch (error) {
    console.error(error)
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.id = row.id
  form.name = row.name
  form.description = row.description || ''
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      await updateUserGroupApi(form.id, { name: form.name, description: form.description })
      ElMessage.success('更新成功')
    } else {
      await createUserGroupApi({ name: form.name, description: form.description })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchGroups()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户组"${row.name}"？`, '提示', { type: 'warning' })
    await deleteUserGroupApi(row.id)
    ElMessage.success('删除成功')
    fetchGroups()
  } catch (error) {
    console.error(error)
  }
}

const openMembersDialog = (row) => {
  currentGroup.value = row
  selectedMembers.value = [...(row.member_ids || [])]
  membersDialogVisible.value = true
}

const handleSaveMembers = async () => {
  if (!currentGroup.value) return
  try {
    await updateGroupMembersApi(currentGroup.value.id, selectedMembers.value)
    ElMessage.success('成员更新成功')
    membersDialogVisible.value = false
    fetchGroups()
  } catch (error) {
    console.error(error)
  }
}

const openKbAccessDialog = (row) => {
  currentGroup.value = row
  selectedKbs.value = [...(row.kb_ids || [])]
  kbAccessDialogVisible.value = true
}

const handleSaveKbAccess = async () => {
  if (!currentGroup.value) return
  try {
    await updateGroupKbAccessApi(currentGroup.value.id, selectedKbs.value)
    ElMessage.success('知识库授权成功')
    kbAccessDialogVisible.value = false
    fetchGroups()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchGroups()
  fetchUsers()
  fetchKbs()
})
</script>

<style scoped>
.user-group-manage {
  /* page-shell 由 admin.css 统一 */
}

.transfer-dialog__body {
  display: flex;
  justify-content: center;
  padding: 4px 0 8px;
  overflow-x: auto;
}

.transfer-dialog__body :deep(.el-transfer) {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: max-content;
  max-width: 100%;
}

.transfer-dialog__body :deep(.el-transfer-panel) {
  flex: 0 0 240px;
  width: 240px;
}

.transfer-dialog__body :deep(.el-transfer__buttons) {
  display: flex !important;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 4px;
}

.transfer-dialog__body :deep(.el-transfer__button) {
  margin: 0 !important;
}
</style>