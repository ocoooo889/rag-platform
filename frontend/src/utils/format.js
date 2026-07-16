/**
 * 字节格式化：自动换算为 KB / MB
 * @param {number} bytes 文件字节数
 * @returns {string}
 */
export function formatFileSize(bytes) {
  const size = Number(bytes) || 0
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

/**
 * 日期格式化
 * @param {string|number|Date} date 日期
 * @param {'YYYYMMDD'|'datetime'} pattern 输出模式
 * @returns {string}
 */
export function formatDate(date, pattern = 'YYYYMMDD') {
  const d = date ? new Date(date) : new Date()
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  if (pattern === 'datetime') {
    return `${y}-${m}-${day} ${h}:${min}:${s}`
  }
  return `${y}${m}${day}`
}
