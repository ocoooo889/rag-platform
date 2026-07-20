<template>
  <div class="page-shell model-runtime" v-loading="loading">
    <div class="page-header">
      <h2>大模型运行配置</h2>
      <el-button @click="clearLocal">清理本地缓存</el-button>
    </div>
    <div class="page-body">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="模型列表与参数区间必须由 GET /api/runtime-config/models 下发；保存走 PUT /api/runtime-config/models。前端不硬编码模型名与上下限。"
        class="mb16"
      />
      <el-empty v-if="!optionsReady && !loading" description="尚未拉取到可用模型配置" />
      <el-form
        v-else
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        class="cfg-form"
        :disabled="!optionsReady"
      >
        <el-form-item label="向量模型" prop="embedding_model_id">
          <el-select v-model="embKey" filterable style="width: 100%" @change="onEmbKeyChange">
            <el-option
              v-for="m in embeddingModels"
              :key="modelKey(m)"
              :label="m.id == null ? `${m.model_name} (env)` : m.model_name"
              :value="modelKey(m)"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="LLM 模型" prop="chat_model_id">
          <el-select v-model="chatKey" filterable style="width: 100%" @change="onChatKeyChange">
            <el-option
              v-for="m in chatModels"
              :key="modelKey(m)"
              :label="m.id == null ? `${m.model_name} (env)` : m.model_name"
              :value="modelKey(m)"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="温度" prop="temperature">
          <el-input-number
            v-model="form.temperature"
            :min="limits.temperature.min"
            :max="limits.temperature.max"
            :step="limits.temperature.step || 0.1"
            @change="persistLocal"
          />
          <span class="hint">{{ limits.temperature.min }} ~ {{ limits.temperature.max }}</span>
        </el-form-item>
        <el-form-item label="Top P" prop="top_p">
          <el-input-number
            v-model="form.top_p"
            :min="limits.top_p.min"
            :max="limits.top_p.max"
            :step="limits.top_p.step || 0.05"
            @change="persistLocal"
          />
          <span class="hint">{{ limits.top_p.min }} ~ {{ limits.top_p.max }}</span>
        </el-form-item>
        <el-form-item label="最大输出 Token" prop="max_tokens">
          <el-input-number
            v-model="form.max_tokens"
            :min="limits.max_tokens.min"
            :max="limits.max_tokens.max"
            :step="limits.max_tokens.step || 1"
            @change="persistLocal"
          />
          <span class="hint">{{ limits.max_tokens.min }} ~ {{ limits.max_tokens.max }}</span>
        </el-form-item>
        <el-form-item v-if="dimOptions.length" label="向量维度" prop="embedding_dimension">
          <el-select v-model="form.embedding_dimension" style="width: 100%" @change="persistLocal">
            <el-option v-for="d in dimOptions" :key="d" :label="String(d)" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" :disabled="!optionsReady" @click="onSave">
            保存并同步后端
          </el-button>
          <el-button @click="reload">重新拉取</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  fetchRuntimeModelOptions,
  formToUpdate,
  listModelsByType,
  selectionToForm,
  syncRuntimeModelConfig
} from '@/api/runtimeConfig'
import { loadRuntimeModelConfig, saveRuntimeModelConfig } from '@/utils/localCache'
import { clearAllFrontendCache } from '@/utils/cacheLifecycle'
import type { RuntimeModelConfig, RuntimeModelItem, RuntimeParamLimit } from '@/types'

const loading = ref(false)
const saving = ref(false)
const optionsReady = ref(false)
const formRef = ref<FormInstance>()
const embeddingModels = ref<RuntimeModelItem[]>([])
const chatModels = ref<RuntimeModelItem[]>([])
const embKey = ref<string | number>('')
const chatKey = ref<string | number>('')

const limits = reactive({
  temperature: { min: Number.NaN, max: Number.NaN, step: 0.1 } as RuntimeParamLimit,
  top_p: { min: Number.NaN, max: Number.NaN, step: 0.05 } as RuntimeParamLimit,
  max_tokens: { min: Number.NaN, max: Number.NaN, step: 1 } as RuntimeParamLimit
})

const dimOptions = ref<number[]>([])

const form = reactive<RuntimeModelConfig>({
  chat_model_id: null,
  embedding_model_id: null,
  temperature: Number.NaN,
  top_p: Number.NaN,
  max_tokens: Number.NaN
})

const rules: FormRules = {
  temperature: [{ required: true, message: '请填写温度', trigger: 'change' }],
  top_p: [{ required: true, message: '请填写 Top P', trigger: 'change' }],
  max_tokens: [{ required: true, message: '请填写最大输出 Token', trigger: 'change' }]
}

function modelKey(m: RuntimeModelItem): string | number {
  return m.id != null ? m.id : `env:${m.model_type}:${m.model_name}`
}

function findByKey(list: RuntimeModelItem[], key: string | number): RuntimeModelItem | undefined {
  return list.find((m) => modelKey(m) === key)
}

function persistLocal() {
  if (!optionsReady.value) return
  if (
    Number.isNaN(form.temperature) ||
    Number.isNaN(form.top_p) ||
    Number.isNaN(form.max_tokens)
  ) {
    return
  }
  saveRuntimeModelConfig({ ...form })
}

function onEmbKeyChange(key: string | number) {
  const m = findByKey(embeddingModels.value, key)
  form.embedding_model_id = m?.id ?? null
  form.embedding_model_name = m?.model_name
  persistLocal()
}

function onChatKeyChange(key: string | number) {
  const m = findByKey(chatModels.value, key)
  form.chat_model_id = m?.id ?? null
  form.chat_model_name = m?.model_name
  persistLocal()
}

function applyBoundsCheck(): string | null {
  if (!optionsReady.value || Number.isNaN(Number(limits.temperature.min))) {
    return '请先拉取后端下发的参数区间'
  }
  if (
    form.temperature < Number(limits.temperature.min) ||
    form.temperature > Number(limits.temperature.max)
  ) {
    return `温度需在 ${limits.temperature.min} ~ ${limits.temperature.max} 之间`
  }
  if (form.top_p < Number(limits.top_p.min) || form.top_p > Number(limits.top_p.max)) {
    return `Top P 需在 ${limits.top_p.min} ~ ${limits.top_p.max} 之间`
  }
  if (
    form.max_tokens < Number(limits.max_tokens.min) ||
    form.max_tokens > Number(limits.max_tokens.max)
  ) {
    return `最大输出 Token 需在 ${limits.max_tokens.min} ~ ${limits.max_tokens.max} 之间`
  }
  if (!embKey.value || !findByKey(embeddingModels.value, embKey.value)) {
    return '向量模型不在后端返回的可用列表中'
  }
  if (!chatKey.value || !findByKey(chatModels.value, chatKey.value)) {
    return 'LLM 模型不在后端返回的可用列表中'
  }
  return null
}

async function reload() {
  loading.value = true
  optionsReady.value = false
  try {
    const data = await fetchRuntimeModelOptions()
    const emb = listModelsByType(data, 'embedding')
    const chats = listModelsByType(data, 'chat')
    if (!emb.length || !chats.length || !data.parameter_limits?.chat) {
      ElMessage.error('后端返回的模型列表或参数区间不完整')
      return
    }
    embeddingModels.value = emb
    chatModels.value = chats
    Object.assign(limits.temperature, data.parameter_limits.chat.temperature || {})
    Object.assign(limits.top_p, data.parameter_limits.chat.top_p || {})
    Object.assign(limits.max_tokens, data.parameter_limits.chat.max_tokens || {})
    dimOptions.value = data.parameter_limits.embedding?.dimension?.options || []

    const fromApi = selectionToForm(data)
    Object.assign(form, fromApi)
    const embPick =
      emb.find((m) => m.id === fromApi.embedding_model_id) ||
      emb.find((m) => m.model_name === fromApi.embedding_model_name) ||
      emb[0]
    const chatPick =
      chats.find((m) => m.id === fromApi.chat_model_id) ||
      chats.find((m) => m.model_name === fromApi.chat_model_name) ||
      chats[0]
    embKey.value = embPick ? modelKey(embPick) : ''
    chatKey.value = chatPick ? modelKey(chatPick) : ''
    onEmbKeyChange(embKey.value)
    onChatKeyChange(chatKey.value)

    const cached = loadRuntimeModelConfig()
    if (
      cached &&
      !Number.isNaN(cached.temperature) &&
      cached.temperature >= Number(limits.temperature.min) &&
      cached.temperature <= Number(limits.temperature.max) &&
      (cached.top_p == null ||
        (Number(cached.top_p) >= Number(limits.top_p.min) &&
          Number(cached.top_p) <= Number(limits.top_p.max))) &&
      (cached.max_tokens == null ||
        (Number(cached.max_tokens) >= Number(limits.max_tokens.min) &&
          Number(cached.max_tokens) <= Number(limits.max_tokens.max)))
    ) {
      form.temperature = cached.temperature
      if (cached.top_p != null) form.top_p = cached.top_p
      if (cached.max_tokens != null) form.max_tokens = cached.max_tokens
    }

    if (applyBoundsCheck()) {
      Object.assign(form, fromApi)
      onEmbKeyChange(embKey.value)
      onChatKeyChange(chatKey.value)
    }

    optionsReady.value = true
    persistLocal()
  } catch {
    ElMessage.error('拉取模型配置失败，请确认 GET /api/runtime-config/models 已就绪')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!optionsReady.value) {
    ElMessage.warning('请先拉取后端配置')
    return
  }
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  const tip = applyBoundsCheck()
  if (tip) {
    ElMessage.warning(tip)
    return
  }
  saving.value = true
  try {
    persistLocal()
    await syncRuntimeModelConfig(formToUpdate({ ...form }))
    ElMessage.success('配置已保存并同步')
  } catch {
    ElMessage.error('同步失败：PUT /api/runtime-config/models')
  } finally {
    saving.value = false
  }
}

async function clearLocal() {
  await clearAllFrontendCache()
  ElMessage.success('本地缓存已清理')
  await reload()
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}
.cfg-form {
  max-width: 640px;
  padding: 16px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-card);
}
.hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
}
</style>
