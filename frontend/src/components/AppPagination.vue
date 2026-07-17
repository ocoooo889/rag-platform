<template>
  <!-- 全局分页器：复用 Element Plus，统一事件对外抛出 -->
  <div class="app-pagination" v-if="total > 0">
    <el-pagination
      background
      layout="total, prev, pager, next, sizes"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      :page-sizes="pageSizes"
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />
  </div>
</template>

<script setup>
defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 },
  pageSizes: { type: Array, default: () => [10, 20, 50] }
})

const emit = defineEmits(['update:page', 'update:pageSize', 'change'])

function onPageChange(val) {
  emit('update:page', val)
  emit('change', { page: val })
}

function onSizeChange(val) {
  emit('update:pageSize', val)
  emit('change', { pageSize: val })
}
</script>

<style scoped>
.app-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
