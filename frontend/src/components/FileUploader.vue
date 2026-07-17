<template>
  <!-- 文件上传：仅 md/txt、单文件 10MB、点击+拖拽、进度条、加载锁 -->
  <div
    class="file-uploader"
    v-loading="uploading"
    element-loading-text="文档上传中，请稍候"
  >
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      :disabled="disabled || uploading || !kbId"
      accept=".md,.txt"
      :on-change="onFileChange"
    >
      <div class="upload-tip">
        <p>点击或拖拽文件到此处上传</p>
        <p class="sub">仅支持 .md、.txt，单文件不超过 10MB</p>
      </div>
    </el-upload>

    <el-progress
      v-if="uploading || progress > 0"
      :percentage="progress"
      :stroke-width="10"
      style="margin-top: 12px"
    />
  </div>
</template>

<script setup>
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

function validateFile(file) {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXT.includes(ext)) {
    // 固定提示文案，页面不另写弹窗逻辑以外的自定义文案
    ElMessage.warning('仅支持 .md、.txt 格式文档上传')
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.warning('文件大小不可超过 10MB，请压缩后重新上传')
    return false
  }
  return true
}

async function onFileChange(uploadFile) {
  const raw = uploadFile?.raw
  if (!raw || props.disabled || props.uploading || !props.kbId) return
  if (!validateFile(raw)) return

  const formData = new FormData()
  formData.append('kb_id', String(props.kbId))
  formData.append('file', raw)

  emit('update:uploading', true)
  emit('update:progress', 0)

  try {
    const res = await uploadDocument(formData, (evt) => {
      if (!evt.total) return
      const percent = Math.round((evt.loaded / evt.total) * 100)
      emit('update:progress', percent)
      emit('progress', percent)
    })
    emit('update:progress', 100)
    emit('success', res.data)
  } catch (error) {
    // 业务异常交由全局 axios 拦截弹窗，此处仅回传失败事件刷新 UI
    emit('fail', error)
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
</style>
