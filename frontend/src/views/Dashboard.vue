<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon kb-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.kb_count }}</div>
            <div class="stat-label">知识库数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon doc-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.doc_count }}</div>
            <div class="stat-label">文档数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon user-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.user_count }}</div>
            <div class="stat-label">用户数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon group-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.group_count }}</div>
            <div class="stat-label">用户组数量</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStatsApi } from '@/api/dashboard'

const stats = ref({
  kb_count: 0,
  doc_count: 0,
  user_count: 0,
  group_count: 0
})

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
}
.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  margin-right: 20px;
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
</style>
