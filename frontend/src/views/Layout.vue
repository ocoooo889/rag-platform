<template>
  <el-container class="layout-container">
    <el-aside width="196px" class="aside">
      <div class="logo">
        <div class="logo-icon"></div>
        <div class="logo-text">
          <span class="logo-title">智能RAG平台</span>
          <span class="logo-subtitle">RAG管理后台</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="menu" router>
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>系统概览</span>
        </el-menu-item>
        <el-menu-item index="/roles">
          <el-icon><UserFilled /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Monitor /></el-icon>
          <span>大模型管理</span>
        </el-menu-item>
        <el-menu-item index="/knowledge-bases">
          <el-icon><Folder /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/documents">
          <el-icon><Document /></el-icon>
          <span>文档管理</span>
        </el-menu-item>
        <el-menu-item index="/hit-test">
          <el-icon><Search /></el-icon>
          <span>命中率测试</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能对话</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">RAG管理后台</div>
        <div class="header-right">
          <el-button type="primary" link @click="goToChat">智能对话</el-button>
          <el-button type="primary" link @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatDotRound,
  Document,
  Folder,
  HomeFilled,
  Monitor,
  Search,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => router.currentRoute.value.path)

function goToChat() {
  router.push('/chat')
}

function handleLogout() {
  userStore.logout()
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.aside {
  background: #304156;
  color: #ffffff;
}

.logo {
  display: flex;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  width: 36px;
  height: 36px;
  margin-right: 10px;
  border-radius: 8px;
  background: linear-gradient(135deg, #ff7b7b 0%, #ff6b6b 100%);
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

.logo-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.menu {
  border-right: none;
  background: transparent;
}

:deep(.el-menu) {
  background: transparent;
  border-right: none;
}

:deep(.el-menu-item) {
  color: #d8e0ea;
}

:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-color-card);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.main {
  padding: 16px;
  background: var(--bg-color-page);
}
</style>
