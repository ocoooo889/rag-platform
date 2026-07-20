<template>
  <div class="page-shell chunk-strategy">
    <div class="page-header">
      <h2>文档切分策略</h2>
    </div>
    <div class="page-body">
      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <el-form label-width="120px" class="panel">
            <el-form-item label="文本块大小">
              <el-input-number v-model="form.chunk_size" :min="50" :max="4000" :step="50" @change="onFormChange" />
            </el-form-item>
            <el-form-item label="切片重叠">
              <el-input-number v-model="form.chunk_overlap" :min="0" :max="2000" :step="10" @change="onFormChange" />
            </el-form-item>
            <el-form-item label="分割符号">
              <el-input
                v-model="form.separators"
                placeholder="多个符号用 | 分隔，换行写 \\n"
                @change="onFormChange"
              />
            </el-form-item>
            <el-form-item label="文本清洗">
              <el-switch v-model="form.clean_enabled" @change="onFormChange" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="onSave">保存并同步后端</el-button>
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :xs="24" :md="12">
          <div class="panel">
            <div class="panel-title">纯前端模拟预览（非真实分块）</div>
            <el-input
              v-model="sampleText"
              type="textarea"
              :rows="8"
              placeholder="输入测试文本后查看分块效果"
              @input="runPreview"
            />
            <p v-if="previewTip" class="tip">{{ previewTip }}</p>
            <div v-for="item in preview" :key="item.index" class="chunk-card">
              <div class="chunk-card__head">分块 #{{ item.index + 1 }}（{{ item.char_count }} 字）</div>
              <pre>{{ item.content }}</pre>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchChunkStrategy, syncChunkStrategy } from '@/api/chunkStrategy'
import { loadChunkStrategyConfig, saveChunkStrategyConfig } from '@/utils/localCache'
import { previewChunkSplit } from '@/utils/chunkPreview'
import { INPUT_MAX_LENGTH, processUserInput } from '@/utils/inputFilter'
import type { ChunkPreviewItem, ChunkStrategyConfig } from '@/types'

const saving = ref(false)
const sampleText = ref('这是一段用于演示分块的测试文本。\n## 标题\n下一小节内容。')
const preview = ref<ChunkPreviewItem[]>([])
const previewTip = ref('')

const form = reactive<ChunkStrategyConfig>({
  chunk_size: 500,
  chunk_overlap: 50,
  separators: '\\n## |\\n### |\\n|。|.',
  clean_enabled: true
})

function onFormChange() {
  if (form.chunk_overlap >= form.chunk_size) {
    ElMessage.warning('切片重叠必须小于文本块大小')
    return
  }
  saveChunkStrategyConfig({ ...form })
  runPreview()
}

function runPreview() {
  // 预览允许空文本；仅拦截危险脚本。长度超限给出提示但仍用原文做可视化（不截断原始预览源）
  const dual = processUserInput(sampleText.value, INPUT_MAX_LENGTH)
  if (dual.blocked) {
    previewTip.value = dual.tip
    preview.value = []
    return
  }
  previewTip.value = dual.overLimit ? dual.tip : ''
  preview.value = previewChunkSplit(dual.raw, { ...form })
}

async function onSave() {
  if (form.chunk_overlap >= form.chunk_size) {
    ElMessage.warning('切片重叠必须小于文本块大小')
    return
  }
  const sepDual = processUserInput(form.separators, INPUT_MAX_LENGTH)
  if (sepDual.blocked || sepDual.overLimit) {
    ElMessage.warning(sepDual.tip || '分割符号不合法')
    return
  }
  const payload: ChunkStrategyConfig = {
    chunk_size: form.chunk_size,
    chunk_overlap: form.chunk_overlap,
    separators: sepDual.raw,
    clean_enabled: form.clean_enabled
  }
  saving.value = true
  try {
    saveChunkStrategyConfig(payload)
    Object.assign(form, payload)
    await syncChunkStrategy(payload)
    ElMessage.success('切分策略已同步')
  } catch {
    ElMessage.error('同步失败：需后端实现 PUT /api/chunk-strategy')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const cached = loadChunkStrategyConfig()
  if (cached) Object.assign(form, cached)
  try {
    const remote = await fetchChunkStrategy()
    if (remote) Object.assign(form, remote)
  } catch {
    /* 后端未就绪时使用缓存/默认 */
  }
  saveChunkStrategyConfig({ ...form })
  runPreview()
})
</script>

<style scoped>
.panel {
  padding: 16px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
  margin-bottom: 16px;
}
.panel-title {
  margin-bottom: 10px;
  font-weight: 600;
}
.tip {
  color: var(--el-color-warning);
  font-size: 13px;
}
.chunk-card {
  margin-top: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
}
.chunk-card__head {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-bottom: 6px;
}
.chunk-card pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.5;
}
</style>
