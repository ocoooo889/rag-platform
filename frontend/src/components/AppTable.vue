<template>
  <!-- 基础表格：统一空数据插槽，无批量复选逻辑 -->
  <el-table
    v-loading="loading"
    element-loading-text="加载中..."
    :data="data"
    border
    style="width: 100%"
  >
    <slot />
    <template #empty>
      <slot name="empty">
        <EmptyState type="default" />
      </slot>
    </template>
  </el-table>
</template>

<script setup>
import EmptyState from './EmptyState.vue'

defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
</script>
