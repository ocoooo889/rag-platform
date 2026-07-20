<template>
  <!--
    聊天气泡（可复用）
    - 用户：自定义头像 + 纯文本
    - AI：公司 Logo + StreamText（流式光标 / 加载 / 报错）+ 可选溯源
  -->
  <div class="chat-bubble" :class="role">
    <div class="chat-bubble__role" :class="{ 'is-image': !!avatarSrc }" :title="roleLabel">
      <img
        v-if="avatarSrc && !avatarBroken"
        :src="avatarSrc"
        :alt="roleLabel"
        class="chat-bubble__avatar"
        @error="avatarBroken = true"
      />
      <span v-else>{{ roleFallback }}</span>
    </div>
    <div class="chat-bubble__body">
      <!-- 用户气泡：DOM 使用转义后的 contentDisplay；原始 content 仅作数据保留 -->
      <div
        v-if="role === 'user'"
        class="chat-bubble__content"
        v-html="userDisplayHtml"
      />
      <div v-else class="chat-bubble__content chat-bubble__content--assistant">
        <div v-if="retrievalBadge" class="chat-bubble__meta">
          <el-tag :type="retrievalBadge.type" size="small" effect="plain">
            {{ retrievalBadge.label }}
          </el-tag>
          <el-tag
            v-if="retrievalDegraded"
            type="warning"
            size="small"
            effect="light"
          >
            已降级
          </el-tag>
        </div>
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
                <span class="source-item__title">
                  {{ item.source_doc || '未知文档' }}
                  <el-tag
                    v-if="item.reranked"
                    size="small"
                    type="success"
                    effect="plain"
                    class="source-rerank-tag"
                  >
                    已重排
                  </el-tag>
                </span>
                <span class="source-item__meta">
                  <el-tag
                    v-if="methodLabel(item.method)"
                    size="small"
                    type="info"
                    effect="plain"
                  >
                    {{ methodLabel(item.method) }}
                  </el-tag>
                  <span :style="{ color: getScoreColor(item.score) }">
                    {{ formatScorePercent(item.score) }}
                  </span>
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
import { computed, ref, watch } from 'vue'
import { getScoreColor, formatScorePercent } from '@/utils/score'
import StreamText from '@/components/StreamText.vue'
import { useBrandingStore } from '@/stores/branding'
import { useUserStore } from '@/stores/user'
import { escapeHtml } from '@/utils/inputFilter'
import {
  getRetrievalModeLabel,
  retrievalModeTagType
} from '@/utils/retrievalMode'

const props = defineProps({
  role: { type: String, default: 'assistant' },
  /** 原始文本（raw）：提交/缓存用，不直接当未转义 HTML 插入 */
  content: { type: String, default: '' },
  /** 展示文本（display）：已 HTML 转义，仅用于用户气泡 DOM */
  contentDisplay: { type: String, default: '' },
  /** 后端/本地业务错误文案（非 HTTP 层） */
  error: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
  /** 是否处于 SSE 追加中（页面/store 的 streaming 标记） */
  streaming: { type: Boolean, default: false },
  loadingTip: { type: String, default: 'AI 思考中...' },
  /** 消息级检索模式：semantic | keyword | hybrid */
  retrievalMode: { type: String, default: '' },
  /** 本次是否发生向量→关键词降级 */
  retrievalDegraded: { type: Boolean, default: false }
})

const brandingStore = useBrandingStore()
const userStore = useUserStore()
const streamRef = ref(null)
const avatarBroken = ref(false)

/** 用户气泡：优先用独立 display；缺省时对 raw 做一次转义兜底 */
const userDisplayHtml = computed(() => {
  if (props.contentDisplay) return props.contentDisplay
  return escapeHtml(props.content || '')
})

const roleLabel = computed(() => (props.role === 'user' ? '我' : 'AI'))

const avatarSrc = computed(() => {
  if (props.role === 'user') {
    return String(userStore.userInfo?.avatar_url || '').trim()
  }
  return String(brandingStore.brandLogoUrl || '').trim()
})

const roleFallback = computed(() => {
  if (props.role === 'user') {
    const name = String(
      userStore.userInfo?.display_name || userStore.userInfo?.username || '我'
    ).trim()
    return name.slice(0, 1) || '我'
  }
  return 'AI'
})

watch(avatarSrc, () => {
  avatarBroken.value = false
})

const EMPTY_KB_ANSWER_RE = /未查询到相关内容|暂无相关内容/

/** 无相关答案时不展示溯源（即便后端仍返回了低相关 hits） */
const showSources = computed(() => {
  if (props.streaming) return false
  if (!Array.isArray(props.sources) || props.sources.length === 0) return false
  const text = String(props.content || '').replace(/\s+/g, '')
  if (EMPTY_KB_ANSWER_RE.test(text)) return false
  return true
})

const retrievalBadge = computed(() => {
  if (props.role !== 'assistant') return null
  const label = getRetrievalModeLabel(props.retrievalMode)
  if (!label) return null
  return { label, type: retrievalModeTagType(props.retrievalMode) }
})

const METHOD_LABEL = {
  vector: '语义',
  bm25: '关键词',
  keyword: '关键词',
  hybrid: '混合'
}

function methodLabel(raw) {
  return METHOD_LABEL[String(raw || '').toLowerCase()] || ''
}

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
  color: var(--text-color-inverse, #fff);
  background: var(--el-color-primary);
  border: none;
  overflow: hidden;
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--el-color-primary) 55%, transparent),
    0 0 10px color-mix(in srgb, var(--el-color-primary) 42%, transparent),
    0 0 18px color-mix(in srgb, var(--el-color-primary) 22%, transparent);
}

.chat-bubble.assistant .chat-bubble__role {
  background: color-mix(in srgb, var(--el-color-primary) 28%, rgba(20, 24, 36, 0.92));
}

.chat-bubble__role.is-image {
  background: rgba(12, 14, 22, 0.9) !important;
  padding: 0;
}

.chat-bubble__avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: 50%;
}

.chat-bubble__body {
  max-width: 72%;
}

.chat-bubble__content {
  padding: 10px 12px;
  border-radius: 8px;
  line-height: 1.6;
  word-break: break-word;
  background: var(--bg-color-user-bubble);
  color: var(--text-color-primary);
}

.chat-bubble.user .chat-bubble__content {
  white-space: pre-wrap;
}

.chat-bubble__content--assistant {
  background: var(--bg-color-ai-bubble);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  white-space: normal;
}

.chat-bubble__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding-bottom: 2px;
}

.source-panel {
  margin-top: 4px;
  border-top: 1px solid color-mix(in srgb, var(--border-color) 80%, transparent);
  padding-top: 2px;
}

.source-panel :deep(.el-collapse) {
  border: none;
}

.source-panel :deep(.el-collapse-item__header) {
  height: 36px;
  line-height: 36px;
  font-size: 13px;
  color: var(--text-color-secondary);
  background: transparent;
  border: none;
}

.source-panel :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
}

.source-panel :deep(.el-collapse-item__content) {
  padding-bottom: 4px;
}

.source-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.source-item:last-child {
  border-bottom: none;
}

.source-item__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.source-item__title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.source-rerank-tag {
  font-weight: 500;
}

.source-item__meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.source-item p {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
