<template>
  <div
    class="chat-dialog"
    :class="{ 'chat-dialog--resizing': resizing || vResizing }"
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

      <el-button
        class="new-session-btn"
        type="primary"
        :loading="creating"
        :disabled="chatStore.streaming || !chatStore.selectedKbId"
        @click="onCreateSession"
      >
        {{ creating ? '加载中...' : '开启新对话' }}
      </el-button>

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
          :class="{
            active: item.session_id === chatStore.currentSessionId,
            pinned: item.pinned
          }"
          @click="onSwitchSession(item.session_id)"
        >
          <span class="session-item__title">{{ item.title || '未命名会话' }}</span>
          <el-dropdown
            trigger="click"
            placement="bottom-end"
            :teleported="true"
            popper-class="session-action-menu"
            @command="(cmd) => onSessionCommand(cmd, item)"
          >
            <span
              class="session-item__action"
              :class="{ 'is-pinned': item.pinned }"
              role="button"
              tabindex="0"
              :aria-label="item.pinned ? '已置顶，点击管理会话' : '会话操作'"
              :title="item.pinned ? '已置顶' : '更多操作'"
              @click.stop
            >
              <el-icon v-if="item.pinned" class="session-item__action-pin" :size="14">
                <Top />
              </el-icon>
              <el-icon class="session-item__action-more" :size="16">
                <MoreFilled />
              </el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="pin">
                  <el-icon><Top /></el-icon>
                  <span>{{ item.pinned ? '取消置顶' : '置顶' }}</span>
                </el-dropdown-item>
                <el-dropdown-item command="rename">
                  <el-icon><EditPen /></el-icon>
                  <span>重命名</span>
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided class="session-action-danger">
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
        <el-button type="primary" @click="initPage">重新加载</el-button>
      </EmptyState>

      <EmptyState
        v-else-if="!hasKb"
        type="kb"
        tip="暂无知识库，无法发起智能问答"
      />

      <div v-else class="chat-main__inner">
        <div class="chat-scroll" ref="messageListRef" @scroll.passive="onChatScroll">
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
                <el-button
                  v-for="item in suggestions"
                  :key="item"
                  class="suggest-chip"
                  @click="useSuggestion(item)"
                >
                  {{ item }}
                </el-button>
              </div>
            </div>

            <div v-if="hasMessages || chatStore.streaming" class="message-thread">
              <ChatBubble
                v-for="(msg, index) in chatStore.messages"
                :key="msg.id || `${msg.role}-${index}`"
                :role="msg.role"
                :content="msg.content"
                :error="msg.error || ''"
                :sources="msg.sources || []"
                :streaming="isStreamingMessage(index)"
                :loading-tip="chatStore.streamStatus || 'AI 思考中...'"
              />
            </div>
          </div>
        </div>

        <!-- 上下可拖拽分割条 -->
        <div
          class="v-resize-handle"
          :class="{ 'is-resizing': vResizing }"
          @mousedown="onVResizeStart"
        />

        <footer class="composer-dock" :style="{ height: composerHeight + 'px' }">
          <div
            class="composer-box"
            :class="{ 'composer-box--active': composerActive }"
          >
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              class="composer-input"
              maxlength="1000"
              placeholder="给 RAG 智能助手发送消息"
              :disabled="chatStore.streaming || !chatStore.selectedKbId"
              @focus="composerActive = true"
              @blur="composerActive = false"
              @keydown.enter.exact.prevent="onSend"
            />
            <div class="composer-toolbar">
              <div class="composer-toolbar__left">
                <label class="kb-chip-label" for="composer-kb-select">知识库：</label>
                <el-select
                  id="composer-kb-select"
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
                <el-button
                  v-if="chatStore.streaming"
                  text
                  type="danger"
                  @click="onStopStream"
                >
                  停止生成
                </el-button>
              </div>
              <button
                type="button"
                class="send-btn"
                :disabled="!canSend || chatStore.streaming"
                :title="sendDisabledTip"
                :aria-label="chatStore.streaming ? '生成中' : '发送'"
                @click="onSend"
              >
                <span v-if="chatStore.streaming" class="send-btn__loading" />
                <el-icon v-else :size="18"><Top /></el-icon>
              </button>
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

    <el-dialog
      v-model="renameVisible"
      title="重命名会话"
      width="400px"
      append-to-body
      class="session-rename-dialog"
      @closed="renameTitle = ''"
    >
      <el-input
        v-model="renameTitle"
        maxlength="25"
        show-word-limit
        placeholder="输入会话名称（最多25字）"
        @keydown.enter.prevent="confirmRename"
      />
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Service, Top, MoreFilled, EditPen, Delete } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import { useChatStore } from '@/stores/chat'
import EmptyState from '@/components/EmptyState.vue'
import ChatBubble from '@/components/ChatBubble.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const kbStore = useKbStore()
const chatStore = useChatStore()

const question = ref('')
const sessionKeyword = ref('')
const composerActive = ref(false)
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

/** 上下拖拽：调整底部输入区高度 */
const composerHeight = ref(148)
const vResizing = ref(false)

function onVResizeStart(e) {
  e.preventDefault()
  vResizing.value = true
  const startY = e.clientY
  const startH = composerHeight.value

  function onMove(ev) {
    // 向上拖 → 输入区变高；向下拖 → 变矮
    const delta = startY - ev.clientY
    composerHeight.value = Math.max(120, Math.min(420, startH + delta))
  }

  function onUp() {
    vResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

const deleting = ref(false)
const deleteVisible = ref(false)
const deletingId = ref(null)
const renameVisible = ref(false)
const renameId = ref(null)
const renameTitle = ref('')
const messageListRef = ref(null)
const bootLoading = ref(false)
const pageError = ref('')
/** 仅当用户贴近底部时才自动滚到底，避免流式输出抢滚动 */
const stickToBottom = ref(true)
let scrollRaf = null
let streamScrollTimer = null

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

function onChatScroll() {
  const el = messageListRef.value
  if (!el) return
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 96
}

async function scrollToBottom(force = false) {
  if (!force && !stickToBottom.value) return
  await nextTick()
  const el = messageListRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

watch(
  () => chatStore.messages.length,
  () => {
    stickToBottom.value = true
    scrollToBottom(true)
  }
)

// 流式期间用定时滚动，禁止按 content.length 每次 layout（会卡主线程 >1s 再整段刷出）
watch(
  () => chatStore.streaming,
  (on) => {
    if (streamScrollTimer != null) {
      clearInterval(streamScrollTimer)
      streamScrollTimer = null
    }
    if (on) {
      streamScrollTimer = setInterval(() => {
        scrollToBottom()
      }, 120)
    } else {
      scrollToBottom(true)
    }
  }
)

watch(
  () => chatStore.currentSessionId,
  () => {
    stickToBottom.value = true
    scrollToBottom(true)
  }
)

watch(
  () => chatStore.selectedKbId,
  (kbId) => {
    if (kbId) {
      kbStore.setSelectedKb(kbId)
      chatStore.warmupSelectedKb()
    }
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
      chatStore.hydrateFromLocal()
      // 预热与拉会话并行，缩短首问前的冷启动
      await Promise.all([
        chatStore.loadSessions(),
        chatStore.warmupSelectedKb()
      ])
      // 左侧历史列表；主区只展示当前会话（本地已持久化）
      if (chatStore.sessions.length) {
        const targetId =
          chatStore.currentSessionId &&
          chatStore.sessions.some(
            (s) => String(s.session_id) === String(chatStore.currentSessionId)
          )
            ? chatStore.currentSessionId
            : chatStore.sessions[0].session_id
        await chatStore.switchSession(targetId)
      } else {
        stickToBottom.value = true
      }
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
    stickToBottom.value = true
    await chatStore.switchSession(sessionId)
    await scrollToBottom(true)
  } catch (e) {
    // 全局 axios 处理
  }
}

function openDelete(sessionId) {
  deletingId.value = String(sessionId)
  deleteVisible.value = true
}

async function onSessionCommand(command, item) {
  if (chatStore.streaming) {
    ElMessage.warning('请先停止生成后再操作会话')
    return
  }
  const sid = String(item.session_id)
  try {
    if (command === 'pin') {
      const pinned = await chatStore.togglePinSession(sid)
      ElMessage.success(pinned ? '已置顶' : '已取消置顶')
      return
    }
    if (command === 'rename') {
      renameId.value = sid
      renameTitle.value = item.title || ''
      renameVisible.value = true
      return
    }
    if (command === 'delete') {
      openDelete(sid)
    }
  } catch (e) {
    ElMessage.error(e?.msg || e?.message || '操作失败，请重试')
  }
}

async function confirmRename() {
  const title = renameTitle.value.trim()
  if (!title) {
    ElMessage.warning('请输入会话名称')
    return
  }
  if (!renameId.value) return
  try {
    await chatStore.renameSession(renameId.value, title)
    ElMessage.success('已重命名')
    renameVisible.value = false
  } catch (e) {
    ElMessage.error(e?.msg || e?.message || '重命名失败')
  }
}

async function confirmDelete() {
  if (!deletingId.value) return
  deleting.value = true
  try {
    await chatStore.removeSession(deletingId.value)
    deleteVisible.value = false
    ElMessage.success('会话已删除')
  } catch (e) {
    ElMessage.error(e?.msg || e?.message || '删除失败')
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
  // 不 await 整段流式：避免发送 Promise 挂起影响切页体感；错误由 store 落在气泡里
  chatStore.sendQuestion(text).catch(() => {})
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
  if (streamScrollTimer != null) {
    clearInterval(streamScrollTimer)
    streamScrollTimer = null
  }
  if (scrollRaf != null) {
    cancelAnimationFrame(scrollRaf)
    scrollRaf = null
  }
})

defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.chat-dialog {
  display: grid;
  grid-template-columns: 260px 6px 1fr;
  height: calc(100vh - var(--admin-header-height) - 48px);
  min-height: 520px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-color-card);
}

/* ---- 左侧会话栏 ---- */
.session-panel {
  display: flex;
  flex-direction: column;
  background: var(--bg-color-page-soft);
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
  /* 高度跟随全局主按钮 32px，与「批量删除」对齐 */
}

.session-panel__search :deep(.el-input__wrapper) {
  border-radius: 20px;
  background: var(--bg-color-card);
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
  background: var(--bg-color-hover);
}

.session-item.active {
  background: var(--color-primary-soft);
}

.session-item__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--admin-fs-secondary, 13px);
  color: var(--text-color-regular);
}

/* 右侧操作位：未置顶=三点；已置顶=图钉，悬停同位置变三点 */
.session-item__action {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 8px;
  color: rgba(180, 180, 185, 0.72);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.session-item__action-pin,
.session-item__action-more {
  position: absolute;
  inset: 0;
  margin: auto;
  transition: opacity 0.15s ease;
}

.session-item__action:not(.is-pinned) .session-item__action-more {
  opacity: 0.55;
}

.session-item:hover .session-item__action:not(.is-pinned) .session-item__action-more,
.session-item.active .session-item__action:not(.is-pinned) .session-item__action-more {
  opacity: 1;
}

.session-item__action.is-pinned .session-item__action-pin {
  opacity: 1;
}

.session-item__action.is-pinned .session-item__action-more {
  opacity: 0;
  pointer-events: none;
}

.session-item__action.is-pinned:hover .session-item__action-pin {
  opacity: 0;
}

.session-item__action.is-pinned:hover .session-item__action-more {
  opacity: 1;
  pointer-events: auto;
}

.session-item__action:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--admin-text, #f5f5f5);
}

.session-empty {
  flex: 1;
  padding: 20px 0;
}

.resize-handle {
  cursor: col-resize;
  width: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-left: 1px solid rgba(120, 160, 255, 0.1);
  border-right: 1px solid rgba(120, 160, 255, 0.1);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.2);
  transition: background 0.18s ease, box-shadow 0.18s ease;
}

.resize-handle:hover,
.chat-dialog--resizing .resize-handle {
  background: color-mix(in srgb, var(--el-color-primary) 42%, rgba(16, 20, 32, 0.9));
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 35%, transparent),
    0 0 12px color-mix(in srgb, var(--el-color-primary) 35%, transparent);
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
  background: var(--bg-color-card);
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
  background: linear-gradient(135deg, var(--el-color-primary) 0%, var(--el-color-primary-light-3) 100%);
  color: var(--text-color-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--el-color-primary) 28%, transparent);
}

.welcome-title {
  margin: 0 0 8px;
  font-size: var(--admin-fs-title, 22px);
  font-weight: 600;
  color: var(--text-color-primary);
}

.welcome-subtitle {
  margin: 0 0 28px;
  font-size: var(--admin-fs-body, 14px);
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
  background: var(--bg-color-card);
  color: var(--text-color-regular);
}

.suggest-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

/* ---- 消息流 ---- */
.message-thread {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
  width: 100%;
}

.message-thread :deep(.chat-bubble) {
  margin-bottom: 4px;
}

.message-thread :deep(.chat-bubble__body) {
  max-width: 85%;
}

/* ---- 上下分割条 ---- */
.v-resize-handle {
  flex-shrink: 0;
  height: 6px;
  cursor: row-resize;
  background: transparent;
  position: relative;
  z-index: 2;
}

.v-resize-handle::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(120, 160, 255, 0.14);
  box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.25);
  transition: background 0.18s ease, width 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.v-resize-handle:hover::after,
.v-resize-handle.is-resizing::after {
  width: 56px;
  background: color-mix(in srgb, var(--el-color-primary) 55%, rgba(16, 20, 32, 0.85));
  border-color: color-mix(in srgb, var(--el-color-primary) 45%, transparent);
  box-shadow: 0 0 10px color-mix(in srgb, var(--el-color-primary) 40%, transparent);
}

.chat-dialog--resizing,
.chat-main__inner:has(.v-resize-handle.is-resizing) {
  user-select: none;
}

/* ---- 底部输入区：静默无蓝光；仅 textarea 聚焦时外壳亮蓝光 ---- */
.composer-dock {
  flex-shrink: 0;
  height: 148px;
  min-height: 128px;
  max-height: 420px;
  padding: 4px 28px 20px;
  display: flex;
  justify-content: center;
  box-sizing: border-box;
  border-top: none;
  background: transparent;
}

.composer-box {
  width: 100%;
  max-width: 820px;
  height: 100%;
  /* 底色透明跟页面；浅蓝毛玻璃覆盖由 admin-theme（glass-fill + blur）提供 */
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 28px;
  padding: 16px 18px 12px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
  transition: border-color 0.22s ease, box-shadow 0.22s ease;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 打字/聚焦：仅外壳蓝光，无内层描边 */
.composer-box--active {
  border-color: color-mix(in srgb, var(--el-color-primary) 72%, #fff 8%);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--el-color-primary) 35%, transparent),
    0 0 22px color-mix(in srgb, var(--el-color-primary) 28%, transparent),
    0 10px 32px rgba(0, 0, 0, 0.45);
}

.composer-input {
  flex: 1;
  min-height: 0;
}

.composer-input :deep(.el-textarea) {
  height: 100%;
}

/* 彻底盖掉 admin.css / EP 给 textarea 的 inset 蓝边，避免套娃 */
.composer-input :deep(.el-textarea__inner),
.composer-input :deep(.el-textarea__inner:hover),
.composer-input :deep(.el-textarea__inner:focus) {
  box-shadow: none !important;
  outline: none !important;
  background: transparent !important;
  border: none !important;
  padding: 2px 4px;
  resize: none;
  font-size: var(--admin-fs-body-lg, 15px);
  line-height: 1.65;
  color: var(--admin-text, #f5f5f5);
  caret-color: var(--el-color-primary);
  height: 100% !important;
  min-height: 52px;
  overflow-y: auto;
}

.composer-input :deep(.el-textarea__inner::placeholder) {
  color: rgba(160, 160, 165, 0.48);
}

.composer-input :deep(.el-textarea__inner::-webkit-resizer) {
  display: none;
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 12px;
  flex-shrink: 0;
  min-height: 36px;
}

.composer-toolbar__left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.kb-chip-label {
  flex-shrink: 0;
  margin: 0;
  font-size: 13px;
  line-height: 1;
  color: rgba(200, 200, 205, 0.62);
  cursor: default;
  user-select: none;
}

.kb-chip-select {
  width: 168px;
}

.kb-chip-select :deep(.el-select__wrapper) {
  border-radius: 999px;
  min-height: 32px;
  padding: 0 12px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.04) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset !important;
  color: rgba(200, 200, 205, 0.62);
}

.kb-chip-select :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2) inset !important;
}

.kb-chip-select :deep(.el-select__wrapper.is-focused) {
  /* 下拉聚焦也不给蓝边，避免和外壳抢戏 */
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2) inset !important;
}

.kb-chip-select :deep(.el-select__placeholder),
.kb-chip-select :deep(.el-select__selected-item) {
  color: rgba(200, 200, 205, 0.62);
}

.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  background: var(--el-color-primary);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--el-color-primary) 40%, transparent);
  transition: transform 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--el-color-primary) 48%, transparent);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.42;
  box-shadow: none;
}

.send-btn__loading {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: send-spin 0.7s linear infinite;
}

@keyframes send-spin {
  to {
    transform: rotate(360deg);
  }
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
    padding: 4px 16px 16px;
  }

  .chat-content {
    padding: 16px 16px 8px;
  }

  .kb-chip-select {
    width: 140px;
  }
}
</style>

<style>
/* teleported 菜单：统一磨砂玻璃 */
.session-action-menu.el-popper,
.session-action-menu {
  background: var(--glass-fill) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--glass-radius) !important;
  padding: 6px !important;
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--glass-shadow) !important;
}

.session-action-menu .el-dropdown-menu {
  background: transparent;
  border: none;
  padding: 0;
}

.session-action-menu .el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 140px;
  height: 40px;
  margin: 2px 0;
  padding: 0 12px;
  border-radius: 8px;
  color: rgba(235, 235, 240, 0.88);
  line-height: 1;
}

.session-action-menu .el-dropdown-menu__item .el-icon {
  margin: 0;
  font-size: 16px;
  color: inherit;
}

.session-action-menu .el-dropdown-menu__item:not(.is-disabled):hover,
.session-action-menu .el-dropdown-menu__item:focus {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.session-action-menu .el-dropdown-menu__item.session-action-danger,
.session-action-menu .el-dropdown-menu__item.session-action-danger:not(.is-disabled):hover {
  color: #f56c6c;
}

.session-action-menu .el-popper__arrow::before {
  background: #2a2a2a !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
</style>
