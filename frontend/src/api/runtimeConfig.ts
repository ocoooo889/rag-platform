/**
 * 运行时大模型配置 API
 *
 * 【后端待实现】建议：
 *   GET  /api/runtime-config/models   -> embedding/llm 列表 + bounds
 *   PUT  /api/runtime-config          -> 同步 RuntimeModelConfig
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import type { ApiResponse, RuntimeModelConfig, RuntimeModelOptionsPayload } from '@/types'
import { withRequestDebounceCache } from '@/utils/cacheLifecycle'

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

/** 拉取可用模型与参数区间（禁止前端硬编码模型名） */
export async function fetchRuntimeModelOptions(): Promise<RuntimeModelOptionsPayload> {
  return withRequestDebounceCache('runtime-model-options', async () => {
    if (MOCK_OPEN()) {
      return unwrap(
        await mockResolve({
          embedding_models: ['text-embedding-v4', 'text-embedding-3-small'],
          llm_models: ['gpt-4o-mini', 'qwen-plus'],
          bounds: {
            temperature_min: 0,
            temperature_max: 2,
            max_tokens_min: 64,
            max_tokens_max: 8192
          },
          current: {
            embedding_model: 'text-embedding-v4',
            llm_model: 'qwen-plus',
            temperature: 0.7,
            max_tokens: 1024
          }
        } satisfies RuntimeModelOptionsPayload)
      )
    }
    const res = (await request.get('/api/runtime-config/models')) as ApiResponse<RuntimeModelOptionsPayload>
    return unwrap(res)
  })
}

/** 同步配置到后端 */
export async function syncRuntimeModelConfig(
  config: RuntimeModelConfig
): Promise<RuntimeModelConfig> {
  if (MOCK_OPEN()) {
    return unwrap(await mockResolve({ ...config }))
  }
  const res = (await request.put('/api/runtime-config', config)) as ApiResponse<RuntimeModelConfig>
  return unwrap(res)
}
