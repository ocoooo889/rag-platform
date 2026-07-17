/**
 * 根据相似度返回全局 CSS 变量色值（禁止硬编码十六进制）
 * ≥0.8 绿 / 0.5~0.8 黄 / ＜0.5 红
 * @param {number} score 0~1 相似度
 * @returns {string} CSS 变量字符串
 */
export function getScoreColor(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return 'var(--score-color-low)'
  if (value >= 0.8) return 'var(--score-color-high)'
  if (value >= 0.5) return 'var(--score-color-mid)'
  return 'var(--score-color-low)'
}

/**
 * 相似度百分比展示（保留 1 位小数）
 * @param {number} score
 * @returns {string}
 */
export function formatScorePercent(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return '0%'
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`
}
