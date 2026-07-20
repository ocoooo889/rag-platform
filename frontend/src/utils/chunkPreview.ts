/**
 * 文档切分「纯前端模拟预览」
 * 仅用于可视化，不替代后端真实分块 / 向量化
 */
import type { ChunkPreviewItem, ChunkStrategyConfig } from '@/types'

function applyClean(text: string, enabled: boolean): string {
  if (!enabled) return text
  return text
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

/**
 * 按 separators 粗切后再按 size/overlap 滑窗（演示用，非 langchain 等价实现）
 */
export function previewChunkSplit(
  sourceText: string,
  config: ChunkStrategyConfig
): ChunkPreviewItem[] {
  const size = Math.max(20, Number(config.chunk_size))
  if (!Number.isFinite(size)) return []
  const overlap = Math.min(Math.max(0, Number(config.chunk_overlap) || 0), Math.max(size - 1, 0))
  const cleaned = applyClean(String(sourceText || ''), !!config.clean_enabled)
  if (!cleaned) return []

  const seps = String(config.separators || '\n')
    .split('|')
    .map((s) => s.replace(/\\n/g, '\n'))
    .filter(Boolean)

  let pieces: string[] = [cleaned]
  for (const sep of seps) {
    const next: string[] = []
    for (const p of pieces) {
      if (!sep || !p.includes(sep)) {
        next.push(p)
        continue
      }
      const parts = p.split(sep)
      parts.forEach((part, idx) => {
        const chunk = idx === 0 ? part : `${sep}${part}`
        if (chunk) next.push(chunk)
      })
    }
    pieces = next
  }

  const merged = pieces.join('')
  const result: ChunkPreviewItem[] = []
  let start = 0
  let index = 0
  while (start < merged.length) {
    const end = Math.min(merged.length, start + size)
    const content = merged.slice(start, end)
    result.push({ index, content, char_count: content.length })
    index += 1
    if (end >= merged.length) break
    start = end - overlap
    if (start < 0) start = 0
    if (start >= end) start = end
  }
  return result
}
