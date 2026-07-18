/**
 * 文档状态 — 以后端契约为唯一数据源
 * 契约值：pending | processing | completed | failed
 *
 * 约定：
 * - store / API / 请求体：只存、只传契约值（DOC_STATUS）
 * - 页面展示文案：用 DOC_STATUS_LABEL，禁止把「就绪」等文案写回 status 字段
 * - 不要再引入 vectoring / ready 等平行枚举，避免对接时分不清本地/后端
 */
export const DOC_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
}

/** 展示文案（仅 UI，不是接口字段） */
export const DOC_STATUS_LABEL = {
  [DOC_STATUS.PENDING]: '等待中',
  [DOC_STATUS.PROCESSING]: '向量化中',
  [DOC_STATUS.COMPLETED]: '就绪',
  [DOC_STATUS.FAILED]: '失败'
}

/** 规范化后端返回（容错大小写；未知值按 pending） */
export function normalizeDocStatus(raw) {
  const s = String(raw || '').toLowerCase()
  if (s === DOC_STATUS.COMPLETED) return DOC_STATUS.COMPLETED
  if (s === DOC_STATUS.PROCESSING) return DOC_STATUS.PROCESSING
  if (s === DOC_STATUS.FAILED) return DOC_STATUS.FAILED
  if (s === DOC_STATUS.PENDING) return DOC_STATUS.PENDING
  // 历史误用兼容：若某处曾写成 ready/vectoring，映射回契约值
  if (s === 'ready') return DOC_STATUS.COMPLETED
  if (s === 'vectoring') return DOC_STATUS.PROCESSING
  return DOC_STATUS.PENDING
}

/** 命中测试 / 检索：仅 completed 可选 */
export function isDocSelectable(raw) {
  return normalizeDocStatus(raw) === DOC_STATUS.COMPLETED
}

/** @deprecated 使用 isDocSelectable；保留别名避免旧调用报错 */
export function isDocReady(raw) {
  return isDocSelectable(raw)
}

export function getDocStatusLabel(raw) {
  return DOC_STATUS_LABEL[normalizeDocStatus(raw)] || DOC_STATUS_LABEL[DOC_STATUS.PENDING]
}

/** Element Plus Tag 类型（展示层） */
export function getDocStatusTagType(raw) {
  const status = normalizeDocStatus(raw)
  if (status === DOC_STATUS.COMPLETED) return 'success'
  if (status === DOC_STATUS.PROCESSING) return 'primary'
  if (status === DOC_STATUS.FAILED) return 'danger'
  return 'info'
}

/** 状态色 class 后缀（与 variables.css 中 --status-* 对应） */
export function getDocStatusClassSuffix(raw) {
  return normalizeDocStatus(raw)
}

// 兼容旧导出名（逐步废弃）
export const DOC_UI_STATUS = DOC_STATUS
export function toUiDocStatus(raw) {
  return normalizeDocStatus(raw)
}
