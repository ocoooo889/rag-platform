<template>
  <!-- 统一空状态：无知识库 / 文档 / 检索结果 / 对话记录 -->
  <div class="empty-state">
    <el-empty :description="description" :image-size="96" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** kb | doc | retrieve | chat | default */
  type: { type: String, default: 'default' },
  tip: { type: String, default: '' }
})

const TEXT_MAP = {
  kb: '暂无知识库，请先新建知识库',
  doc: '暂无文档，请上传 md/txt 文件',
  retrieve: '暂无匹配结果，请调整问题或检索模式后重试',
  chat: '暂无对话记录，请新建会话开始提问',
  default: '暂无数据'
}

const description = computed(() => props.tip || TEXT_MAP[props.type] || TEXT_MAP.default)
</script>

<style scoped>
.empty-state {
  padding: 24px 0;
}
</style>
