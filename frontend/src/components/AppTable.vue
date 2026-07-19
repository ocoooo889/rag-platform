<template>
  <el-table
    ref="tableRef"
    v-equal-table
    v-loading="loading"
    element-loading-text="加载中..."
    :data="data"
    border
    table-layout="fixed"
    style="width: 100%"
    class="app-table"
    @selection-change="onSelectionChange"
  >
    <el-table-column v-if="selectable" type="selection" align="center" />
    <slot />
    <template #empty>
      <slot name="empty">
        <EmptyState type="default" />
      </slot>
    </template>
  </el-table>
</template>

<script setup>
import { ref } from 'vue'
import EmptyState from './EmptyState.vue'

defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false }
})

const emit = defineEmits(['selection-change'])
const tableRef = ref(null)

function onSelectionChange(rows) {
  emit('selection-change', rows)
}

function clearSelection() {
  tableRef.value?.clearSelection?.()
}

defineExpose({ clearSelection })
</script>
