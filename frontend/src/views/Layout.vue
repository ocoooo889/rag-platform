<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="aside">
      <div class="logo">
        <div class="logo-icon"></div>
        <div class="logo-text">
          <span class="logo-title">智能RAG平台</span>
          <span class="logo-subtitle">RAG管理后台</span>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        router
      >
        <el-menu-item v-if="canSeeMenu('/dashboard')" index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>系统概览</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/roles')" index="/roles">
          <el-icon><UserFilled /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/users')" index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/models')" index="/models">
          <el-icon><Monitor /></el-icon>
          <span>大模型管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/knowledge-bases')" index="/knowledge-bases">
          <el-icon><Folder /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/hit-test')" index="/hit-test">
          <el-icon><Search /></el-icon>
          <span>命中率测试</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/chat')" index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能对话</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span>RAG管理后台</span>
        </div>
        <div class="header-right">
          <el-button v-if="canSeeMenu('/chat')" type="text" @click="goToChat">智能对话</el-button>
          <el-button type="text" @click="handleLogout">退出</el-button>
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
import { useUserStore } from '@/stores/user'
import { HomeFilled, UserFilled, User, Monitor, Folder, Search, ChatDotRound } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => router.currentRoute.value.path)

const menuRoles = {
  '/dashboard': ['管理员', '编辑员'],
  '/roles': ['管理员'],
  '/users': ['管理员'],
  '/models': ['管理员'],
  '/knowledge-bases': ['管理员', '编辑员'],
  '/hit-test': ['管理员', '编辑员'],
  '/chat': ['管理员', '编辑员', '普通用户'],
}

const canSeeMenu = (path) => {
  const role = userStore.userInfo?.role_name
  if (!role) return false
  const allowedRoles = menuRoles[path]
  if (!allowedRoles) return false
  return allowedRoles.includes(role)
}

const goToChat = () => {
  router.push('/chat')
}

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.aside {
  background-color: #304156;
  color: #fff;
}
.logo {
  display: flex;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #434f63;
}
.logo-icon {
  width: 40px;
  height: 40px;
  background-color: #f56c6c;
  border-radius: 8px;
  margin-right: 10px;
}
.logo-text {
  display: flex;
  flex-direction: column;
}
.logo-title {
  font-size: 16px;
  font-weight: bold;
  color: #fff;
}
.logo-subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}
.menu {
  border-right: none;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
}
.header-left {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>