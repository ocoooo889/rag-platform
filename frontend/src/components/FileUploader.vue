<template>
  <!-- 支持批量：md/txt/pdf/docx/html/csv、单文件 10MB、切分策略可选、点击+拖拽、进度条 -->
  <div
    class="file-uploader"
    v-loading="uploading"
    element-loading-text="文档上传中，请稍候"
  >
    <div class="split-panel">
      <div class="split-row">
        <span class="split-label">切分方式</span>
        <el-select
          v-model="splitStrategy"
          placeholder="选择切分方式"
          style="width: 260px"
          :disabled="disabled || uploading"
        >
          <el-option
            v-for="item in strategyOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          >
            <div class="opt-main">{{ item.label }}</div>
            <div class="opt-desc">{{ item.desc }}</div>
          </el-option>
        </el-select>
      </div>

      <div class="split-row params">
        <span class="split-label">块大小</span>
        <el-input-number
          v-model="chunkSize"
          :min="100"
          :max="4000"
          :step="50"
          :disabled="disabled || uploading"
        />
        <span class="split-label">重叠</span>
        <el-input-number
          v-model="chunkOverlap"
          :min="0"
          :max="1000"
          :step="10"
          :disabled="disabled || uploading"
        />
      </div>

      <div v-if="splitStrategy === 'parent_child'" class="split-row params">
        <span class="split-label">父块大小</span>
        <el-input-number
          v-model="parentChunkSize"
          :min="300"
          :max="8000"
          :step="100"
          :disabled="disabled || uploading"
        />
        <span class="split-label">父块重叠</span>
        <el-input-number
          v-model="parentChunkOverlap"
          :min="0"
          :max="2000"
          :step="20"
          :disabled="disabled || uploading"
        />
      </div>

      <div v-if="splitStrategy === 'semantic'" class="split-row params">
        <span class="split-label">语义阈值</span>
        <el-input-number
          v-model="semanticThreshold"
          :min="0.1"
          :max="0.95"
          :step="0.05"
          :precision="2"
          :disabled="disabled || uploading"
        />
        <span class="hint-inline">越低越容易切开（入库更慢）</span>
      </div>

      <p class="strategy-hint">{{ currentStrategyDesc }}</p>
    </div>

    <el-upload
      drag
      multiple
      :auto-upload="false"
      :show-file-list="true"
      :disabled="disabled || uploading || !kbId"
      accept=".md,.markdown,.txt,.pdf,.docx,.html,.htm,.csv"
      :on-change="onFileChange"
      :on-remove="onRemove"
      :file-list="fileList"
    >
      <div class="upload-tip">
        <p>点击或拖拽文件到此处上传（支持多选）</p>
        <p class="sub">支持 .md / .txt / .pdf / .docx / .html / .csv，单文件不超过 10MB</p>
      </div>
    </el-upload>

    <div v-if="pendingCount > 0" class="actions">
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="disabled || !kbId || uploading"
        @click="startUpload"
      >
        开始上传（{{ pendingCount }} 个文件）
      </el-button>
    </div>

    <el-progress
      v-if="uploading || progress > 0"
      :percentage="progress"
      :stroke-width="10"
      style="margin-top: 12px"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSplitStrategies, uploadDocument } from '@/api/doc'

const props = defineProps({
  kbId: { type: [Number, String], default: null },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  progress: { type: Number, default: 0 }
})

const emit = defineEmits(['success', 'fail', 'progress', 'update:uploading', 'update:progress'])

const MAX_SIZE = 10 * 1024 * 1024
const ALLOWED_EXT = ['md', 'markdown', 'txt', 'pdf', 'docx', 'html', 'htm', 'csv']
const ALLOWED_LABEL = '.md / .txt / .pdf / .docx / .html / .csv'

const DEFAULT_STRATEGIES = [
  { value: 'recursive', label: '递归切分', desc: '优先按标题/段落/句子边界切，默认兼容 Day1' },
  { value: 'fixed', label: '固定长度', desc: '按固定字符数硬切，适合快速对比实验' },
  { value: 'markdown_header', label: '按标题切分', desc: '按 # / ## / ### 章节切，适合手册、规范' },
  { value: 'paragraph', label: '按段落切分', desc: '按空行分段，过长段落再二次切' },
  { value: 'sentence', label: '按句子切分', desc: '按句号等断句后拼到目标长度' },
  { value: 'semantic', label: '语义切分', desc: '按句子语义相似度找主题边界（入库较慢）' },
  { value: 'parent_child', label: '父子块切分', desc: '子块向量检索，入库内容用父块上下文' }
]

const strategyOptions = ref([...DEFAULT_STRATEGIES])
const splitStrategy = ref('recursive')
const chunkSize = ref(500)
const chunkOverlap = ref(50)
const parentChunkSize = ref(1500)
const parentChunkOverlap = ref(100)
const semanticThreshold = ref(0.55)

const fileList = ref([])
const queue = ref([])

const pendingCount = computed(() => queue.value.length)
const currentStrategyDesc = computed(() => {
  const hit = strategyOptions.value.find((s) => s.value === splitStrategy.value)
  return hit?.desc || ''
})

onMounted(async () => {
  try {
    const res = await fetchSplitStrategies()
    const items = res?.data?.items || res?.data || []
    if (Array.isArray(items) && items.length) {
      strategyOptions.value = items
    }
  } catch {
    // 后端未就绪时用本地默认列表
  }
})

function validateFile(file) {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXT.includes(ext)) {
    ElMessage.warning(`「${name}」格式不支持，仅支持 ${ALLOWED_LABEL}`)
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.warning(`「${name}」超过 10MB，请压缩后重新上传`)
    return false
  }
  return true
}

function onFileChange(uploadFile, uploadFiles) {
  fileList.value = uploadFiles
  const raw = uploadFile?.raw
  if (!raw || !validateFile(raw)) {
    fileList.value = uploadFiles.filter((f) => f.uid !== uploadFile.uid)
    return
  }
  if (!queue.value.some((f) => f.uid === uploadFile.uid)) {
    queue.value.push(uploadFile)
  }
}

function onRemove(uploadFile) {
  queue.value = queue.value.filter((f) => f.uid !== uploadFile.uid)
}

function buildFormData(raw) {
  const formData = new FormData()
  formData.append('kb_id', String(props.kbId))
  formData.append('file', raw)
  formData.append('split_strategy', splitStrategy.value || 'recursive')
  formData.append('chunk_size', String(chunkSize.value || 500))
  formData.append('chunk_overlap', String(chunkOverlap.value ?? 50))
  if (splitStrategy.value === 'parent_child') {
    formData.append('parent_chunk_size', String(parentChunkSize.value || 1500))
    formData.append('parent_chunk_overlap', String(parentChunkOverlap.value ?? 100))
  }
  if (splitStrategy.value === 'semantic') {
    formData.append('semantic_threshold', String(semanticThreshold.value ?? 0.55))
  }
  return formData
}

async function uploadOne(uploadFile) {
  const formData = buildFormData(uploadFile.raw)
  return uploadDocument(formData, (evt) => {
    if (!evt.total) return
  })
}

async function startUpload() {
  if (props.disabled || props.uploading || !props.kbId || !queue.value.length) return

  emit('update:uploading', true)
  emit('update:progress', 0)

  const files = [...queue.value]
  let ok = 0
  let fail = 0

  try {
    for (let i = 0; i < files.length; i++) {
      const item = files[i]
      try {
        const res = await uploadOne(item)
        ok += 1
        emit('success', res.data)
      } catch (error) {
        fail += 1
        emit('fail', error)
      }
      emit('update:progress', Math.round(((i + 1) / files.length) * 100))
      emit('progress', Math.round(((i + 1) / files.length) * 100))
    }

    if (ok > 0 && fail === 0) {
      ElMessage.success(`成功上传 ${ok} 个文档，正在后台处理`)
    } else if (ok > 0 && fail > 0) {
      ElMessage.warning(`成功 ${ok} 个，失败 ${fail} 个`)
    } else if (fail > 0) {
      ElMessage.error('文档上传失败，请检查后重试')
    }

    queue.value = []
    fileList.value = []
  } finally {
    emit('update:uploading', false)
  }
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.split-panel {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-card, 8px);
  /* 优先主题 secondary；未定义时回退 page-soft，避免夜间白底 */
  background: var(--bg-color-secondary, var(--bg-color-page-soft, transparent));
  color: var(--text-color-primary);
}

.split-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
}

.split-row.params {
  margin-top: 4px;
}

.split-label {
  font-size: 13px;
  color: var(--text-color-secondary);
  min-width: 64px;
}

.strategy-hint,
.hint-inline {
  margin: 0;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.opt-main {
  font-size: 13px;
  color: var(--text-color-primary);
}

.opt-desc {
  font-size: 11px;
  color: var(--text-color-secondary);
  line-height: 1.3;
  max-width: 320px;
  white-space: normal;
}

.upload-tip p {
  margin: 0;
  color: var(--text-color-primary);
}

.upload-tip .sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.actions {
  margin-top: 12px;
}
</style>
