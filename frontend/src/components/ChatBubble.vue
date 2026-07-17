<template>
  <!--
    聊天气泡（可复用）
    - 用户：纯文本
    - AI：内嵌 StreamText（流式光标 / 加载 / 报错）+ 可选溯源
    页面只需传 props，不必再抄 ai-row / 溯源 DOM
  -->
  <div class="chat-bubble" :class="role">
    <div class="chat-bubble__role">{{ role === 'user' ? '我' : 'AI' }}</div>
    <div class="chat-bubble__body">
      <div v-if="role === 'user'" class="chat-bubble__content">{{ content }}</div>
      <div v-else class="chat-bubble__content chat-bubble__content--assistant">
        <StreamText
          ref="streamRef"
          :content="content"
          :loading="streaming"
          :error="error"
          :loading-tip="loadingTip"
          variant="assistant"
        />
      </div>
      <div v-if="role === 'assistant' && showSources" class="source-panel">
        <el-collapse>
          <el-collapse-item title="查看溯源" name="sources">
            <div
              v-for="(item, index) in sources"
              :key="item.chunk_id || index"
              class="source-item"
            >
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
import { computed, ref } from 'vue'
import { getScoreColor, formatScorePercent } from '@/utils/score'
import StreamText from '@/components/StreamText.vue'

const props = defineProps({
  role: { type: String, default: 'assistant' },
  content: { type: String, default: '' },
  /** 后端/本地业务错误文案（非 HTTP 层） */
  error: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
  /** 是否处于 SSE 追加中（页面/store 的 streaming 标记） */
  streaming: { type: Boolean, default: false },
  loadingTip: { type: String, default: 'AI 思考中...' }
})

const streamRef = ref(null)

const showSources = computed(
  () => !props.streaming && Array.isArray(props.sources) && props.sources.length > 0
)

/** 透传流式命令式 API，供少数非受控场景复用 */
defineExpose({
  append: (chunk) => streamRef.value?.append?.(chunk),
  clear: () => streamRef.value?.clear?.(),
  setText: (text) => streamRef.value?.setText?.(text),
  setError: (msg) => streamRef.value?.setError?.(msg),
  getText: () => streamRef.value?.getText?.() || ''
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

.chat-bubble__content--assistant {
  background: var(--bg-color-ai-bubble);
  padding: 10px 12px;
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
