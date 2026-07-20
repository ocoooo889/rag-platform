<template>
  <!-- 检索结果卡片：排名 + 三色相似度进度条 + 分片信息 -->
  <div class="retrieve-card">
    <div class="retrieve-card__header">
      <span class="rank">
        排名 #{{ rank }}
        <el-tag v-if="reranked" size="small" type="success" effect="plain" class="rerank-tag">
          已重排
        </el-tag>
      </span>
      <span class="score-text">{{ formatScorePercent(score) }}</span>
    </div>
    <el-progress
      :percentage="scorePercent"
      :stroke-width="10"
      :show-text="false"
      :color="scoreColor"
    />
    <p class="content">{{ content }}</p>
    <div class="meta">
      <span>来源文档：{{ sourceDoc }}</span>
      <span>分片 ID：{{ chunkId }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getScoreColor, formatScorePercent } from '@/utils/score'

const props = defineProps({
  rank: { type: Number, required: true },
  score: { type: Number, default: 0 },
  content: { type: String, default: '' },
  sourceDoc: { type: String, default: '' },
  chunkId: { type: String, default: '' },
  reranked: { type: Boolean, default: false }
})

const scorePercent = computed(() => Math.round(Math.max(0, Math.min(1, Number(props.score) || 0)) * 100))
const scoreColor = computed(() => getScoreColor(props.score))
</script>

<style scoped>
.retrieve-card {
  padding: 14px 16px;
  margin-bottom: 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-color-card);
}

.retrieve-card__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.rank {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.rerank-tag {
  font-weight: 500;
}

.content {
  margin: 12px 0 8px;
  line-height: 1.6;
  color: var(--text-color-regular);
  white-space: pre-wrap;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
}
</style>
