<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="app-aside">
      <div class="logo">RAG Platform</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/kb">知识库管理</el-menu-item>
        <el-menu-item index="/doc">文档管理</el-menu-item>
        <el-menu-item index="/hit-test">命中率测试</el-menu-item>
        <el-menu-item index="/chat">智能对话</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-aside {
  border-right: 1px solid var(--border-color);
  background: var(--bg-color-card);
}

.logo {
  padding: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.app-main {
  background: var(--bg-color-page);
}
</style>
