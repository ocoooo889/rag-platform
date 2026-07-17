<template>
  <!-- 聊天气泡：区分用户 / AI，AI 可折叠溯源面板 -->
  <div class="chat-bubble" :class="role">
    <div class="chat-bubble__role">{{ role === 'user' ? '我' : 'AI' }}</div>
    <div class="chat-bubble__body">
      <div class="chat-bubble__content">{{ content }}</div>
      <div v-if="role === 'assistant' && sources.length" class="source-panel">
        <el-collapse>
          <el-collapse-item title="查看溯源" name="sources">
            <div v-for="(item, index) in sources" :key="item.chunk_id || index" class="source-item">
              <div class="source-item__head">
                <span>{{ item.source_doc || '未知文档' }}</span>
                <span :style="{ color: getScoreColor(item.score) }">
                  {{ formatScorePercent(item.score) }}
                </span>
              </div>
              <p>{{ item.content }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup>
import { getScoreColor, formatScorePercent } from '@/utils/score'

defineProps({
  role: { type: String, default: 'assistant' },
  content: { type: String, default: '' },
  sources: { type: Array, default: () => [] }
})
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.chat-bubble.user {
  flex-direction: row-reverse;
}

.chat-bubble__role {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-color-inverse);
  background: var(--color-primary);
}

.chat-bubble.assistant .chat-bubble__role {
  background: var(--color-assistant-avatar);
}

.chat-bubble__body {
  max-width: 72%;
}

.chat-bubble__content {
  padding: 10px 12px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--bg-color-user-bubble);
  color: var(--text-color-primary);
}

.chat-bubble.assistant .chat-bubble__content {
  background: var(--bg-color-ai-bubble);
}

.source-panel {
  margin-top: 8px;
}

.source-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.source-item:last-child {
  border-bottom: none;
}

.source-item__head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.source-item p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-color-regular);
}
</style>
