<template>
  <!-- 多格式上传 + 切分策略来自 GET /api/split-strategies（无本地假列表兜底） -->
  <div
    class="file-uploader"
    v-loading="uploading || strategiesLoading"
    :element-loading-text="strategiesLoading ? '加载切分策略…' : '文档上传中，请稍候'"
  >
    <el-alert
      v-if="strategiesError"
      type="error"
      :closable="false"
      show-icon
      class="mb8"
      :title="strategiesError"
    />

    <div class="split-panel">
      <div class="split-row">
        <span class="split-label">切分方式</span>
        <el-select
          v-model="splitStrategy"
          placeholder="选择切分方式"
          style="width: 260px"
          :disabled="disabled || uploading || !strategyOptions.length"
          @change="onStrategyChange"
        >
          <el-option
            v-for="item in strategyOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          >
            <div class="opt-main">
              {{ item.label }}
              <span v-if="item.is_default" class="opt-default">默认</span>
            </div>
            <div class="opt-desc">{{ item.desc }}</div>
          </el-option>
        </el-select>
      </div>

      <div class="split-row params">
        <span class="split-label">块大小</span>
        <el-input-number
          v-model="chunkSize"
          :min="sizeMin"
          :max="sizeMax"
          :step="50"
          :disabled="disabled || uploading || !currentStrategy"
        />
        <span class="split-label">重叠</span>
        <el-input-number
          v-model="chunkOverlap"
          :min="overlapMin"
          :max="Math.max(overlapMin, (chunkSize || 1) - 1)"
          :step="10"
          :disabled="disabled || uploading || !currentStrategy"
        />
      </div>

      <div v-if="splitStrategy === 'parent_child'" class="split-row params">
        <span class="split-label">父块大小</span>
        <el-input-number
          v-model="parentChunkSize"
          :min="parentSizeMin"
          :max="parentSizeMax"
          :step="100"
          :disabled="disabled || uploading"
        />
        <span class="split-label">父块重叠</span>
        <el-input-number
          v-model="parentChunkOverlap"
          :min="0"
          :max="Math.max(0, (parentChunkSize || 1) - 1)"
          :step="20"
          :disabled="disabled || uploading"
        />
      </div>

      <div v-if="splitStrategy === 'semantic'" class="split-row params">
        <span class="split-label">语义阈值</span>
        <el-input-number
          v-model="semanticThreshold"
          :min="semanticMin"
          :max="semanticMax"
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
      :disabled="disabled || uploading || !kbId || !strategyOptions.length"
      accept=".md,.markdown,.txt,.pdf,.docx,.html,.htm,.csv"
      :on-change="onFileChange"
      :on-remove="onRemove"
      :file-list="fileList"
    >
      <div class="upload-tip">
        <p>点击或拖拽文件到此处上传（支持多选）</p>
        <p class="sub">支持 {{ ALLOWED_LABEL }}，单文件不超过 10MB</p>
      </div>
    </el-upload>

    <div v-if="pendingCount > 0" class="actions">
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="disabled || !kbId || uploading || !splitStrategy"
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
import { uploadDocument } from '@/api/doc'
import { useSplitStrategies } from '@/composables/useSplitStrategies'

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

const {
  loading: strategiesLoading,
  error: strategiesError,
  items: strategyOptions,
  defaultItem,
  load: loadStrategies,
  findByValue
} = useSplitStrategies()

const splitStrategy = ref('')
const chunkSize = ref(Number.NaN)
const chunkOverlap = ref(Number.NaN)
const parentChunkSize = ref(Number.NaN)
const parentChunkOverlap = ref(Number.NaN)
const semanticThreshold = ref(Number.NaN)

const fileList = ref([])
const queue = ref([])

const pendingCount = computed(() => queue.value.length)
const currentStrategy = computed(() => findByValue(splitStrategy.value) || defaultItem.value)
const currentStrategyDesc = computed(() => currentStrategy.value?.desc || '')

const sizeMin = computed(() => currentStrategy.value?.chunk_size_min ?? 100)
const sizeMax = computed(() => currentStrategy.value?.chunk_size_max ?? 2000)
const overlapMin = computed(() => currentStrategy.value?.chunk_overlap_min ?? 0)
const parentSizeMin = computed(() => currentStrategy.value?.parent_chunk_size_min ?? 300)
const parentSizeMax = computed(() => currentStrategy.value?.parent_chunk_size_max ?? 8000)
const semanticMin = computed(() => currentStrategy.value?.semantic_threshold_min ?? 0.1)
const semanticMax = computed(() => currentStrategy.value?.semantic_threshold_max ?? 0.95)

function applyStrategyParams(item) {
  if (!item) return
  splitStrategy.value = item.value
  chunkSize.value = item.default_chunk_size
  chunkOverlap.value = item.default_chunk_overlap
  if (item.default_parent_chunk_size != null) {
    parentChunkSize.value = item.default_parent_chunk_size
  }
  if (item.default_parent_chunk_overlap != null) {
    parentChunkOverlap.value = item.default_parent_chunk_overlap
  }
  if (item.default_semantic_threshold != null) {
    semanticThreshold.value = item.default_semantic_threshold
  }
}

function onStrategyChange(val) {
  const item = findByValue(val)
  if (item) applyStrategyParams(item)
}

onMounted(async () => {
  try {
    await loadStrategies()
    applyStrategyParams(defaultItem.value)
  } catch {
    /* strategiesError 已展示 */
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

function onRemove(uploadFile, uploadFiles) {
  fileList.value = uploadFiles
  queue.value = queue.value.filter((f) => f.uid !== uploadFile.uid)
}

async function startUpload() {
  if (!props.kbId) {
    ElMessage.warning('请先选择知识库')
    return
  }
  if (!splitStrategy.value || Number.isNaN(chunkSize.value)) {
    ElMessage.warning('请等待切分策略加载完成')
    return
  }
  if (chunkOverlap.value >= chunkSize.value) {
    ElMessage.warning('切片重叠必须小于文本块大小')
    return
  }

  const files = [...queue.value]
  if (!files.length) return

  emit('update:uploading', true)
  emit('update:progress', 0)

  let ok = 0
  let fail = 0
  try {
    for (let i = 0; i < files.length; i++) {
      const item = files[i]
      const formData = new FormData()
      formData.append('kb_id', String(props.kbId))
      formData.append('file', item.raw)
      formData.append('split_strategy', splitStrategy.value)
      formData.append('chunk_size', String(chunkSize.value))
      formData.append('chunk_overlap', String(chunkOverlap.value))
      if (splitStrategy.value === 'parent_child' && !Number.isNaN(parentChunkSize.value)) {
        formData.append('parent_chunk_size', String(parentChunkSize.value))
        formData.append('parent_chunk_overlap', String(parentChunkOverlap.value || 0))
      }
      if (splitStrategy.value === 'semantic' && !Number.isNaN(semanticThreshold.value)) {
        formData.append('semantic_threshold', String(semanticThreshold.value))
      }

      try {
        const res = await uploadDocument(formData, (evt) => {
          if (!evt.total) return
          const base = (i / files.length) * 100
          const part = (evt.loaded / evt.total) * (100 / files.length)
          const p = Math.min(99, Math.round(base + part))
          emit('update:progress', p)
          emit('progress', p)
        })
        ok += 1
        emit('success', res?.data)
      } catch (e) {
        fail += 1
        emit('fail', e)
        ElMessage.error(e?.msg || e?.message || `「${item.name}」上传失败`)
      }
      emit('update:progress', Math.round(((i + 1) / files.length) * 100))
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
.mb8 {
  margin-bottom: 8px;
}
.file-uploader {
  width: 100%;
}
.split-panel {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-card, 8px);
  background: var(--bg-color-secondary, var(--bg-color-page-soft, transparent));
  color: var(--text-color-primary);
}
.split-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.split-label {
  font-size: 13px;
  color: var(--text-color-secondary);
  min-width: 64px;
}
.params .split-label {
  min-width: 56px;
}
.opt-main {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-color-primary);
}
.opt-default {
  font-size: 11px;
  color: var(--el-color-primary);
}
.opt-desc {
  font-size: 11px;
  color: var(--text-color-secondary);
  line-height: 1.3;
  max-width: 320px;
  white-space: normal;
}
.strategy-hint,
.hint-inline {
  margin: 0;
  font-size: 12px;
  color: var(--text-color-secondary);
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
