<template>

  <!-- 支持批量：md/txt、单文件 10MB、点击+拖拽、进度条 -->

  <!-- 上传弹窗内容：多文件 md/txt、单文件 ≤10MB -->

  <div
    class="file-uploader"
    v-loading="uploading"
    element-loading-text="文档上传中，请稍候"
  >
    <p class="upload-lead">点击或拖拽文件到此处上传</p>

    <el-upload
      class="upload-drop"
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

      :before-upload="() => false"
    >
      <div class="drop-inner">
        <span class="drop-badge">支持多选</span>
        <el-icon class="drop-icon" :size="48"><Document /></el-icon>
        <p class="drop-hint">仅支持 .md / .txt 格式文件，单个文件大小不超过 10MB</p>
      </div>
    </el-upload>

    <ul v-if="fileList.length" class="pending-list">
      <li v-for="item in fileList" :key="item.uid" class="pending-item">
        <div class="pending-item__icon" :class="fileIconClass(item.name)">
          <el-icon :size="18"><Document /></el-icon>
        </div>
        <div class="pending-item__text">
          <span class="pending-item__name">{{ item.name }}</span>
          <span class="pending-item__status">待上传</span>
        </div>
        <button
          type="button"
          class="pending-item__remove"
          :disabled="uploading"
          aria-label="移除文件"
          @click="removeFile(item.uid)"
        >
          <el-icon :size="14"><Close /></el-icon>
        </button>
      </li>
    </ul>


    <el-progress
      v-if="uploading || progress > 0"
      :percentage="progress"
      :stroke-width="8"
      class="upload-progress"
    />
    <p v-if="uploading && totalInBatch > 0" class="batch-hint">
      正在上传第 {{ currentIndex }} / {{ totalInBatch }} 个文件
    </p>

    <div class="upload-footer">
      <el-button class="footer-btn footer-btn--cancel" :disabled="uploading" @click="handleCancel">
        取消
      </el-button>
      <el-button
        type="primary"
        class="footer-btn footer-btn--submit"
        :disabled="disabled || !kbId || !fileList.length"
        :loading="uploading"
        @click="startUpload"
      >
        开始上传
      </el-button>
    </div>
  </div>
</template>

<script setup>

import { computed, ref } from 'vue'

import { ref } from 'vue'
import { Close, Document } from '@element-plus/icons-vue'

import { ElMessage } from 'element-plus'
import { uploadDocument } from '@/api/doc'

const props = defineProps({
  kbId: { type: [Number, String], default: null },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  progress: { type: Number, default: 0 }
})

const emit = defineEmits([
  'success',
  'fail',
  'progress',
  'cancel',
  'update:uploading',
  'update:progress'
])

const MAX_SIZE = 10 * 1024 * 1024
const ALLOWED_EXT = ['md', 'txt']
const fileList = ref([])
const queue = ref([])

const pendingCount = computed(() => queue.value.length)

const fileList = ref([])
const currentIndex = ref(0)
const totalInBatch = ref(0)

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

function fileIconClass(name = '') {
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (ext === 'txt') return 'pending-item__icon--txt'
  return 'pending-item__icon--md'
}

function onFileChange(uploadFile, uploadFiles) {
  if (props.disabled || props.uploading || !props.kbId) return

  const valid = []
  const seen = new Set()
  for (const item of uploadFiles || []) {
    const raw = item.raw
    if (!raw) continue
    if (!validateFile(raw)) continue
    const key = `${raw.name}::${raw.size}`
    if (seen.has(key)) continue
    seen.add(key)
    valid.push({
      name: raw.name,
      size: raw.size,
      raw,
      status: 'ready',
      uid: item.uid
    })
  }
  fileList.value = valid
}

function removeFile(uid) {
  fileList.value = fileList.value.filter((f) => f.uid !== uid)
}

function clearFiles() {
  fileList.value = []
  emit('update:progress', 0)
}

function handleCancel() {
  if (props.uploading) return
  clearFiles()
  emit('cancel')
}

async function startUpload() {
  if (props.disabled || props.uploading || !props.kbId) return
  const queue = fileList.value.filter((f) => f.raw)
  if (!queue.length) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }


  emit('update:uploading', true)
  emit('update:progress', 0)
  totalInBatch.value = queue.length
  currentIndex.value = 0

  const okResults = []
  const failNames = []

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

    for (let i = 0; i < queue.length; i += 1) {
      currentIndex.value = i + 1
      const item = queue[i]
      const formData = new FormData()
      formData.append('kb_id', String(props.kbId))
      formData.append('file', item.raw)

      try {
        const res = await uploadDocument(formData, (evt) => {
          if (!evt.total) return
          const filePct = Math.round((evt.loaded / evt.total) * 100)
          const overall = Math.round(((i + filePct / 100) / queue.length) * 100)
          emit('update:progress', Math.min(overall, 99))
          emit('progress', overall)
        })
        okResults.push(res.data)
      } catch (error) {
        failNames.push(item.name || `文件${i + 1}`)
        emit('fail', error)
      }
    }

    emit('update:progress', 100)

    if (okResults.length) {
      ElMessage.success(
        failNames.length
          ? `成功上传 ${okResults.length} 个，失败 ${failNames.length} 个`
          : `成功上传 ${okResults.length} 个文件`
      )
      emit('success', okResults)
    } else if (failNames.length) {
      ElMessage.error('全部上传失败，请检查文件后重试')
    }


    fileList.value = []
  } finally {
    emit('update:uploading', false)
    currentIndex.value = 0
    totalInBatch.value = 0
  }
}

defineExpose({ clearFiles })
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.upload-lead {
  margin: 0 0 12px;
  text-align: center;
  font-size: 14px;
  color: var(--text-color-primary);
}

.upload-drop {
  width: 100%;
}

.upload-drop :deep(.el-upload) {
  width: 100%;
}

.upload-drop :deep(.el-upload-dragger) {
  width: 100%;
  height: auto;
  padding: 0;
  border: none;
  background: transparent;
}

.drop-inner {
  position: relative;
  padding: 32px 20px 28px;
  border-radius: 12px;
  border: 1px dashed #a0cfff;
  background: #f5f9ff;
}

.drop-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 2px 10px;
  font-size: 12px;
  color: var(--color-primary);
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  background: #fff;
}

.drop-icon {
  color: var(--color-primary);
  margin-bottom: 12px;
}

.drop-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-color-secondary);
}

.pending-list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.pending-item__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.pending-item__icon--md {
  background: #f0f9eb;
  color: #67c23a;
}

.pending-item__icon--txt {
  background: #fef0f0;
  color: #f56c6c;
}

.pending-item__text {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: var(--text-color-primary);
}

.pending-item__name {
  margin-right: 6px;
}

.pending-item__status {
  color: var(--text-color-secondary);
  font-size: 13px;
}

.pending-item__remove {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #dcdfe6;
  border-radius: 50%;
  background: #fff;
  color: var(--text-color-secondary);
  cursor: pointer;
}

.pending-item__remove:hover:not(:disabled) {
  border-color: #c0c4cc;
  color: var(--text-color-primary);
}

.pending-item__remove:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.upload-progress {
  margin-top: 16px;
}

.batch-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-color-secondary);
  text-align: center;
}

.upload-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 4px;
}

.footer-btn {
  min-width: 88px;
  border-radius: 8px;
}

.footer-btn--cancel {
  border-color: #dcdfe6;
  color: var(--text-color-regular);
}

.footer-btn--submit {
  min-width: 96px;
}

.actions {
  margin-top: 12px;
}
</style>
