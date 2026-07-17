import { formatDate } from './format'

/**
 * 将单元格内容转义为 CSV 安全字段
 * 含逗号、换行、双引号时用双引号包裹，内部双引号加倍
 * @param {*} cell
 * @returns {string}
 */
function escapeCSVCell(cell) {
  const raw = cell == null ? '' : String(cell)
  if (/[",\r\n]/.test(raw)) {
    return `"${raw.replace(/"/g, '""')}"`
  }
  return raw
}

/**
 * 纯前端 CSV 导出（UTF-8 BOM，兼容中文 Excel）
 * 前置判空：无数据不执行下载
 * @param {Array<Object>} rows 数据行
 * @param {Array<{key:string,label:string}>} columns 列定义
 * @param {string} [filePrefix='rag检索结果'] 文件名前缀
 * @returns {boolean} 是否成功触发下载
 */
export function exportCSV(rows, columns, filePrefix = 'rag检索结果') {
  // 前置判空：空数组直接阻断，避免导出空文件
  if (!Array.isArray(rows) || rows.length === 0) {
    return false
  }
  if (!Array.isArray(columns) || columns.length === 0) {
    return false
  }

  const header = columns.map((col) => escapeCSVCell(col.label)).join(',')
  const body = rows
    .map((row) => columns.map((col) => escapeCSVCell(row[col.key])).join(','))
    .join('\r\n')

  // \uFEFF 为 UTF-8 BOM，保证 Excel 正确识别中文
  const csvContent = `\uFEFF${header}\r\n${body}`
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const fileName = `${filePrefix}_${formatDate(new Date(), 'YYYYMMDD')}.csv`
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return true
}
