<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon kb-icon">
            <el-icon size="32" color="#fff"><Folder /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.kb_count }}</div>
            <div class="stat-label">知识库数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon doc-icon">
            <el-icon size="32" color="#fff"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.doc_count }}</div>
            <div class="stat-label">文档数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon user-icon">
            <el-icon size="32" color="#fff"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.user_count }}</div>
            <div class="stat-label">用户数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon group-icon">
            <el-icon size="32" color="#fff"><UserFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.group_count }}</div>
            <div class="stat-label">用户组数量</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">知识库概览</span>
              <el-button type="text" @click="goTo('/knowledge-bases')">查看全部</el-button>
            </div>
          </template>
          <div class="kb-list">
            <div v-for="kb in kbList" :key="kb.id" class="kb-item">
              <div class="kb-icon-wrapper">
                <el-icon size="24" color="#667eea"><Folder /></el-icon>
              </div>
              <div class="kb-info">
                <div class="kb-name">{{ kb.name }}</div>
                <div class="kb-meta">{{ kb.document_count }} 个文档 · {{ kb.chunk_count }} 个片段</div>
              </div>
              <div class="kb-date">{{ formatDate(kb.created_at) }}</div>
            </div>
            <div v-if="kbList.length === 0" class="empty-state">
              <el-icon size="48" color="#ccc"><Folder /></el-icon>
              <p>暂无知识库</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <span class="card-title">系统状态</span>
          </template>
          <div class="system-status">
            <div class="status-item">
              <div class="status-dot online"></div>
              <span>后端服务</span>
              <span class="status-text">运行中</span>
            </div>
            <div class="status-item">
              <div class="status-dot online"></div>
              <span>数据库</span>
              <span class="status-text">正常</span>
            </div>
            <div class="status-item">
              <div class="status-dot online"></div>
              <span>Chroma 向量库</span>
              <span class="status-text">运行中</span>
            </div>
            <div class="status-item">
              <div class="status-dot online"></div>
              <span>API 服务</span>
              <span class="status-text">正常</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card class="section-card">
          <template #header>
            <span class="card-title">快速操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="goTo('/knowledge-bases')" class="action-btn">
              <el-icon><Folder /></el-icon>
              <span>新建知识库</span>
            </el-button>
            <el-button type="primary" @click="goTo('/documents')" class="action-btn">
              <el-icon><Upload /></el-icon>
              <span>上传文档</span>
            </el-button>
            <el-button type="primary" @click="goTo('/chat')" class="action-btn">
              <el-icon><ChatDotRound /></el-icon>
              <span>智能对话</span>
            </el-button>
            <el-button type="primary" @click="goTo('/hit-test')" class="action-btn">
              <el-icon><Search /></el-icon>
              <span>命中率测试</span>
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStatsApi } from '@/api/dashboard'
import { fetchKnowledgeBases } from '@/api/kb'
import { Folder, Document, User, UserFilled, Upload, ChatDotRound, Search } from '@element-plus/icons-vue'

const router = useRouter()
const stats = ref({
  kb_count: 0,
  doc_count: 0,
  user_count: 0,
  group_count: 0
})
const kbList = ref([])

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return dateStr.substring(0, 10)
}

const goTo = (path) => {
  router.push(path)
}

onMounted(async () => {
  try {
    const data = await getStatsApi()
    stats.value = {
      kb_count: data.kb_count ?? 0,
      doc_count: data.doc_count ?? 0,
      user_count: data.user_count ?? 0,
      group_count: data.group_count ?? 0
    }
  } catch (error) {
    console.error(error)
  }

  try {
    const kbs = await fetchKnowledgeBases({ page: 1, page_size: 5 })
    kbList.value = kbs?.items || []
  } catch (error) {
    console.error(error)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 10px 0;
}
.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  margin-right: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kb-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.doc-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
.user-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}
.group-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}
.stat-info {
  flex: 1;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
.section-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
.kb-list {
  margin-top: 10px;
}
.kb-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f2f6fc;
}
.kb-item:last-child {
  border-bottom: none;
}
.kb-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}
.kb-info {
  flex: 1;
}
.kb-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
.kb-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.kb-date {
  font-size: 12px;
  color: #909399;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: #909399;
}
.empty-state p {
  margin-top: 10px;
  font-size: 14px;
}
.system-status {
  margin-top: 10px;
}
.status-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f2f6fc;
}
.status-item:last-child {
  border-bottom: none;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 12px;
}
.status-dot.online {
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.4);
}
.status-dot.offline {
  background: #f56c6c;
}
.status-text {
  margin-left: auto;
  font-size: 12px;
  color: #67c23a;
}
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 10px;
}
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  border-radius: 8px;
}
</style>