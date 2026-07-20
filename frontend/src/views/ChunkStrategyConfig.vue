<template>
  <div class="page-shell split-strategies" v-loading="loading">
    <div class="page-header">
      <h2>文档切分策略</h2>
      <el-button :loading="loading" @click="reload">重新拉取</el-button>
    </div>
    <div class="page-body">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb12"
        title="策略列表与默认块参数均来自 GET /api/split-strategies，前端不写死策略名与 chunk 尺寸。本页只读展示；上传/评测时自动选 is_default 项。"
      />
      <el-alert
        v-if="error"
        type="error"
        :closable="false"
        show-icon
        class="mb12"
        :title="error"
      />
      <el-empty v-if="!loading && !items.length" description="暂无策略，请确认后端 split-strategies 已就绪" />
      <el-table v-else :data="items" stripe style="width: 100%">
        <el-table-column prop="label" label="策略" min-width="140">
          <template #default="{ row }">
            {{ row.label }}
            <el-tag v-if="row.is_default" size="small" type="primary" class="ml6">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="标识" width="140" />
        <el-table-column prop="desc" label="说明" min-width="220" />
        <el-table-column label="推荐块大小" width="120">
          <template #default="{ row }">{{ row.default_chunk_size }}</template>
        </el-table-column>
        <el-table-column label="推荐重叠" width="100">
          <template #default="{ row }">{{ row.default_chunk_overlap }}</template>
        </el-table-column>
        <el-table-column label="合法区间" width="140">
          <template #default="{ row }">
            {{ row.chunk_size_min }}~{{ row.chunk_size_max }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSplitStrategies } from '@/composables/useSplitStrategies'
import { clearSplitStrategiesCache } from '@/api/splitStrategies'

const { loading, error, items, load } = useSplitStrategies()

async function reload() {
  clearSplitStrategiesCache()
  try {
    await load(true)
    ElMessage.success(`已加载 ${items.value.length} 条策略`)
  } catch {
    ElMessage.error(error.value || '拉取失败')
  }
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.mb12 {
  margin-bottom: 12px;
}
.ml6 {
  margin-left: 6px;
}
</style>
