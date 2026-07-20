/**
 * 文档切分策略同步 API
 *
 * 【后端待实现】建议：
 *   PUT /api/chunk-strategy  body: ChunkStrategyConfig
 *   GET /api/chunk-strategy
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import type { ApiResponse, ChunkStrategyConfig } from '@/types'

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

export async function fetchChunkStrategy(): Promise<ChunkStrategyConfig | null> {
  if (MOCK_OPEN()) {
    return unwrap(
      await mockResolve({
        chunk_size: 500,
        chunk_overlap: 50,
        separators: '\\n## |\\n### |\\n|。|.',
        clean_enabled: true
      } satisfies ChunkStrategyConfig)
    )
  }
  try {
    const res = (await request.get('/api/chunk-strategy', { silent: true })) as ApiResponse<ChunkStrategyConfig>
    return unwrap(res)
  } catch {
    return null
  }
}

export async function syncChunkStrategy(config: ChunkStrategyConfig): Promise<ChunkStrategyConfig> {
  if (MOCK_OPEN()) {
    return unwrap(await mockResolve({ ...config }))
  }
  const res = (await request.put('/api/chunk-strategy', config)) as ApiResponse<ChunkStrategyConfig>
  return unwrap(res)
}
