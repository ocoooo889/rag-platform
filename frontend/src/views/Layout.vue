<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo">

        <img
          v-if="brandingStore.brandLogoUrl && !logoBroken"
          :src="brandingStore.brandLogoUrl"
          alt="logo"
          class="logo-img"
          @error="onLogoError"
        />
        <div v-else class="logo-icon"></div>
        <div class="logo-text">
          <span class="logo-title">{{ brandingStore.brandName }}</span>
          <span class="logo-subtitle">{{ brandingStore.brandName }}管理后台</span>

        <div class="logo-icon" :style="{ backgroundColor: brandingStore.brandThemeColor }">
          <img v-if="brandingStore.brandLogoUrl && brandingStore.brandLogoUrl !== '/uploads/branding/logo.png'" :src="brandingStore.brandLogoUrl" alt="Logo" />
        </div>
        <div class="logo-text">
          <span class="logo-title">{{ brandingStore.brandName }}</span>
          <span class="logo-subtitle">RAG管理后台</span>

        </div>
      </div>
      <el-menu :default-active="activeMenu" class="menu" router>
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
        <el-menu-item v-if="canSeeMenu('/user-groups')" index="/user-groups">
          <el-icon><UserFilled /></el-icon>
          <span>用户组管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/models')" index="/models">
          <el-icon><Monitor /></el-icon>
          <span>大模型管理</span>
        </el-menu-item>
        <!-- 品牌配置页面暂不显示，后续需要时取消注释 -->
        <!-- <el-menu-item v-if="canSeeMenu('/branding')" index="/branding">
          <el-icon><Setting /></el-icon>
          <span>品牌配置</span>
        </el-menu-item> -->
        <el-menu-item v-if="canSeeMenu('/knowledge-bases')" index="/knowledge-bases">
          <el-icon><Folder /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSeeMenu('/documents')" index="/documents">
          <el-icon><Document /></el-icon>
          <span>文档管理</span>
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
      <div class="aside-footer">{{ brandingStore.brandFooterText }}</div>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">

          <span class="header-title">{{ brandingStore.brandName }}管理后台</span>
          <span class="header-subtitle">企业知识库检索与智能问答系统</span>

          <span>{{ brandingStore.brandName }}</span>

        </div>
        <div class="header-right">
          <span class="user-chip">{{ displayRole }}</span>
          <el-button v-if="canSeeMenu('/chat')" type="primary" link @click="goToChat">智能对话</el-button>
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

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'
import { isAdminRole, resolveRoleCode, roleCodeToLabel } from '@/utils/role'

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'

import {
  HomeFilled,
  UserFilled,
  User,
  Monitor,
  Folder,
  Document,
  Search,
  ChatDotRound,
  Setting
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const brandingStore = useBrandingStore()

const logoBroken = ref(false)


onMounted(() => {
  brandingStore.fetchBranding()
})


const activeMenu = computed(() => router.currentRoute.value.path)
const displayRole = computed(() => {
  const u = userStore.userInfo
  return u?.role_name || roleCodeToLabel(resolveRoleCode(u)) || '用户'
})

const menuVisibility = {
  '/dashboard': (role) => isAdminRole(role),
  '/roles': (role) => isAdminRole(role),
  '/users': (role) => isAdminRole(role),
  '/user-groups': (role) => isAdminRole(role),
  '/models': (role) => isAdminRole(role),
  '/branding': (role) => isAdminRole(role),
  '/knowledge-bases': () => true,
  '/documents': () => true,
  '/hit-test': () => true,
  '/chat': () => true
}

const canSeeMenu = (path) => {
  const role = resolveRoleCode(userStore.userInfo)
  if (!role) return false
  const fn = menuVisibility[path]
  return fn ? fn(role) : false
}

const onLogoError = () => {
  logoBroken.value = true
}

onMounted(async () => {
  try {
    await userStore.ensureUserInfo()
  } catch (e) {
    /* ignore */
  }
  try {
    await brandingStore.fetchBranding()
  } catch (e) {
    brandingStore.applyBranding()
  }
})

const goToChat = () => {
  router.push('/chat')
}

const handleLogout = () => {
  userStore.logout()
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background: var(--bg-color-page);
}
.aside {
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #1e2a3a 0%, #24364d 100%);
  color: var(--text-color-inverse);
  box-shadow: 8px 0 24px rgba(30, 42, 58, 0.12);
}
.aside::after {
  position: absolute;
  right: -70px;
  bottom: -70px;
  width: 180px;
  height: 180px;
  content: '';
  background: radial-gradient(circle, rgba(74, 122, 255, 0.35), rgba(74, 122, 255, 0));
  pointer-events: none;
}
.logo {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  min-height: 72px;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo-img {
  width: 38px;
  height: 38px;
  margin-right: 12px;
  object-fit: contain;
  border-radius: 10px;
  background: #fff;
}
.logo-icon {

  position: relative;
  width: 38px;
  height: 38px;
  margin-right: 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4a7aff 0%, #6b93ff 100%);
  box-shadow: 0 10px 20px rgba(74, 122, 255, 0.28);
}
.logo-icon::before,
.logo-icon::after {
  position: absolute;
  left: 10px;
  width: 18px;
  height: 4px;
  content: '';
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
}
.logo-icon::before {
  top: 12px;
}
.logo-icon::after {
  top: 21px;

  width: 40px;
  height: 40px;
  border-radius: 8px;
  margin-right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;

}
.logo-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.logo-title {
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.logo-subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.menu {
  position: relative;
  z-index: 1;
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
  border-right: none;
  background: transparent;
}
.aside-footer {
  position: relative;
  z-index: 1;
  padding: 12px 16px 16px;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.45);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
:deep(.el-menu) {
  background: transparent;
  border-right: none;
}
:deep(.el-menu-item) {
  height: 46px;
  margin: 4px 0;
  border-radius: 10px;
  color: var(--color-sidebar-text);
  transition: all 0.2s ease;
}
:deep(.el-menu-item .el-icon) {
  color: rgba(191, 203, 217, 0.85);
}
:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: rgba(74, 122, 255, 0.18);
  color: var(--color-sidebar-active);
}
:deep(.el-menu-item.is-active) {
  box-shadow: inset 3px 0 0 var(--color-primary);
}
:deep(.el-menu-item:hover .el-icon),
:deep(.el-menu-item.is-active .el-icon) {
  color: var(--color-sidebar-active);
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid var(--border-color-light);
  box-shadow: 0 2px 12px rgba(30, 42, 58, 0.04);
  backdrop-filter: blur(10px);
}
.header-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.header-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-color-primary);
}
.header-subtitle {
  font-size: 12px;
  color: var(--text-color-secondary);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.user-chip {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 1px solid var(--border-color-primary);
  border-radius: 999px;
}
.main {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background:
    radial-gradient(circle at 15% 10%, rgba(74, 122, 255, 0.09), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, var(--bg-color-page) 44%);
  overflow-y: auto;
}
</style>
