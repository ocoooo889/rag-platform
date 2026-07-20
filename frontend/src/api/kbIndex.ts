/**
 * 知识库索引配置 / 重建 API（前端契约）
 *
 * 【后端待实现】建议：
 *   GET  /api/knowledge-bases/{id}/index-config
 *   PUT  /api/knowledge-bases/{id}/index-config
 *   POST /api/knowledge-bases/{id}/rebuild
 *   GET  /api/knowledge-bases/{id}/rebuild/{job_id}
 *
 * 当前：配置落 LocalStorage；重建在 Mock 下模拟进度；
 * 真实环境 force_all 可临时逐文档调用已有 reprocess（见 rebuildKnowledgeBase）。
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import { saveKbIndexConfig, loadKbIndexConfig, removeKbIndexConfig } from '@/utils/localCache'
import { normalizeKbIndexConfig, KB_INDEX_DEFAULTS, resolveKbIndexConfig } from '@/utils/kbIndex'
import { reprocessDocument, fetchDocuments } from '@/api/doc'
import { DOC_STATUS } from '@/utils/docStatus'
import type { ApiResponse, KbIndexConfig, KbRebuildJob } from '@/types'

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

const mockJobs = new Map<string, KbRebuildJob>()

export { resolveKbIndexConfig }

/**
 * 保存索引配置
 * 时序：PUT 成功后再写 LocalStorage；422/网络错误清除本地脏缓存并抛错
 */
export async function updateKbIndexConfig(
  kbId: string | number,
  config: KbIndexConfig
): Promise<KbIndexConfig> {
  const normalized = normalizeKbIndexConfig(config)

  if (MOCK_OPEN()) {
    const saved = unwrap(await mockResolve(normalized))
    const next = normalizeKbIndexConfig(saved || normalized)
    saveKbIndexConfig(kbId, next)
    return next
  }

  try {
    // 【后端待实现】
    const res = (await request.put(`/api/knowledge-bases/${kbId}/index-config`, normalized, {
      silent: true
    })) as ApiResponse<KbIndexConfig>
    const remote = unwrap(res)
    const next = normalizeKbIndexConfig(remote || normalized)
    // PUT 成功后再同步本地
    saveKbIndexConfig(kbId, next)
    return next
  } catch (e) {
    // 422 / 网络错误：清掉本地脏数据，交给页面弹失败提示
    removeKbIndexConfig(kbId)
    throw e
  }
}

/**
 * 触发知识库重建
 * Mock：返回 job 并在内存推进进度
 * Real：先尝试 POST rebuild；失败则按 sync_mode 降级为逐文档 reprocess
 */
export async function rebuildKnowledgeBase(
  kbId: string | number,
  config: KbIndexConfig
): Promise<KbRebuildJob> {
  const normalized = normalizeKbIndexConfig(config)
  saveKbIndexConfig(kbId, normalized)

  if (MOCK_OPEN()) {
    const job: KbRebuildJob = {
      job_id: `job-${Date.now()}`,
      kb_id: String(kbId),
      status: 'running',
      progress: 5,
      message: normalized.create_snapshot ? '已创建变更快照，开始重建…' : '开始重建…'
    }
    mockJobs.set(job.job_id, job)
    let p = 5
    const timer = setInterval(() => {
      p += 18
      const cur = mockJobs.get(job.job_id)
      if (!cur) {
        clearInterval(timer)
        return
      }
      if (p >= 100) {
        cur.progress = 100
        cur.status = 'completed'
        cur.message = '重建完成'
        clearInterval(timer)
      } else {
        cur.progress = p
        cur.message = `重建中 ${p}%`
      }
    }, 600)
    return unwrap(await mockResolve(job))
  }

  try {
    // 【后端待实现】优先走库级重建
    const res = (await request.post(`/api/knowledge-bases/${kbId}/rebuild`, {
      ...normalized,
      create_snapshot: normalized.create_snapshot,
      sync_mode: normalized.sync_mode
    })) as ApiResponse<KbRebuildJob>
    return unwrap(res)
  } catch {
    // 降级：仅 force_all 时用已有文档 reprocess 模拟「强制全部」
    if (normalized.sync_mode !== 'force_all') {
      return {
        job_id: `local-pending-${kbId}`,
        kb_id: String(kbId),
        status: 'failed',
        progress: 0,
        message:
          '索引配置已保存到本地，但后端按库重建接口未就绪。「仅待处理」无法在前端完成同步。'
      }
    }

    const targets: Array<{ id: string | number; status?: string }> = []
    let page = 1
    const pageSize = 100
    for (;;) {
      const listRes = await fetchDocuments({ kb_id: kbId, page, page_size: pageSize })
      const raw = listRes?.data ?? listRes
      const list = Array.isArray(raw) ? raw : raw?.items || raw?.list || []
      const total = Array.isArray(raw) ? list.length : Number(raw?.total || list.length)
      targets.push(...list)
      if (list.length < pageSize || page * pageSize >= total) break
      page += 1
      if (page > 50) break
    }

    const reprocessTargets = targets.filter((d) => {
      const s = String(d.status || '')
      return (
        s === DOC_STATUS.COMPLETED ||
        s === DOC_STATUS.DEGRADED ||
        s === DOC_STATUS.FAILED
      )
    })

    const jobId = `local-reprocess-${Date.now()}`
    let done = 0
    for (const doc of reprocessTargets) {
      try {
        await reprocessDocument(doc.id)
        done += 1
      } catch {
        /* 单个失败继续 */
      }
    }

    return {
      job_id: jobId,
      kb_id: String(kbId),
      status: done > 0 ? 'completed' : 'failed',
      progress: done > 0 ? 100 : 0,
      message: `已对 ${done}/${reprocessTargets.length} 个文档提交重新向量化（临时方案，待库级 rebuild 接口）`
    }
  }
}

export async function fetchRebuildStatus(
  kbId: string | number,
  jobId: string
): Promise<KbRebuildJob | null> {
  if (MOCK_OPEN()) {
    const job = mockJobs.get(jobId)
    if (!job) return null
    return unwrap(await mockResolve({ ...job }, { delay: 80 }))
  }

  try {
    const res = (await request.get(`/api/knowledge-bases/${kbId}/rebuild/${jobId}`, {
      silent: true
    })) as ApiResponse<KbRebuildJob>
    return unwrap(res)
  } catch {
    return null
  }
}

/**
 * 拉取后端真实索引配置，成功后覆盖 LocalStorage（缓存仅作二次加速）
 * 失败时回退本地缓存 / 默认值，不抛错阻断页面
 */
export async function fetchKbIndexConfig(kbId: string | number): Promise<KbIndexConfig> {
  if (kbId == null || kbId === '') {
    return normalizeKbIndexConfig(KB_INDEX_DEFAULTS)
  }

  if (MOCK_OPEN()) {
    const local = resolveKbIndexConfig(kbId).config
    const next = unwrap(await mockResolve(local, { delay: 80 }))
    const normalized = normalizeKbIndexConfig(next || local)
    saveKbIndexConfig(kbId, normalized)
    return normalized
  }

  try {
    const res = (await request.get(`/api/knowledge-bases/${kbId}/index-config`, {
      silent: true
    })) as ApiResponse<KbIndexConfig>
    const remote = unwrap(res)
    const normalized = normalizeKbIndexConfig(remote)
    // 后端为准：覆盖本地缓存
    saveKbIndexConfig(kbId, normalized)
    return normalized
  } catch {
    // 二次加速：接口失败再用本地缓存
    const cached = loadKbIndexConfig(kbId)
    if (cached) return normalizeKbIndexConfig(cached)
    return normalizeKbIndexConfig(KB_INDEX_DEFAULTS)
  }
}
