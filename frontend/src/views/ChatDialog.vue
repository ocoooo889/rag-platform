<template>
  <div class="chat-dialog" v-loading="chatStore.loading" element-loading-text="加载中...">
    <!-- 左侧会话列表 -->
    <aside class="session-panel">
      <div class="session-panel__header">
        <span>会话列表</span>
        <!-- 无可用知识库时，隐藏所有新建会话入口 -->
        <AppButton
          v-if="hasKb"
          type="primary"
          text="新建会话"
          :loading="creating"
          loading-mode="normal"
          @click="onCreateSession"
        />
      </div>

      <EmptyState v-if="!chatStore.sessions.length" type="chat" />

      <ul v-else class="session-list">
        <li
          v-for="item in chatStore.sessions"
          :key="item.session_id"
          class="session-item"
          :class="{ active: item.session_id === chatStore.currentSessionId }"
          @click="onSwitchSession(item.session_id)"
        >
          <div class="session-item__title">{{ item.title || '未命名会话' }}</div>
          <AppButton
            type="danger"
            text="删除"
            link
            @click.stop="openDelete(item.session_id)"
          />
        </li>
      </ul>
    </aside>

    <!-- 右侧对话区 -->
    <section class="chat-panel">
      <div class="chat-panel__header">
        <div class="kb-select">
          <span>知识库范围</span>
          <el-select
            v-model="chatStore.selectedKbId"
            placeholder="请选择知识库"
            style="width: 240px"
            :disabled="chatStore.streaming"
          >
            <el-option
              v-for="kb in kbStore.list"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </div>
        <AppButton
          v-if="hasKb"
          type="primary"
          text="新建会话"
          :loading="creating"
          loading-mode="normal"
          @click="onCreateSession"
        />
      </div>

      <EmptyState v-if="!hasKb" type="kb" tip="暂无知识库，无法发起智能对话" />

      <template v-else>
        <div class="message-list" ref="messageListRef">
          <EmptyState
            v-if="!chatStore.messages.length && !chatStore.streaming"
            type="chat"
          />
          <ChatBubble
            v-for="(msg, index) in chatStore.messages"
            :key="`${msg.role}-${index}`"
            :role="msg.role"
            :content="msg.content"
            :sources="msg.sources || []"
          />
        </div>

        <!-- 无知识库时隐藏提问输入框；有知识库才展示 -->
        <div class="composer">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            maxlength="1000"
            placeholder="请输入问题，Enter 发送，Shift+Enter 换行"
            :disabled="chatStore.streaming || !chatStore.currentSessionId"
            @keydown.enter.exact.prevent="onSend"
          />
          <AppButton
            type="primary"
            text="发送"
            :loading="chatStore.streaming"
            loading-mode="sse"
            :disabled="!canSend"
            :title="sendDisabledTip"
            @click="onSend"
          />
        </div>
      </template>
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
import { useKbStore } from '@/stores/kb'
import { useChatStore } from '@/stores/chat'
import AppButton from '@/components/AppButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChatBubble from '@/components/ChatBubble.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const kbStore = useKbStore()
const chatStore = useChatStore()

const question = ref('')
const creating = ref(false)
const deleting = ref(false)
const deleteVisible = ref(false)
const deletingId = ref(null)
const messageListRef = ref(null)

const hasKb = computed(() => kbStore.list.length > 0)
const canSend = computed(
  () =>
    hasKb.value &&
    !!chatStore.selectedKbId &&
    !!chatStore.currentSessionId &&
    !!question.value.trim() &&
    !chatStore.streaming
)

const sendDisabledTip = computed(() => {
  if (!hasKb.value) return '无操作权限：暂无可用知识库'
  if (!chatStore.selectedKbId) return '请先选择知识库'
  if (!chatStore.currentSessionId) return '请先新建或选择会话'
  if (!question.value.trim()) return '请输入问题'
  return '发送问题'
})

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

async function initPage() {
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (kbStore.selectedKbId) {
      chatStore.selectedKbId = kbStore.selectedKbId
    } else if (kbStore.list.length) {
      chatStore.selectedKbId = kbStore.list[0].id
    }
    // 有知识库才拉取会话；无知识库隐藏新建入口与输入框
    if (hasKb.value) {
      await chatStore.loadSessions()
    }
  } catch (e) {
    // 全局 axios 处理
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
    // session_id 由后端返回 UUID 字符串，前端不做类型转换
    await chatStore.createSession({ kb_id: chatStore.selectedKbId })
  } catch (e) {
    // 全局 axios 处理
  } finally {
    creating.value = false
  }
}

async function onSwitchSession(sessionId) {
  try {
    // switchSession 内部会 Abort 当前 SSE
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

async function onSend() {
  if (!canSend.value) return
  const text = question.value.trim()
  question.value = ''
  try {
    // 流式入参携带 session_id；历史拼接与 10 轮截断由后端完成
    await chatStore.sendQuestion(text)
  } catch (e) {
    // code5002 等由 store / 全局拦截兜底
  }
}

onMounted(() => {
  initPage()
})

onUnmounted(() => {
  // 页面销毁时彻底中断 SSE，避免后台持续推送
  chatStore.abortCurrentStream()
})
</script>

<style scoped>
.chat-dialog {
  display: flex;
  height: calc(100vh - 120px);
  min-height: 520px;
  border: 1px solid var(--border-color);
  background: var(--bg-color-page);
}

.session-panel {
  width: 260px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-color-card);
}

.session-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-color-primary);
  font-weight: 600;
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow: auto;
  flex: 1;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  margin-bottom: 6px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-color-regular);
}

.session-item:hover,
.session-item.active {
  background: var(--bg-color-hover);
  color: var(--color-primary);
}

.session-item__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.kb-select {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-color-primary);
}

.message-list {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.composer {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--border-color);
}
</style>
