<template>
  <el-dialog
    :model-value="modelValue"
    title="索引重建"
    width="480px"
    destroy-on-close
    :close-on-click-modal="!running"
    :close-on-press-escape="!running"
    :show-close="!running"
    @update:model-value="onVisible"
  >
    <p class="rb-title">知识库：{{ kbName || kbId }}</p>
    <p class="rb-msg">{{ message }}</p>
      <el-progress :percentage="progress" :stroke-width="12" />
    <template #footer>
      <el-button v-if="!running" type="primary" @click="close">关闭</el-button>
      <el-button v-else disabled>重建进行中…</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { rebuildKnowledgeBase, fetchRebuildStatus } from '@/api/kbIndex'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  kbId: { type: [String, Number], default: '' },
  kbName: { type: String, default: '' },
  /** 要带入重建的配置 */
  config: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'done', 'failed'])

const progress = ref(0)
const message = ref('')
const running = ref(false)
let pollTimer = null
let jobId = ''

function onVisible(v) {
  emit('update:modelValue', v)
  if (!v) stopPoll()
}

function close() {
  if (running.value) return
  stopPoll()
  emit('update:modelValue', false)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function start() {
  if (!props.kbId || !props.config) return
  running.value = true
  progress.value = 0
  message.value = props.config.create_snapshot
    ? '正在创建变更快照并提交重建…'
    : '正在提交重建任务…'
  try {
    const job = await rebuildKnowledgeBase(props.kbId, props.config)
    jobId = job.job_id
    progress.value = Number(job.progress) || 10
    message.value = job.message || '重建中…'
    if (job.status === 'completed' || job.status === 'failed') {
      finish(job)
      return
    }
    // Mock / 有 job_id 时轮询
    if (String(jobId).startsWith('job-') || String(jobId).includes('rebuild')) {
      pollTimer = setInterval(async () => {
        const st = await fetchRebuildStatus(props.kbId, jobId)
        if (!st) return
        progress.value = Number(st.progress) || progress.value
        message.value = st.message || message.value
        if (st.status === 'completed' || st.status === 'failed') {
          finish(st)
        }
      }, 700)
    } else {
      finish(job)
    }
  } catch (e) {
    running.value = false
    message.value = e?.msg || e?.message || '重建提交失败'
    progress.value = 0
    emit('failed')
    ElMessage.error(message.value)
  }
}

function finish(job) {
  stopPoll()
  running.value = false
  progress.value = Number(job.progress) || (job.status === 'completed' ? 100 : progress.value)
  message.value = job.message || (job.status === 'completed' ? '重建完成' : '重建失败')
  if (job.status === 'completed') {
    ElMessage.success(message.value)
    emit('done', job)
  } else {
    ElMessage.warning(message.value)
    emit('failed', job)
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      if (!props.config) {
        message.value = '缺少重建配置'
        running.value = false
        return
      }
      start()
    } else stopPoll()
  }
)

onBeforeUnmount(() => stopPoll())
</script>

<style scoped>
.rb-title {
  margin: 0 0 8px;
  font-weight: 600;
}
.rb-msg {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--text-color-regular, #606266);
  line-height: 1.5;
  min-height: 1.5em;
}
</style>
