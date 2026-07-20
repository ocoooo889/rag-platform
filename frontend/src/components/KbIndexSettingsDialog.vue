<template>
  <el-dialog
    :model-value="modelValue"
    title="知识库索引配置"
    width="640px"
    top="8vh"
    destroy-on-close
    class="kb-index-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb12"
      title="字段与后端 index-config 对齐：块大小/重叠、混合权重、默认检索、Rerank、TopN。向量模型请到「大模型运行配置」修改。"
    />

    <el-form label-width="120px" :disabled="saving || configLoading" v-loading="configLoading">
      <el-form-item label="文本块大小">
        <el-input-number
          v-model="form.chunk_size"
          :min="KB_CHUNK_SIZE_MIN"
          :max="KB_CHUNK_SIZE_MAX"
          :step="50"
        />
        <span class="hint">{{ KB_CHUNK_SIZE_MIN }}~{{ KB_CHUNK_SIZE_MAX }}</span>
      </el-form-item>
      <el-form-item label="切片重叠">
        <el-input-number
          v-model="form.chunk_overlap"
          :min="0"
          :max="Math.max(0, form.chunk_size - 1)"
          :step="10"
        />
      </el-form-item>
      <el-form-item label="混合权重 α">
        <el-slider v-model="form.hybrid_alpha" :min="0" :max="1" :step="0.05" show-input />
      </el-form-item>
      <el-form-item label="默认检索">
        <el-select v-model="form.default_search_type" style="width: 100%">
          <el-option
            v-for="opt in SEARCH_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="默认 TopN">
        <el-input-number v-model="form.default_top_n" :min="1" :max="10" :step="1" />
      </el-form-item>
      <el-form-item label="启用 Rerank">
        <el-switch v-model="form.enable_rerank" />
      </el-form-item>
      <el-form-item label="变更快照">
        <el-switch v-model="form.create_snapshot" />
        <p class="hint">前端重建意图标记（不写入 index-config）</p>
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
  SEARCH_TYPE_OPTIONS,
  SYNC_MODE_OPTIONS,
  KB_CHUNK_SIZE_MIN,
  KB_CHUNK_SIZE_MAX,
  normalizeKbIndexConfig,
  validateKbIndexConfig,
  resolveKbIndexConfig,
  getKbIndexDefaults
} from '@/utils/kbIndex'
import { updateKbIndexConfig, fetchKbIndexConfig } from '@/api/kbIndex'
import { fetchSplitStrategies } from '@/api/splitStrategies'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  kbId: { type: [String, Number], default: '' },
  kbName: { type: String, default: '' },
  apiIndex: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'saved', 'rebuild', 'synced'])

const saving = ref(false)
const configLoading = ref(false)
const form = reactive(normalizeKbIndexConfig(getKbIndexDefaults()))

const syncTip = computed(() => {
  const opt = SYNC_MODE_OPTIONS.find((o) => o.value === form.sync_mode)
  return opt?.tip || ''
})

async function hydrate() {
  if (!props.kbId) return
  // 先拉 split-strategies，使默认块参数来自后端
  try {
    await fetchSplitStrategies()
  } catch {
    /* 索引配置仍可从 index-config 拉取 */
  }
  const { config } = resolveKbIndexConfig(props.kbId, props.apiIndex)
  Object.assign(form, normalizeKbIndexConfig(config))

  configLoading.value = true
  try {
    const remote = await fetchKbIndexConfig(props.kbId)
    Object.assign(
      form,
      normalizeKbIndexConfig({
        ...remote,
        create_snapshot: form.create_snapshot,
        sync_mode: form.sync_mode
      })
    )
    emit('synced', remote)
  } catch {
    /* fetch 内部已回退 */
  } finally {
    configLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) hydrate()
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

async function onSave(andRebuild) {
  const cfg = normalizeKbIndexConfig(form)
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
      try {
        await ElMessageBox.confirm(
          '将提交库级重建（对可处理文档重新切片向量化）。是否继续？',
          '保存并重建',
          { type: 'warning' }
        )
      } catch {
        emit('update:modelValue', false)
        return
      }
      emit('rebuild', saved)
      emit('update:modelValue', false)
    } else {
      emit('update:modelValue', false)
    }
  } catch (e) {
    const detail = e?.msg || e?.message || e?.response?.data?.msg || '保存失败'
    ElMessageBox.alert(String(detail), '索引配置保存失败', { type: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mb12 {
  margin-bottom: 12px;
}
.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
}
</style>
