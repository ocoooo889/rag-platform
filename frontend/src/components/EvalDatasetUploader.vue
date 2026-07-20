<template>
  <!-- 评测数据集上传：点击/拖拽 + 进度条 -->
  <div class="eval-uploader">
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="true"
      :limit="1"
      :disabled="disabled || uploading"
      accept=".json,.jsonl,.csv,.txt"
      :on-change="onChange"
      :on-remove="onRemove"
      :on-exceed="onExceed"
      :file-list="fileList"
    >
      <div class="upload-tip">
        <p>点击或拖拽数据集到此处</p>
        <p class="sub">支持 .json / .jsonl / .csv / .txt，单文件 ≤ 20MB</p>
      </div>
    </el-upload>

    <el-progress
      v-if="uploading || progress > 0"
      class="progress"
      :percentage="progress"
      :stroke-width="12"
      :status="progress >= 100 ? 'success' : undefined"
    />

    <p v-if="fileName" class="file-name">已选：{{ fileName }}</p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  /** 外部清空时重置 */
  resetKey: { type: [Number, String], default: 0 }
})

const emit = defineEmits(['change', 'clear'])

const MAX_SIZE = 20 * 1024 * 1024
const ALLOWED = ['json', 'jsonl', 'csv', 'txt']
const fileList = ref([])
const picked = ref(null)

const fileName = computed(() => picked.value?.name || '')

watch(
  () => props.resetKey,
  () => {
    fileList.value = []
    picked.value = null
    emit('clear')
  }
)

function validate(file) {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED.includes(ext)) {
    ElMessage.warning(`不支持「.${ext}」，请上传 json/jsonl/csv/txt`)
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.warning('文件超过 20MB')
    return false
  }
  return true
}

function onChange(uploadFile, uploadFiles) {
  const raw = uploadFile.raw
  if (!raw || !validate(raw)) {
    fileList.value = []
    picked.value = null
    emit('clear')
    return
  }
  fileList.value = uploadFiles.slice(-1)
  picked.value = raw
  emit('change', raw)
}

function onRemove() {
  fileList.value = []
  picked.value = null
  emit('clear')
}

function onExceed() {
  ElMessage.warning('一次仅可选择一个数据集文件')
}

defineExpose({
  getFile: () => picked.value
})
</script>

<style scoped>
.eval-uploader {
  width: 100%;
}
.upload-tip {
  color: var(--admin-text-muted, #909399);
  line-height: 1.5;
}
.upload-tip .sub {
  margin-top: 4px;
  font-size: 12px;
}
.progress {
  margin-top: 12px;
}
.file-name {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--admin-text-muted, #909399);
}
</style>
