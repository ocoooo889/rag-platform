/**
 * 评测模块 API（仅透传；关闭 Mock 时直接打后端，失败不回落本地假数据）
 *
 * 【后端待实现】建议路由：
 *   GET/POST  /api/eval/tasks
 *   DELETE    /api/eval/tasks/{id}
 *   POST      /api/eval/tasks/{id}/run
 *   GET       /api/eval/tasks/{id}/progress
 *   GET/POST  /api/eval/tasks/{id}/samples
 *   POST      /api/eval/tasks/{id}/samples/import
 *   GET       /api/eval/tasks/{id}/results
 *   GET       /api/eval/compare?ids=
 */
import request from '@/utils/request'
import { MOCK_OPEN, mockResolve, mockReject } from '@/mock/flag'
import type {
  ApiResponse,
  EvalComparePoint,
  EvalMetricRow,
  EvalProgress,
  EvalResultsPayload,
  EvalRunParams,
  EvalSample,
  EvalTask,
  EvalTaskStatus,
  PageResult
} from '@/types'

const mockTasks: EvalTask[] = [
  {
    id: 'eval-001',
    name: '基线召回评测',
    status: 'completed',
    created_at: '2026-07-19T10:00:00',
    sample_count: 3,
    progress: 100,
    params: {
      kb_id: 1,
      kb_name: '演示知识库',
      embedding_model: 'mock-embedding',
      chunk_size: Number.NaN,
      chunk_overlap: Number.NaN,
      chunk_mode: '',
      separators: '',
      clean_enabled: true
    }
  }
]

const mockSamples: EvalSample[] = [
  {
    id: 's1',
    task_id: 'eval-001',
    question: '公司考勤制度是什么？',
    expected_answer: '应按照员工手册执行',
    tags: '制度'
  },
  {
    id: 's2',
    task_id: 'eval-001',
    question: '报销流程有哪些步骤？',
    expected_answer: '提交申请-审批-打款',
    tags: '流程'
  },
  {
    id: 's3',
    task_id: 'eval-001',
    question: '年假如何申请？',
    expected_answer: '提前在系统提交，经直属主管审批',
    tags: '休假'
  }
]

const mockProgressTimers = new Map<string, ReturnType<typeof setInterval>>()

function unwrap<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in (res as object) && 'code' in (res as object)) {
    return (res as ApiResponse<T>).data
  }
  return res as T
}

function normalizeTask(raw: Partial<EvalTask> | null | undefined): EvalTask {
  const t = raw || {}
  return {
    id: String(t.id || ''),
    name: String(t.name || ''),
    status: (t.status as EvalTaskStatus) || 'pending',
    created_at: t.created_at || new Date().toISOString(),
    sample_count: Number(t.sample_count) || 0,
    rule_json: t.rule_json,
    error_message: t.error_message,
    params: t.params,
    progress: t.progress != null ? Number(t.progress) : undefined,
    progress_message: t.progress_message
  }
}

function normalizeMetric(raw: Partial<EvalMetricRow>): EvalMetricRow {
  return {
    sample_id: String(raw.sample_id || ''),
    question: String(raw.question || ''),
    answer: raw.answer != null ? String(raw.answer) : undefined,
    expected_answer: raw.expected_answer != null ? String(raw.expected_answer) : undefined,
    score: Number(raw.score) || 0,
    precision: raw.precision != null ? Number(raw.precision) : undefined,
    recall: raw.recall != null ? Number(raw.recall) : undefined,
    faithfulness: raw.faithfulness != null ? Number(raw.faithfulness) : undefined,
    detail: raw.detail,
    retrieval_mode: raw.retrieval_mode || (raw.retrieval_degraded ? 'keyword' : 'semantic'),
    retrieval_degraded: !!raw.retrieval_degraded,
    sources: Array.isArray(raw.sources) ? raw.sources : []
  }
}

/** 兼容 results：纯数组 或 分页 { items | list } */
export function unwrapEvalResults(payload: EvalResultsPayload | null | undefined): EvalMetricRow[] {
  if (payload == null) return []
  if (Array.isArray(payload)) {
    return payload.map((row) => normalizeMetric(row || {}))
  }
  if (typeof payload === 'object') {
    const page = payload as { items?: EvalMetricRow[]; list?: EvalMetricRow[] }
    const rows = Array.isArray(page.items)
      ? page.items
      : Array.isArray(page.list)
        ? page.list
        : []
    return rows.map((row) => normalizeMetric(row || {}))
  }
  return []
}

export async function fetchEvalTasks(params: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
} = {}): Promise<PageResult<EvalTask>> {
  if (MOCK_OPEN()) {
    let list = [...mockTasks]
    if (params.status) list = list.filter((t) => t.status === params.status)
    if (params.keyword) {
      const kw = params.keyword.toLowerCase()
      list = list.filter((t) => t.name.toLowerCase().includes(kw))
    }
    return unwrap(
      await mockResolve({
        items: list,
        total: list.length,
        page: params.page || 1,
        page_size: params.page_size || 10
      })
    )
  }

  const res = (await request.get('/api/eval/tasks', { params })) as ApiResponse<PageResult<EvalTask>>
  const data = unwrap(res) || { items: [], total: 0 }
  return {
    items: (data.items || []).map(normalizeTask),
    total: data.total || 0,
    page: data.page || params.page || 1,
    page_size: data.page_size || params.page_size || 10
  }
}

export async function createEvalTask(payload: {
  name: string
  rule_json?: string
  params: EvalRunParams
}): Promise<EvalTask> {
  if (MOCK_OPEN()) {
    if (!payload.name?.trim()) return mockReject(400, '请填写任务名称') as never
    if (payload.params?.kb_id == null || payload.params.kb_id === '') {
      return mockReject(400, '请选择知识库') as never
    }
    const row: EvalTask = {
      id: `eval-${Date.now()}`,
      name: payload.name.trim(),
      status: 'pending',
      created_at: new Date().toISOString(),
      sample_count: 0,
      rule_json: payload.rule_json,
      params: { ...payload.params },
      progress: 0
    }
    mockTasks.unshift(row)
    return unwrap(await mockResolve(row))
  }

  const res = (await request.post('/api/eval/tasks', payload)) as ApiResponse<EvalTask>
  return normalizeTask(unwrap(res))
}

/** 删除评测任务（创建后上传失败时前端回滚用） */
export async function deleteEvalTask(taskId: string): Promise<void> {
  if (MOCK_OPEN()) {
    const idx = mockTasks.findIndex((t) => t.id === taskId)
    if (idx < 0) return mockReject(404, '任务不存在') as never
    mockTasks.splice(idx, 1)
    for (let i = mockSamples.length - 1; i >= 0; i -= 1) {
      if (mockSamples[i].task_id === taskId) mockSamples.splice(i, 1)
    }
    if (mockProgressTimers.has(taskId)) {
      clearInterval(mockProgressTimers.get(taskId)!)
      mockProgressTimers.delete(taskId)
    }
    await mockResolve(null)
    return
  }
  await request.delete(`/api/eval/tasks/${taskId}`)
}

export async function startEvalTask(taskId: string): Promise<EvalProgress> {
  if (MOCK_OPEN()) {
    const task = mockTasks.find((t) => t.id === taskId)
    if (!task) return mockReject(404, '任务不存在') as never
    task.status = 'running'
    task.progress = 5
    task.progress_message = '评测任务已启动…'
    if (mockProgressTimers.has(taskId)) clearInterval(mockProgressTimers.get(taskId)!)
    const timer = setInterval(() => {
      const t = mockTasks.find((x) => x.id === taskId)
      if (!t) {
        clearInterval(timer)
        mockProgressTimers.delete(taskId)
        return
      }
      t.progress = Math.min(100, (t.progress || 0) + 18)
      t.progress_message = `评测进行中 ${t.progress}%`
      if ((t.progress || 0) >= 100) {
        t.status = 'completed'
        t.progress = 100
        t.progress_message = '评测完成'
        clearInterval(timer)
        mockProgressTimers.delete(taskId)
      }
    }, 700)
    mockProgressTimers.set(taskId, timer)
    return unwrap(
      await mockResolve({
        task_id: taskId,
        status: task.status,
        progress: task.progress || 0,
        message: task.progress_message
      })
    )
  }

  const res = (await request.post(`/api/eval/tasks/${taskId}/run`, {})) as ApiResponse<EvalProgress>
  return unwrap(res)
}

export async function fetchEvalProgress(taskId: string): Promise<EvalProgress> {
  if (MOCK_OPEN()) {
    const task = mockTasks.find((t) => t.id === taskId)
    if (!task) return mockReject(404, '任务不存在') as never
    return unwrap(
      await mockResolve(
        {
          task_id: taskId,
          status: task.status,
          progress: task.progress ?? (task.status === 'completed' ? 100 : 0),
          message: task.progress_message
        },
        { delay: 60 }
      )
    )
  }

  const res = (await request.get(`/api/eval/tasks/${taskId}/progress`)) as ApiResponse<EvalProgress>
  return unwrap(res)
}

export async function uploadEvalDataset(
  taskId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ imported: number }> {
  if (MOCK_OPEN()) {
    for (let p = 10; p <= 100; p += 30) {
      onProgress?.(p)
      await new Promise((r) => setTimeout(r, 120))
    }
    const task = mockTasks.find((t) => t.id === taskId)
    if (task) task.sample_count += 2
    return unwrap(await mockResolve({ imported: 2 }))
  }

  const form = new FormData()
  form.append('file', file)
  const res = (await request.post(`/api/eval/tasks/${taskId}/samples/import`, form, {
    onUploadProgress: (evt: { loaded: number; total?: number }) => {
      if (!onProgress || !evt.total) return
      onProgress(Math.round((evt.loaded / evt.total) * 100))
    }
  })) as ApiResponse<{ imported: number }>
  return unwrap(res)
}

export async function fetchEvalSamples(
  taskId: string,
  params: { page?: number; page_size?: number; keyword?: string } = {}
): Promise<PageResult<EvalSample>> {
  if (MOCK_OPEN()) {
    let list = mockSamples.filter((s) => s.task_id === taskId)
    if (params.keyword) {
      const kw = params.keyword.toLowerCase()
      list = list.filter(
        (s) =>
          s.question.toLowerCase().includes(kw) ||
          s.expected_answer.toLowerCase().includes(kw)
      )
    }
    return unwrap(
      await mockResolve({
        items: list,
        total: list.length,
        page: params.page || 1,
        page_size: params.page_size || 10
      })
    )
  }

  const res = (await request.get(`/api/eval/tasks/${taskId}/samples`, {
    params
  })) as ApiResponse<PageResult<EvalSample>>
  return unwrap(res)
}

export async function addEvalSample(
  taskId: string,
  payload: { question: string; expected_answer: string; tags?: string }
): Promise<EvalSample> {
  if (MOCK_OPEN()) {
    const row: EvalSample = {
      id: `s-${Date.now()}`,
      task_id: taskId,
      question: payload.question,
      expected_answer: payload.expected_answer,
      tags: payload.tags
    }
    mockSamples.push(row)
    const task = mockTasks.find((t) => t.id === taskId)
    if (task) task.sample_count += 1
    return unwrap(await mockResolve(row))
  }

  const res = (await request.post(
    `/api/eval/tasks/${taskId}/samples`,
    payload
  )) as ApiResponse<EvalSample>
  return unwrap(res)
}

export async function fetchEvalResults(taskId: string): Promise<EvalMetricRow[]> {
  if (MOCK_OPEN()) {
    const list = mockSamples
      .filter((s) => s.task_id === taskId)
      .map((s, idx) =>
        normalizeMetric({
          sample_id: s.id,
          question: s.question,
          expected_answer: s.expected_answer,
          answer:
            idx === 1
              ? '报销需先提交申请，再经财务审批后打款。'
              : `根据知识库：${s.expected_answer}`,
          score: idx === 1 ? 0.71 : 0.86,
          precision: idx === 1 ? 0.68 : 0.84,
          recall: idx === 1 ? 0.7 : 0.8,
          faithfulness: idx === 1 ? 0.75 : 0.92,
          detail: idx === 1 ? '部分关键实体未命中' : '命中期望要点',
          retrieval_degraded: idx === 1,
          retrieval_mode: idx === 1 ? 'keyword' : 'semantic',
          sources: [
            {
              chunk_id: `c-${s.id}-1`,
              document_name: '员工手册.md',
              content: s.expected_answer,
              score: idx === 1 ? 0.42 : 0.88
            }
          ]
        })
      )
    return unwrap(await mockResolve(list))
  }

  const res = (await request.get(`/api/eval/tasks/${taskId}/results`)) as ApiResponse<EvalResultsPayload>
  return unwrapEvalResults(unwrap(res))
}

export async function fetchEvalCompare(taskIds: string[]): Promise<EvalComparePoint[]> {
  if (MOCK_OPEN()) {
    const points: EvalComparePoint[] = []
    for (const id of taskIds) {
      const t = mockTasks.find((x) => x.id === id)
      const name = t?.name || id
      points.push(
        { task_id: id, task_name: name, metric: 'score', value: 0.82 },
        { task_id: id, task_name: name, metric: 'precision', value: 0.8 },
        { task_id: id, task_name: name, metric: 'recall', value: 0.75 },
        { task_id: id, task_name: name, metric: 'faithfulness', value: 0.88 }
      )
    }
    return unwrap(await mockResolve(points))
  }

  const res = (await request.get('/api/eval/compare', {
    params: { ids: taskIds.join(',') }
  })) as ApiResponse<EvalComparePoint[]>
  return unwrap(res) || []
}
