<template>
  <!-- 支持批量：md/txt、单文件 10MB、点击+拖拽、进度条 -->
  <div
    class="file-uploader"
    v-loading="uploading"
    element-loading-text="文档上传中，请稍候"
  >
    <el-upload
      drag
      multiple
      :auto-upload="false"
      :show-file-list="true"
      :disabled="disabled || uploading || !kbId"
      accept=".md,.txt"
      :on-change="onFileChange"
      :on-remove="onRemove"
      :file-list="fileList"
    >
      <div class="upload-tip">
        <p>点击或拖拽文件到此处上传（支持多选）</p>
        <p class="sub">仅支持 .md、.txt，单文件不超过 10MB</p>
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
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDocument } from '@/api/doc'

const props = defineProps({
  kbId: { type: [Number, String], default: null },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  progress: { type: Number, default: 0 }
})

const emit = defineEmits(['success', 'fail', 'progress', 'update:uploading', 'update:progress'])

const MAX_SIZE = 10 * 1024 * 1024
const ALLOWED_EXT = ['md', 'txt']
const fileList = ref([])
const queue = ref([])

const pendingCount = computed(() => queue.value.length)

function validateFile(file) {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXT.includes(ext)) {
    ElMessage.warning(`「${name}」格式不支持，仅支持 .md、.txt`)
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

async function uploadOne(uploadFile) {
  const raw = uploadFile.raw
  const formData = new FormData()
  formData.append('kb_id', String(props.kbId))
  formData.append('file', raw)
  return uploadDocument(formData, (evt) => {
    if (!evt.total) return
    // 单文件进度映射到总体时由外层汇总
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
