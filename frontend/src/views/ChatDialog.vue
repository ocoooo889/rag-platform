<template>
  <div
    class="chat-dialog"
    :class="{ 'chat-dialog--resizing': resizing }"
    :style="{ gridTemplateColumns: panelWidth + 'px 6px 1fr' }"
    v-loading="bootLoading"
    element-loading-text="加载中..."
  >
    <!-- 左侧会话栏 -->
    <aside class="session-panel">
      <div class="session-brand">
        <el-icon :size="20"><Service /></el-icon>
        <span>RAG 智能助手</span>
      </div>

      <AppButton
        class="new-session-btn"
        type="primary"
        text="开启新对话"
        :loading="creating"
        loading-mode="normal"
        :disabled="chatStore.streaming || !chatStore.selectedKbId"
        @click="onCreateSession"
      />

      <el-input
        v-model="sessionKeyword"
        class="session-panel__search"
        placeholder="搜索会话"
        clearable
        :prefix-icon="Search"
      />

      <ul v-if="filteredSessions.length" class="session-list">
        <li
          v-for="item in filteredSessions"
          :key="item.session_id"
          class="session-item"
          :class="{ active: item.session_id === chatStore.currentSessionId }"
          @click="onSwitchSession(item.session_id)"
        >
          <span class="session-item__title">{{ item.title || '未命名会话' }}</span>
          <button
            type="button"
            class="session-item__delete"
            :disabled="chatStore.streaming"
            @click.stop="openDelete(item.session_id)"
          >
            ×
          </button>
        </li>
      </ul>

      <EmptyState
        v-else
        class="session-empty"
        type="chat"
        tip="暂无会话，点击上方开启新对话"
      />
    </aside>

    <div class="resize-handle" @mousedown="onResizeStart" />

    <!-- 右侧主区域 -->
    <section class="chat-main">
      <EmptyState v-if="pageError" type="error" :tip="pageError">
        <AppButton type="primary" text="重新加载" @click="initPage" />
      </EmptyState>

      <EmptyState
        v-else-if="!hasKb"
        type="kb"
        tip="暂无知识库，无法发起智能问答"
      />

      <div v-else class="chat-main__inner">
        <div class="chat-scroll" ref="messageListRef">
          <div class="chat-content">
            <div
              v-if="!hasMessages && !chatStore.streaming"
              class="welcome-wrap"
            >
              <div class="welcome-logo">
                <el-icon :size="36"><Service /></el-icon>
              </div>
              <h2 class="welcome-title">基于知识库开始智能问答</h2>
              <p class="welcome-subtitle">选择知识库范围后输入问题，系统将基于文档内容回答</p>

              <div class="suggest-row">
                <AppButton
                  v-for="item in suggestions"
                  :key="item"
                  type="default"
                  class="suggest-chip"
                  :text="item"
                  @click="useSuggestion(item)"
                />
              </div>
            </div>

            <div v-if="hasMessages || chatStore.streaming" class="message-thread">
              <ChatBubble
                v-for="(msg, index) in chatStore.messages"
                :key="`${msg.role}-${index}`"
                :role="msg.role"
                :content="msg.content"
                :error="msg.error || ''"
                :sources="msg.sources || []"
                :streaming="isStreamingMessage(index)"
              />
            </div>
          </div>
        </div>

        <footer class="composer-dock">
          <div class="composer-box">
            <el-input
              v-model="question"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 8 }"
              class="composer-input"
              maxlength="1000"
              placeholder="给 RAG 智能助手发送消息"
              :disabled="chatStore.streaming || !chatStore.selectedKbId"
              @keydown.enter.exact.prevent="onSend"
            />
            <div class="composer-toolbar">
              <div class="composer-toolbar__left">
                <el-select
                  v-model="chatStore.selectedKbId"
                  class="kb-chip-select"
                  placeholder="选择知识库"
                  :disabled="chatStore.streaming || !hasKb"
                >
                  <el-option
                    v-for="kb in kbStore.list"
                    :key="kb.id"
                    :label="kb.name"
                    :value="kb.id"
                  />
                </el-select>
                <AppButton
                  v-if="chatStore.streaming"
                  type="danger"
                  link
                  text="停止生成"
                  @click="onStopStream"
                />
              </div>
              <AppButton
                class="send-btn"
                type="primary"
                circle
                :loading="chatStore.streaming"
                loading-mode="sse"
                :disabled="!canSend"
                :title="sendDisabledTip"
                @click="onSend"
              >
                <el-icon v-if="!chatStore.streaming"><Top /></el-icon>
              </AppButton>
            </div>
          </div>
        </footer>
      </div>
    </section>

    <ConfirmDialog
      v-model="deleteVisible"
      title="删除会话"
      message="确认删除该会话？会话及消息记录将一并删除。"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Service, Top } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import { useChatStore } from '@/stores/chat'
import AppButton from '@/components/AppButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChatBubble from '@/components/ChatBubble.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const kbStore = useKbStore()
const chatStore = useChatStore()

const question = ref('')
const sessionKeyword = ref('')
const creating = ref(false)

const panelWidth = ref(260)
const resizing = ref(false)

function onResizeStart(e) {
  e.preventDefault()
  resizing.value = true
  const startX = e.clientX
  const startW = panelWidth.value

  function onMove(ev) {
    const delta = ev.clientX - startX
    panelWidth.value = Math.max(200, Math.min(420, startW + delta))
  }

  function onUp() {
    resizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

const deleting = ref(false)
const deleteVisible = ref(false)
const deletingId = ref(null)
const messageListRef = ref(null)
const bootLoading = ref(false)
const pageError = ref('')

const hasKb = computed(() => kbStore.list.length > 0)
const hasMessages = computed(() => chatStore.messages.length > 0)

const filteredSessions = computed(() => {
  const kw = sessionKeyword.value.trim().toLowerCase()
  if (!kw) return chatStore.sessions
  return chatStore.sessions.filter((s) =>
    String(s.title || '').toLowerCase().includes(kw)
  )
})

const suggestions = [
  '如何查看文档状态？',
  '如何测试回答来源？',
  '如何切换知识库？',
  '如何管理分片规则？'
]

const canSend = computed(
  () =>
    hasKb.value &&
    !!chatStore.selectedKbId &&
    !!question.value.trim() &&
    !chatStore.streaming &&
    !bootLoading.value
)

const sendDisabledTip = computed(() => {
  if (chatStore.streaming) return 'AI 生成中'
  if (!hasKb.value) return '暂无可用知识库'
  if (!chatStore.selectedKbId) return '请先选择知识库'
  if (!question.value.trim()) return '请输入问题'
  return '发送问题'
})

function isStreamingMessage(index) {
  return (
    chatStore.streaming &&
    index === chatStore.messages.length - 1 &&
    chatStore.messages[index]?.role === 'assistant'
  )
}

async function scrollToBottom() {
  await nextTick()
  const el = messageListRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

watch(
  () => chatStore.messages.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => {
    const list = chatStore.messages
    return list.length ? list[list.length - 1]?.content : ''
  },
  () => {
    scrollToBottom()
  }
)

watch(
  () => chatStore.selectedKbId,
  (kbId) => {
    if (kbId) kbStore.setSelectedKb(kbId)
  }
)

async function initPage() {
  pageError.value = ''
  bootLoading.value = true
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (kbStore.selectedKbId) {
      chatStore.selectedKbId = kbStore.selectedKbId
    } else if (kbStore.list.length) {
      chatStore.selectedKbId = kbStore.list[0].id
    }
    if (hasKb.value) {
      await chatStore.loadSessions()
    }
  } catch (e) {
    pageError.value = e?.message || e?.msg || '对话页加载失败，请重试'
  } finally {
    bootLoading.value = false
  }
}

async function onCreateSession() {
  if (!hasKb.value) return
  if (!chatStore.selectedKbId) {
    ElMessage.warning('请先选择知识库')
    return
  }
  creating.value = true
  try {
    await chatStore.createSession({ kb_id: chatStore.selectedKbId })
  } catch (e) {
    // 全局 axios 处理
  } finally {
    creating.value = false
  }
}

async function onSwitchSession(sessionId) {
  try {
    await chatStore.switchSession(sessionId)
  } catch (e) {
    // 全局 axios 处理
  }
}

function openDelete(sessionId) {
  deletingId.value = String(sessionId)
  deleteVisible.value = true
}

async function confirmDelete() {
  if (!deletingId.value) return
  deleting.value = true
  try {
    await chatStore.removeSession(deletingId.value)
    deleteVisible.value = false
  } catch (e) {
    // 全局 axios 处理
  } finally {
    deleting.value = false
  }
}

function onStopStream() {
  chatStore.abortCurrentStream()
}

async function onSend() {
  if (!canSend.value) {
    ElMessage.warning(sendDisabledTip.value)
    return
  }
  const text = question.value.trim()
  question.value = ''
  try {
    await chatStore.sendQuestion(text)
  } catch (e) {
    // store / 全局拦截兜底
  }
}

function useSuggestion(text) {
  question.value = text
  onSend()
}

onMounted(() => {
  initPage()
})

onUnmounted(() => {
  chatStore.abortCurrentStream()
})

defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.chat-dialog {
  display: grid;
  grid-template-columns: 260px 6px 1fr;
  height: calc(100vh - 120px);
  min-height: 560px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

/* ---- 左侧会话栏 ---- */
.session-panel {
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  padding: 16px 12px;
  gap: 12px;
  min-height: 0;
}

.session-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.new-session-btn {
  width: 100%;
  height: 40px;
}

.session-panel__search :deep(.el-input__wrapper) {
  border-radius: 20px;
  background: #fff;
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-item:hover {
  background: #eceef2;
}

.session-item.active {
  background: #e8f0fe;
}

.session-item__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--text-color-regular);
}

.session-item__delete {
  border: none;
  background: transparent;
  color: #909399;
  cursor: pointer;
  font-size: 16px;
  opacity: 0;
  flex-shrink: 0;
}

.session-item:hover .session-item__delete {
  opacity: 1;
}

.session-empty {
  flex: 1;
  padding: 20px 0;
}

.resize-handle {
  cursor: col-resize;
  background: var(--border-color);
  width: 6px;
  transition: background 0.15s;
}

.resize-handle:hover,
.chat-dialog--resizing .resize-handle {
  background: var(--color-primary);
}

.chat-dialog--resizing {
  user-select: none;
}

/* ---- 右侧主区域 ---- */
.chat-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #fff;
}

.chat-main__inner {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.chat-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 24px 16px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.welcome-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 0 60px;
}

.welcome-logo {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.25);
}

.welcome-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.welcome-subtitle {
  margin: 0 0 28px;
  font-size: 14px;
  color: var(--text-color-secondary);
}

.suggest-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  max-width: 640px;
}

.suggest-chip {
  border: 1px solid var(--border-color);
  background: #fff;
  color: var(--text-color-regular);
}

.suggest-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: #f0f7ff;
}

/* ---- 消息流 ---- */
.message-thread {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
}

/* ---- 底部输入区 ---- */
.composer-dock {
  flex-shrink: 0;
  padding: 0 24px 24px;
  display: flex;
  justify-content: center;
}

.composer-box {
  width: 100%;
  max-width: 800px;
  background: #f4f5f7;
  border: 1px solid #e8eaed;
  border-radius: 24px;
  padding: 14px 16px 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer-box:focus-within {
  border-color: #c6daf5;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.1);
}

.composer-input :deep(.el-textarea__inner) {
  box-shadow: none;
  background: transparent;
  border: none;
  padding: 0;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  min-height: 48px;
}

.composer-input :deep(.el-textarea__inner::-webkit-resizer) {
  display: none;
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  gap: 12px;
}

.composer-toolbar__left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.kb-chip-select {
  width: 180px;
}

.kb-chip-select :deep(.el-select__wrapper) {
  border-radius: 18px;
  background: #fff;
  min-height: 32px;
  font-size: 13px;
}

.send-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

@media (max-width: 1200px) {
  .suggest-row {
    flex-direction: column;
    align-items: center;
  }
}

@media (max-width: 1024px) {
  .chat-dialog {
    grid-template-columns: 1fr !important;
    height: auto;
  }

  .resize-handle {
    display: none;
  }

  .session-panel {
    border-bottom: 1px solid var(--border-color);
    max-height: 260px;
  }

  .composer-dock {
    padding: 0 16px 16px;
  }

  .chat-content {
    padding: 16px 16px 8px;
  }

  .kb-chip-select {
    width: 140px;
  }
}
</style>
