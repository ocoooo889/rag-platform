<template>
  <!-- 统一空 / 错状态：无知识库 / 文档 / 检索结果 / 对话记录 / 报错 -->
  <div class="empty-state" :class="{ 'is-error': type === 'error' }">
    <el-empty :description="description" :image-size="96">
      <template v-if="type === 'error'" #image>
        <div class="error-badge">!</div>
      </template>
      <slot />
    </el-empty>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** kb | doc | retrieve | chat | error | default */
  type: { type: String, default: 'default' },
  tip: { type: String, default: '' }
})

const TEXT_MAP = {
  kb: '暂无知识库，请先新建知识库',
  doc: '暂无文档，请上传 md/txt 文件',
  retrieve: '暂无匹配结果，请调整问题或检索模式后重试',
  chat: '暂无对话记录，请新建会话开始提问',
  error: '加载失败，请稍后重试',
  default: '暂无数据'
}

const description = computed(() => props.tip || TEXT_MAP[props.type] || TEXT_MAP.default)
</script>

<style scoped>
.empty-state {
  padding: 24px 0;
}

.empty-state.is-error :deep(.el-empty__description) {
  color: var(--status-failed-text);
}

.error-badge {
  width: 64px;
  height: 64px;
  margin: 0 auto;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  background: var(--status-failed-text);
}
</style>
