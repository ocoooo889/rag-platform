/**
 * 知识库索引配置 / 重建 API
 * GET/PUT /api/knowledge-bases/{id}/index-config
 * POST /api/knowledge-bases/{id}/rebuild  （返回排队摘要，无 job 轮询）
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve } from '@/mock/flag'
import { saveKbIndexConfig, loadKbIndexConfig, removeKbIndexConfig } from '@/utils/localCache'
import {
  normalizeKbIndexConfig,
  resolveKbIndexConfig,
  toKbIndexConfigPayload,
  getKbIndexDefaults
} from '@/utils/kbIndex'
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
 * 保存索引配置：仅提交 BE 接受字段；成功后再写 LocalStorage
 */
export async function updateKbIndexConfig(
  kbId: string | number,
  config: KbIndexConfig
): Promise<KbIndexConfig> {
  const normalized = normalizeKbIndexConfig(config)
  const payload = toKbIndexConfigPayload(normalized)

  if (MOCK_OPEN()) {
    const saved = unwrap(await mockResolve({ ...normalized, ...payload, kb_id: String(kbId) }))
    const next = normalizeKbIndexConfig(saved || normalized)
    saveKbIndexConfig(kbId, next)
    return next
  }

  try {
    const res = (await request.put(`/api/knowledge-bases/${kbId}/index-config`, payload, {
      silent: true
    })) as ApiResponse<KbIndexConfig>
    const remote = unwrap(res)
    const next = normalizeKbIndexConfig({
      ...normalized,
      ...(remote || {}),
      create_snapshot: normalized.create_snapshot,
      sync_mode: normalized.sync_mode
    })
    saveKbIndexConfig(kbId, next)
    return next
  } catch (e) {
    removeKbIndexConfig(kbId)
    throw e
  }
}

/** 将 BE rebuild 摘要映射为前端 job（同步完成，无轮询路由） */
function mapRebuildSummary(kbId: string | number, data: Record<string, unknown>): KbRebuildJob {
  const queued = Number(data.queued ?? 0)
  const total = Number(data.total ?? 0)
  const skippedP = Number(data.skipped_processing ?? 0)
  const skippedF = Number(data.skipped_missing_file ?? 0)
  const ok = queued > 0 || total === 0
  return {
    job_id: `rebuild-sync-${kbId}-${Date.now()}`,
    kb_id: String(kbId),
    status: ok ? 'completed' : 'failed',
    progress: 100,
    total,
    queued,
    message: ok
      ? `已排队 ${queued}/${total} 篇文档重建（跳过 processing ${skippedP}，缺文件 ${skippedF}）`
      : `未能排队任何文档（跳过 processing ${skippedP}，缺文件 ${skippedF}）`
  }
}

/**
 * 触发知识库重建
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
    // BE 不接受 body；先确保配置已 PUT
    await updateKbIndexConfig(kbId, normalized)
    const res = (await request.post(
      `/api/knowledge-bases/${kbId}/rebuild`
    )) as ApiResponse<Record<string, unknown>>
    const data = unwrap(res) || {}
    return mapRebuildSummary(kbId, data as Record<string, unknown>)
  } catch {
    if (normalized.sync_mode !== 'force_all') {
      return {
        job_id: `local-pending-${kbId}`,
        kb_id: String(kbId),
        status: 'failed',
        progress: 0,
        message: '库级重建接口调用失败；「仅待处理」无法在前端完成同步。'
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
      message: `已对 ${done}/${reprocessTargets.length} 个文档提交重新向量化（降级方案）`
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
  // BE 无 GET .../rebuild/{job_id}；同步 rebuild 已返回终态
  return null
}

/**
 * 拉取后端真实索引配置，成功后覆盖 LocalStorage
 */
export async function fetchKbIndexConfig(kbId: string | number): Promise<KbIndexConfig> {
  if (kbId == null || kbId === '') {
    return normalizeKbIndexConfig(getKbIndexDefaults())
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
    saveKbIndexConfig(kbId, normalized)
    return normalized
  } catch {
    const cached = loadKbIndexConfig(kbId)
    if (cached) return normalizeKbIndexConfig(cached)
    return normalizeKbIndexConfig(getKbIndexDefaults())
  }
}
