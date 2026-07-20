<template>
  <!--
    流式文本渲染器（纯展示，与页面解耦）
    推荐用法（store 驱动 SSE）：受控 props content / loading / error
    命令式用法（少数场景）：ref.append / clear / setText / setError
    注意：受控与命令式不要混用同一实例，以免互相覆盖
    variant=assistant 时对回答做轻量 Markdown 排版
  -->
  <div class="stream-text" :class="rootClass" ref="rootRef">
    <div v-if="errorText" class="stream-text__error">
      <span class="stream-text__error-icon">!</span>
      <span>{{ errorText }}</span>
    </div>
    <div v-else-if="loading && !displayText" class="stream-text__loading">
      <span class="dot" /><span class="dot" /><span class="dot" />
      <span class="stream-text__loading-tip">{{ loadingTip }}</span>
    </div>
    <div v-else class="stream-text__body">
      <div
        v-if="useMarkdown"
        class="stream-text__content stream-text__content--md"
        v-html="renderedHtml"
      />
      <span v-else class="stream-text__content">{{ displayText }}</span>
      <span v-if="loading" class="stream-text__cursor" aria-hidden="true" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { renderAssistantMarkdown } from '@/utils/assistantMarkdown'

const props = defineProps({
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  loadingTip: { type: String, default: 'AI 思考中...' },
  /** plain | assistant — assistant 启用 Markdown 排版 */
  variant: { type: String, default: 'plain' }
})

const rootRef = ref(null)
/** 命令式模式下的本地缓冲；受控时由 props 同步覆盖 */
const localText = ref('')
const localError = ref('')
const useLocalText = ref(false)
const useLocalError = ref(false)

watch(
  () => props.content,
  () => {
    useLocalText.value = false
  }
)

watch(
  () => props.error,
  () => {
    useLocalError.value = false
  }
)

const displayText = computed(() =>
  useLocalText.value ? localText.value : props.content || ''
)
const errorText = computed(() =>
  useLocalError.value ? localError.value : props.error || ''
)
const loading = computed(() => !!props.loading)
const useMarkdown = computed(() => props.variant === 'assistant')
const renderedHtml = computed(() =>
  useMarkdown.value ? renderAssistantMarkdown(displayText.value) : ''
)

const rootClass = computed(() => ({
  [`is-${props.variant}`]: true,
  'is-loading': loading.value,
  'is-error': !!errorText.value,
  'is-markdown': useMarkdown.value
}))

function append(chunk = '') {
  if (!chunk) return
  if (!useLocalText.value) {
    localText.value = props.content || ''
  }
  useLocalText.value = true
  useLocalError.value = true
  localError.value = ''
  localText.value += String(chunk)
}

function clear() {
  useLocalText.value = true
  useLocalError.value = true
  localText.value = ''
  localError.value = ''
}

function setText(text = '') {
  useLocalText.value = true
  useLocalError.value = true
  localError.value = ''
  localText.value = String(text || '')
}

function setError(message = '') {
  useLocalError.value = true
  localError.value = String(message || '')
}

function getText() {
  return displayText.value
}

defineExpose({
  append,
  clear,
  setText,
  setError,
  getText,
  rootRef
})
</script>

<style scoped>
.stream-text {
  line-height: 1.7;
  word-break: break-word;
}

.stream-text:not(.is-markdown) {
  white-space: pre-wrap;
}

.stream-text__body {
  min-height: 1.2em;
}

.stream-text__content--md {
  white-space: normal;
}

.stream-text__content--md :deep(.md-p) {
  margin: 0 0 0.75em;
}

.stream-text__content--md :deep(.md-p:last-child) {
  margin-bottom: 0;
}

.stream-text__content--md :deep(.md-h) {
  margin: 0.9em 0 0.45em;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-color-primary);
}

.stream-text__content--md :deep(.md-h1) {
  font-size: 1.15em;
}

.stream-text__content--md :deep(.md-h2),
.stream-text__content--md :deep(.md-h3) {
  font-size: 1.05em;
}

.stream-text__content--md :deep(.md-h:first-child) {
  margin-top: 0;
}

.stream-text__content--md :deep(.md-quote) {
  margin: 0.55em 0 0.85em;
  padding: 0.55em 0.85em;
  border-left: 3px solid color-mix(in srgb, var(--el-color-primary) 70%, transparent);
  border-radius: 0 8px 8px 0;
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  color: var(--text-color-regular, var(--text-color-primary));
}

.stream-text__content--md :deep(.md-quote__p) {
  margin: 0.2em 0;
  line-height: 1.65;
}

.stream-text__content--md :deep(.md-ul),
.stream-text__content--md :deep(.md-ol) {
  margin: 0.4em 0 0.85em;
  padding-left: 1.35em;
}

.stream-text__content--md :deep(.md-ul li),
.stream-text__content--md :deep(.md-ol li) {
  margin: 0.25em 0;
}

.stream-text__content--md :deep(.md-code) {
  padding: 0.1em 0.35em;
  border-radius: 4px;
  font-size: 0.92em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: color-mix(in srgb, var(--text-color-primary) 10%, transparent);
}

.stream-text__content--md :deep(strong) {
  font-weight: 650;
  color: var(--text-color-primary);
}

.stream-text__cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--color-primary);
  animation: stream-blink 0.9s step-end infinite;
}

.stream-text__loading {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-color-secondary);
  font-size: 13px;
}

.stream-text__loading .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.35;
  animation: stream-dot 1.2s ease-in-out infinite;
}

.stream-text__loading .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.stream-text__loading .dot:nth-child(3) {
  animation-delay: 0.4s;
}

.stream-text__loading-tip {
  margin-left: 6px;
}

.stream-text__error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--status-failed-bg);
  color: var(--status-failed-text);
  font-size: 13px;
}

.stream-text__error-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: var(--status-failed-text);
  color: #fff;
}

@keyframes stream-blink {
  50% {
    opacity: 0;
  }
}

@keyframes stream-dot {
  0%,
  80%,
  100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}
</style>
