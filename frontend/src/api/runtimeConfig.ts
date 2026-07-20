/**
 * 运行时大模型配置 API
 * 契约：GET/PUT /api/runtime-config/models
 * 载荷：models + parameter_limits + selection（禁止前端硬编码模型名）
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import type {
  ApiResponse,
  RuntimeModelConfig,
  RuntimeModelConfigUpdate,
  RuntimeModelOptionsPayload,
  RuntimeModelItem,
  RuntimeModelSelection
} from '@/types'
import { withRequestDebounceCache } from '@/utils/cacheLifecycle'

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

function mockPayload(): RuntimeModelOptionsPayload {
  const models: RuntimeModelItem[] = [
    {
      id: 1,
      model_type: 'embedding',
      model_name: 'mock-embedding',
      is_active: true,
      source: 'mock'
    },
    {
      id: 2,
      model_type: 'chat',
      model_name: 'mock-chat',
      is_active: true,
      source: 'mock'
    }
  ]
  return {
    models,
    parameter_limits: {
      chat: {
        temperature: { label: '温度', type: 'float', min: 0, max: 2, default: 0.7, step: 0.1 },
        top_p: { label: 'Top P', type: 'float', min: 0, max: 1, default: 1, step: 0.05 },
        max_tokens: { label: '最大输出 Token', type: 'int', min: 1, max: 8192, default: 2048, step: 1 },
        presence_penalty: {
          label: '存在惩罚',
          type: 'float',
          min: -2,
          max: 2,
          default: 0,
          step: 0.1
        },
        frequency_penalty: {
          label: '频率惩罚',
          type: 'float',
          min: -2,
          max: 2,
          default: 0,
          step: 0.1
        }
      },
      embedding: {
        dimension: { label: '向量维度', type: 'enum', options: [384, 768, 1024, 1536], default: 1024 }
      }
    },
    selection: {
      chat_model_id: 2,
      embedding_model_id: 1,
      chat_params: {
        temperature: 0.7,
        top_p: 1,
        max_tokens: 2048,
        presence_penalty: 0,
        frequency_penalty: 0
      },
      embedding_params: { dimension: 1024 },
      updated_at: null
    }
  }
}

/** 拉取可用模型与参数区间 */
export async function fetchRuntimeModelOptions(): Promise<RuntimeModelOptionsPayload> {
  return withRequestDebounceCache('runtime-model-options', async () => {
    if (MOCK_OPEN()) {
      return unwrap(await mockResolve(mockPayload()))
    }
    const res = (await request.get(
      '/api/runtime-config/models'
    )) as ApiResponse<RuntimeModelOptionsPayload>
    return unwrap(res)
  })
}

/** 同步配置到后端 PUT /api/runtime-config/models */
export async function syncRuntimeModelConfig(
  update: RuntimeModelConfigUpdate
): Promise<RuntimeModelOptionsPayload> {
  if (MOCK_OPEN()) {
    const base = mockPayload()
    return unwrap(
      await mockResolve({
        ...base,
        selection: {
          ...base.selection,
          chat_model_id:
            update.chat_model_id !== undefined
              ? update.chat_model_id
              : base.selection.chat_model_id,
          embedding_model_id:
            update.embedding_model_id !== undefined
              ? update.embedding_model_id
              : base.selection.embedding_model_id,
          chat_params: { ...base.selection.chat_params, ...(update.chat_params || {}) },
          embedding_params: {
            ...base.selection.embedding_params,
            ...(update.embedding_params || {})
          }
        }
      } satisfies RuntimeModelOptionsPayload)
    )
  }
  const res = (await request.put(
    '/api/runtime-config/models',
    update
  )) as ApiResponse<RuntimeModelOptionsPayload>
  return unwrap(res)
}

export function listModelsByType(
  payload: RuntimeModelOptionsPayload | null | undefined,
  type: 'chat' | 'embedding'
): RuntimeModelItem[] {
  const list = payload?.models || []
  return list.filter((m) => {
    const t = String(m.model_type || '').toLowerCase()
    if (type === 'chat') return t === 'chat' || t === 'llm'
    return t === 'embedding'
  })
}

export function selectionToForm(
  payload: RuntimeModelOptionsPayload
): RuntimeModelConfig {
  const sel: RuntimeModelSelection = payload.selection || {
    chat_model_id: null,
    embedding_model_id: null,
    chat_params: {
      temperature: Number(payload.parameter_limits?.chat?.temperature?.default ?? 0.7),
      top_p: Number(payload.parameter_limits?.chat?.top_p?.default ?? 1),
      max_tokens: Number(payload.parameter_limits?.chat?.max_tokens?.default ?? 2048)
    },
    embedding_params: {}
  }
  const chats = listModelsByType(payload, 'chat')
  const embs = listModelsByType(payload, 'embedding')
  const chat = chats.find((m) => m.id === sel.chat_model_id) || chats[0]
  const emb = embs.find((m) => m.id === sel.embedding_model_id) || embs[0]
  const cp = sel.chat_params || {}
  return {
    chat_model_id: chat?.id ?? sel.chat_model_id ?? null,
    embedding_model_id: emb?.id ?? sel.embedding_model_id ?? null,
    chat_model_name: chat?.model_name,
    embedding_model_name: emb?.model_name,
    temperature: Number(cp.temperature ?? payload.parameter_limits.chat.temperature.default ?? 0.7),
    top_p: Number(cp.top_p ?? payload.parameter_limits.chat.top_p.default ?? 1),
    max_tokens: Number(cp.max_tokens ?? payload.parameter_limits.chat.max_tokens.default ?? 2048),
    presence_penalty: Number(
      cp.presence_penalty ?? payload.parameter_limits.chat.presence_penalty?.default ?? 0
    ),
    frequency_penalty: Number(
      cp.frequency_penalty ?? payload.parameter_limits.chat.frequency_penalty?.default ?? 0
    ),
    embedding_dimension: Number(
      sel.embedding_params?.dimension ??
        payload.parameter_limits.embedding.dimension.default ??
        NaN
    )
  }
}

export function formToUpdate(form: RuntimeModelConfig): RuntimeModelConfigUpdate {
  return {
    chat_model_id: form.chat_model_id,
    embedding_model_id: form.embedding_model_id,
    chat_params: {
      temperature: form.temperature,
      top_p: form.top_p,
      max_tokens: form.max_tokens,
      presence_penalty: form.presence_penalty,
      frequency_penalty: form.frequency_penalty
    },
    embedding_params:
      form.embedding_dimension != null && !Number.isNaN(form.embedding_dimension)
        ? { dimension: form.embedding_dimension }
        : undefined
  }
}

/** 仅返回向量模型名称列表（评测/索引下拉用，来自接口而非硬编码） */
export function embeddingModelNames(payload: RuntimeModelOptionsPayload | null): string[] {
  return listModelsByType(payload, 'embedding')
    .map((m) => m.model_name)
    .filter(Boolean)
}
