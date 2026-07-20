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
        title="模型列表与参数区间必须由后端接口下发；前端不硬编码模型名与上下限。保存时同步至后端配置接口。"
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
        <el-form-item label="向量模型" prop="embedding_model">
          <el-select v-model="form.embedding_model" filterable style="width: 100%" @change="persistLocal">
            <el-option v-for="m in embeddingModels" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="LLM 模型" prop="llm_model">
          <el-select v-model="form.llm_model" filterable style="width: 100%" @change="persistLocal">
            <el-option v-for="m in llmModels" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="温度" prop="temperature">
          <el-input-number
            v-model="form.temperature"
            :min="bounds.temperature_min"
            :max="bounds.temperature_max"
            :step="0.1"
            @change="persistLocal"
          />
          <span class="hint">合法区间：{{ bounds.temperature_min }} ~ {{ bounds.temperature_max }}</span>
        </el-form-item>
        <el-form-item label="最大输出 Token" prop="max_tokens">
          <el-input-number
            v-model="form.max_tokens"
            :min="bounds.max_tokens_min"
            :max="bounds.max_tokens_max"
            :step="64"
            @change="persistLocal"
          />
          <span class="hint">合法区间：{{ bounds.max_tokens_min }} ~ {{ bounds.max_tokens_max }}</span>
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
import { fetchRuntimeModelOptions, syncRuntimeModelConfig } from '@/api/runtimeConfig'
import { loadRuntimeModelConfig, saveRuntimeModelConfig } from '@/utils/localCache'
import { clearAllFrontendCache } from '@/utils/cacheLifecycle'
import type { RuntimeModelBounds, RuntimeModelConfig } from '@/types'

const loading = ref(false)
const saving = ref(false)
const optionsReady = ref(false)
const formRef = ref<FormInstance>()
const embeddingModels = ref<string[]>([])
const llmModels = ref<string[]>([])

/** 区间仅在接口返回后赋值，初始化为占位，禁止作为业务硬编码上下限使用 */
const bounds = reactive<RuntimeModelBounds>({
  temperature_min: Number.NaN,
  temperature_max: Number.NaN,
  max_tokens_min: Number.NaN,
  max_tokens_max: Number.NaN
})

const form = reactive<RuntimeModelConfig>({
  embedding_model: '',
  llm_model: '',
  temperature: Number.NaN,
  max_tokens: Number.NaN
})

const rules: FormRules = {
  embedding_model: [{ required: true, message: '请选择向量模型', trigger: 'change' }],
  llm_model: [{ required: true, message: '请选择 LLM 模型', trigger: 'change' }],
  temperature: [{ required: true, message: '请填写温度', trigger: 'change' }],
  max_tokens: [{ required: true, message: '请填写最大输出 Token', trigger: 'change' }]
}

function persistLocal() {
  if (!optionsReady.value) return
  if (!form.embedding_model || !form.llm_model) return
  if (Number.isNaN(form.temperature) || Number.isNaN(form.max_tokens)) return
  saveRuntimeModelConfig({ ...form })
}

function applyBoundsCheck(): string | null {
  if (!optionsReady.value || Number.isNaN(bounds.temperature_min)) {
    return '请先拉取后端下发的参数区间'
  }
  if (form.temperature < bounds.temperature_min || form.temperature > bounds.temperature_max) {
    return `温度需在 ${bounds.temperature_min} ~ ${bounds.temperature_max} 之间`
  }
  if (form.max_tokens < bounds.max_tokens_min || form.max_tokens > bounds.max_tokens_max) {
    return `最大输出 Token 需在 ${bounds.max_tokens_min} ~ ${bounds.max_tokens_max} 之间`
  }
  if (!embeddingModels.value.includes(form.embedding_model)) {
    return '向量模型不在后端返回的可用列表中'
  }
  if (!llmModels.value.includes(form.llm_model)) {
    return 'LLM 模型不在后端返回的可用列表中'
  }
  return null
}

function pickFromLists(cachedName: string | undefined, list: string[], apiCurrent?: string): string {
  if (cachedName && list.includes(cachedName)) return cachedName
  if (apiCurrent && list.includes(apiCurrent)) return apiCurrent
  return list[0] || ''
}

async function reload() {
  loading.value = true
  optionsReady.value = false
  try {
    const data = await fetchRuntimeModelOptions()
    const emb = data.embedding_models || []
    const llms = data.llm_models || []
    if (!emb.length || !llms.length || !data.bounds) {
      ElMessage.error('后端返回的模型列表或参数区间不完整')
      return
    }
    embeddingModels.value = emb
    llmModels.value = llms
    Object.assign(bounds, data.bounds)

    const cached = loadRuntimeModelConfig()
    const apiCurrent = data.current
    form.embedding_model = pickFromLists(cached?.embedding_model, emb, apiCurrent?.embedding_model)
    form.llm_model = pickFromLists(cached?.llm_model, llms, apiCurrent?.llm_model)

    const tempCandidate = cached?.temperature ?? apiCurrent?.temperature
    const tokenCandidate = cached?.max_tokens ?? apiCurrent?.max_tokens
    if (tempCandidate == null || tokenCandidate == null) {
      ElMessage.error('后端未返回温度或最大 Token 默认值，无法初始化表单')
      return
    }
    form.temperature = Number(tempCandidate)
    form.max_tokens = Number(tokenCandidate)

    // 缓存值若越界，回退到接口 current
    if (applyBoundsCheck()) {
      if (apiCurrent?.temperature != null) form.temperature = Number(apiCurrent.temperature)
      if (apiCurrent?.max_tokens != null) form.max_tokens = Number(apiCurrent.max_tokens)
      form.embedding_model = pickFromLists(undefined, emb, apiCurrent?.embedding_model)
      form.llm_model = pickFromLists(undefined, llms, apiCurrent?.llm_model)
    }

    optionsReady.value = true
    persistLocal()
  } catch {
    ElMessage.error('拉取模型配置失败，请确认后端接口已就绪')
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
    await syncRuntimeModelConfig({ ...form })
    ElMessage.success('配置已保存并同步')
  } catch {
    ElMessage.error('同步失败：需后端实现 PUT /api/runtime-config')
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
