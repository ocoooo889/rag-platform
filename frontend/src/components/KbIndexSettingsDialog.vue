<template>
  <el-dialog
    :model-value="modelValue"
    title="知识库索引配置"
    width="820px"
    top="6vh"
    destroy-on-close
    class="kb-index-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb12"
      title="打开本页会从后端拉取索引配置并覆盖本地缓存；本地仅作加速。保存仍需 PUT 成功后才会写回缓存。"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :md="13">
        <el-form label-width="110px" :disabled="saving || configLoading">
          <div class="section-title">切分策略</div>
          <el-form-item label="文本块大小">
            <el-input-number
              v-model="form.chunk_size"
              :min="50"
              :max="4000"
              :step="50"
              @change="runPreview"
            />
          </el-form-item>
          <el-form-item label="切片重叠">
            <el-input-number
              v-model="form.chunk_overlap"
              :min="0"
              :max="2000"
              :step="10"
              @change="runPreview"
            />
          </el-form-item>
          <el-form-item label="分块方式">
            <el-select v-model="form.chunk_mode" style="width: 100%">
              <el-option
                v-for="opt in CHUNK_MODE_OPTIONS"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
                :disabled="opt.disabled"
              />
            </el-select>
            <p class="hint">{{ modeTip }}</p>
          </el-form-item>
          <el-form-item label="分割符号">
            <el-input
              v-model="form.separators"
              placeholder="多个符号用 | 分隔，换行写 \\n"
              @change="runPreview"
            />
          </el-form-item>
          <el-form-item label="文本清洗">
            <el-switch v-model="form.clean_enabled" @change="runPreview" />
          </el-form-item>

          <div class="section-title">向量与同步</div>
          <el-form-item label="向量模型">
            <el-select
              v-model="form.embedding_model"
              filterable
              allow-create
              default-first-option
              style="width: 100%"
              :loading="modelsLoading"
            >
              <el-option v-for="m in embeddingModels" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="变更快照">
            <el-switch v-model="form.create_snapshot" />
            <p class="hint">开启后先建快照，问答可继续使用旧索引，直至重建完成（需后端支持）</p>
          </el-form-item>
          <el-form-item label="同步规则">
            <el-radio-group v-model="form.sync_mode">
              <el-radio
                v-for="opt in SYNC_MODE_OPTIONS"
                :key="opt.value"
                :label="opt.value"
                style="display: block; margin-bottom: 6px"
              >
                {{ opt.label }}
              </el-radio>
            </el-radio-group>
            <p class="hint">{{ syncTip }}</p>
          </el-form-item>
        </el-form>
      </el-col>

      <el-col :xs="24" :md="11">
        <div class="preview-panel">
          <div class="section-title">切分预览（纯前端模拟）</div>
          <el-input
            v-model="sampleText"
            type="textarea"
            :rows="7"
            placeholder="输入测试文本后查看分块效果"
            @input="runPreview"
          />
          <p v-if="previewTip" class="preview-tip">{{ previewTip }}</p>
          <div class="preview-list">
            <div v-for="item in preview" :key="item.index" class="chunk-card">
              <div class="chunk-card__head">分块 #{{ item.index + 1 }}（{{ item.char_count }} 字）</div>
              <pre>{{ item.content }}</pre>
            </div>
            <p v-if="!preview.length && !previewTip" class="hint">暂无预览，请输入文本</p>
          </div>
        </div>
      </el-col>
    </el-row>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button :loading="saving" @click="onSave(false)">仅保存</el-button>
      <el-button type="primary" :loading="saving" @click="onSave(true)">保存并重建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CHUNK_MODE_OPTIONS,
  SYNC_MODE_OPTIONS,
  normalizeKbIndexConfig,
  validateKbIndexConfig,
  resolveKbIndexConfig,
  KB_INDEX_DEFAULTS
} from '@/utils/kbIndex'
import { updateKbIndexConfig, fetchKbIndexConfig } from '@/api/kbIndex'
import { fetchRuntimeModelOptions } from '@/api/runtimeConfig'
import { loadChunkStrategyConfig, loadKbIndexConfig } from '@/utils/localCache'
import { previewChunkSplit } from '@/utils/chunkPreview'
import { INPUT_MAX_LENGTH, processUserInput } from '@/utils/inputFilter'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  kbId: { type: [String, Number], default: '' },
  kbName: { type: String, default: '' },
  /** 后端若已回传索引字段可传入 */
  apiIndex: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'saved', 'rebuild', 'synced'])

const saving = ref(false)
const configLoading = ref(false)
const modelsLoading = ref(false)
const embeddingModels = ref([KB_INDEX_DEFAULTS.embedding_model])
const sampleText = ref('这是一段用于演示分块的测试文本。\n## 标题\n下一小节内容。')
const preview = ref([])
const previewTip = ref('')

const form = reactive(normalizeKbIndexConfig(KB_INDEX_DEFAULTS))

const modeTip = computed(() => {
  const opt = CHUNK_MODE_OPTIONS.find((o) => o.value === form.chunk_mode)
  return opt?.tip || ''
})

const syncTip = computed(() => {
  const opt = SYNC_MODE_OPTIONS.find((o) => o.value === form.sync_mode)
  return opt?.tip || ''
})

function runPreview() {
  const dual = processUserInput(sampleText.value, INPUT_MAX_LENGTH)
  if (dual.blocked) {
    previewTip.value = dual.tip
    preview.value = []
    return
  }
  previewTip.value = dual.overLimit ? dual.tip : ''
  preview.value = previewChunkSplit(dual.raw, {
    chunk_size: form.chunk_size,
    chunk_overlap: form.chunk_overlap,
    separators: form.separators,
    clean_enabled: form.clean_enabled
  })
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const data = await fetchRuntimeModelOptions()
    const list = data?.embedding_models || []
    if (list.length) {
      embeddingModels.value = [...new Set([form.embedding_model, ...list].filter(Boolean))]
      if (!form.embedding_model) {
        form.embedding_model = list[0]
      }
    }
  } catch {
    /* 用默认列表 */
  } finally {
    modelsLoading.value = false
  }
}

/**
 * 先用本地/传入 apiIndex 秒开，再强制 GET 后端覆盖本地与表单
 */
async function hydrate() {
  if (!props.kbId) return

  // 1) 本地秒开（二次加速）
  const { config } = resolveKbIndexConfig(props.kbId, props.apiIndex)
  const next = normalizeKbIndexConfig(config)
  const rawLocal = loadKbIndexConfig(props.kbId)
  if (!rawLocal || rawLocal.separators == null) {
    const legacy = loadChunkStrategyConfig()
    if (legacy) {
      if (legacy.separators != null) next.separators = String(legacy.separators)
      if (legacy.clean_enabled != null) next.clean_enabled = !!legacy.clean_enabled
    }
  }
  Object.assign(form, normalizeKbIndexConfig(next))
  runPreview()

  // 2) 强制拉后端，覆盖 LocalStorage + 表单
  configLoading.value = true
  try {
    const remote = await fetchKbIndexConfig(props.kbId)
    Object.assign(form, normalizeKbIndexConfig(remote))
    runPreview()
    emit('synced', remote)
  } catch {
    /* fetch 内部已回退缓存 */
  } finally {
    configLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      hydrate()
      loadModels()
    }
  }
)

watch(
  () => props.kbId,
  (id, prev) => {
    if (props.modelValue && id && String(id) !== String(prev || '')) {
      hydrate()
    }
  }
)

watch(
  () => props.apiIndex,
  () => {
    if (!props.modelValue || !props.kbId || configLoading.value) return
    if (!props.apiIndex) return
    Object.assign(form, normalizeKbIndexConfig(props.apiIndex))
    runPreview()
  }
)

async function onSave(andRebuild) {
  const sepDual = processUserInput(form.separators, INPUT_MAX_LENGTH)
  if (sepDual.blocked || sepDual.overLimit) {
    ElMessage.warning(sepDual.tip || '分割符号不合法')
    return
  }
  const cfg = normalizeKbIndexConfig({
    ...form,
    separators: sepDual.raw
  })
  const tip = validateKbIndexConfig(cfg)
  if (tip) {
    ElMessage.warning(tip)
    return
  }
  saving.value = true
  try {
    const saved = await updateKbIndexConfig(props.kbId, cfg)
    ElMessage.success('索引配置已保存')
    emit('saved', saved)
    if (andRebuild) {
      emit('rebuild', saved)
      emit('update:modelValue', false)
    } else {
      emit('update:modelValue', false)
    }
  } catch (e) {
    const detail =
      e?.msg ||
      e?.message ||
      e?.response?.data?.msg ||
      e?.response?.data?.message ||
      ''
    const status = e?.response?.status
    const tip =
      status === 422
        ? '保存失败：参数校验未通过（422），本地缓存已清除，请检查后重试。'
        : detail
          ? `保存失败：${detail}（本地缓存已清除）`
          : '保存失败：网络或服务异常，本地缓存已清除，请稍后重试。'
    await ElMessageBox.alert(tip, '索引配置未保存', {
      type: 'error',
      confirmButtonText: '知道了'
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mb12 {
  margin-bottom: 12px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--admin-text, var(--el-text-color-primary));
}
.hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-color-secondary, #909399);
  line-height: 1.4;
}
.preview-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 100%;
}
.preview-tip {
  margin: 0;
  font-size: 12px;
  color: var(--el-color-warning);
}
.preview-list {
  max-height: 320px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chunk-card {
  padding: 8px 10px;
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.12));
  border-radius: 8px;
  background: rgba(10, 18, 36, 0.2);
}
.chunk-card__head {
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--text-color-secondary, #909399);
}
.chunk-card pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.45;
  font-family: inherit;
}
</style>
