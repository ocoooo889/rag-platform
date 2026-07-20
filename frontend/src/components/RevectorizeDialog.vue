<template>
  <el-dialog
    :model-value="modelValue"
    title="重新向量化"
    width="480px"
    destroy-on-close
    :close-on-click-modal="!busy"
    :close-on-press-escape="!busy"
    :show-close="!busy"
    @update:model-value="onVisible"
  >
    <div v-if="phase === 'confirm'" class="rz-body">
      <p class="rz-desc">
        将对文档「{{ filename || docId }}」重新入库并向量化。处理期间该文档不可用于纯向量检索。
      </p>
    </div>

    <div v-else class="rz-body">
      <p class="rz-status">{{ statusText }}</p>
      <el-progress
        v-if="percent != null"
        :percentage="percent"
        :stroke-width="10"
      />
      <p v-if="errorText" class="rz-error">{{ errorText }}</p>
    </div>

    <template #footer>
      <template v-if="phase === 'confirm'">
        <el-button @click="close">取消</el-button>
        <el-button type="primary" :loading="starting" @click="start">开始重新向量化</el-button>
      </template>
      <template v-else-if="phase === 'running'">
        <el-button disabled>处理中…</el-button>
      </template>
      <template v-else>
        <el-button type="primary" @click="close">关闭</el-button>
        <el-button v-if="phase === 'failed'" @click="retry">重试</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { reprocessDocument, fetchDocuments } from '@/api/doc'
import {
  DOC_STATUS,
  getDocStatusLabel,
  parseVectorProgress
} from '@/utils/docStatus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  docId: { type: [String, Number], default: '' },
  kbId: { type: [String, Number], default: '' },
  filename: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'done', 'failed'])

const phase = ref('confirm') // confirm | running | done | failed
const starting = ref(false)
const percent = ref(null)
const statusText = ref('')
const errorText = ref('')
let pollTimer = null
let missCount = 0

const busy = computed(() => phase.value === 'running' || starting.value)

function onVisible(v) {
  emit('update:modelValue', v)
  if (!v) stopPoll()
}

function close() {
  if (busy.value) return
  stopPoll()
  emit('update:modelValue', false)
}

function resetUi() {
  phase.value = 'confirm'
  starting.value = false
  percent.value = null
  statusText.value = ''
  errorText.value = ''
  missCount = 0
}

function stopPoll() {
  if (pollTimer != null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function findDocRow() {
  if (!props.kbId || !props.docId) return null
  const res = await fetchDocuments({
    kb_id: props.kbId,
    page: 1,
    page_size: 200
  })
  const raw = res?.data ?? res
  const list = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
  return list.find((d) => String(d.id) === String(props.docId)) || null
}

function applyDocState(row) {
  if (!row) {
    missCount += 1
    if (missCount >= 8) {
      stopPoll()
      phase.value = 'failed'
      errorText.value = '未找到文档状态，请刷新文档列表后重试'
      emit('failed')
    }
    return
  }
  missCount = 0
  const st = String(row.status || '').toLowerCase()
  if (st === DOC_STATUS.PENDING) {
    statusText.value = '排队等待处理…'
    percent.value = 0
    return
  }
  if (st === DOC_STATUS.PROCESSING) {
    const p = parseVectorProgress(row.error_message)
    if (p) {
      percent.value = p.percent
      statusText.value = `向量化中 ${p.current}/${p.total}`
    } else {
      percent.value = percent.value ?? 10
      statusText.value = getDocStatusLabel(st)
    }
    return
  }
  if (st === DOC_STATUS.COMPLETED) {
    percent.value = 100
    statusText.value = '重新向量化完成'
    phase.value = 'done'
    stopPoll()
    emit('done', row)
    ElMessage.success('重新向量化完成')
    return
  }
  if (st === DOC_STATUS.DEGRADED || st === DOC_STATUS.FAILED) {
    percent.value = null
    statusText.value = getDocStatusLabel(st)
    errorText.value = row.error_message || '处理未完全成功'
    phase.value = 'failed'
    stopPoll()
    emit('failed', row)
  }
}

function startPoll() {
  stopPoll()
  missCount = 0
  pollTimer = setInterval(async () => {
    try {
      const row = await findDocRow()
      applyDocState(row)
    } catch {
      missCount += 1
      if (missCount >= 8) {
        stopPoll()
        phase.value = 'failed'
        errorText.value = '轮询文档状态失败'
        emit('failed')
      }
    }
  }, 2000)
}

async function start() {
  if (!props.docId) {
    ElMessage.warning('缺少文档 ID')
    return
  }
  starting.value = true
  errorText.value = ''
  try {
    await reprocessDocument(props.docId)
    phase.value = 'running'
    statusText.value = '已提交，正在处理…'
    percent.value = 0
    startPoll()
    // 立即拉一次
    const row = await findDocRow()
    applyDocState(row)
  } catch {
    phase.value = 'failed'
    errorText.value = '提交重新向量化失败'
    emit('failed')
  } finally {
    starting.value = false
  }
}

function retry() {
  resetUi()
  start()
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) resetUi()
    else stopPoll()
  }
)

onBeforeUnmount(() => stopPoll())
</script>

<style scoped>
.rz-body {
  min-height: 72px;
}
.rz-desc {
  margin: 0;
  line-height: 1.6;
  color: var(--text-color-regular, #606266);
}
.rz-status {
  margin: 0 0 12px;
  font-size: 14px;
}
.rz-error {
  margin: 12px 0 0;
  color: var(--el-color-danger);
  font-size: 13px;
  line-height: 1.5;
}
</style>
