/**
 * 品牌主题色预设（暗色玻璃风）
 * 按色盘色相排序：红 → 橙 → 金 → 绿 → 青 → 蓝 → 紫 → 中性灰 → 黑
 * 保存字段仍为 brand_theme_color
 */
export const THEME_COLOR_PRESETS = [
  /* 红 / 暖 */
  { id: 'garnet', label: '石榴暗红', value: '#A63D4A' },
  { id: 'terra-orange', label: '陶土暖橙', value: '#C97C48' },
  { id: 'matte-gold', label: '哑光浅鎏金', value: '#D4B060' },

  /* 绿 / 青石族 */
  { id: 'forest-teal', label: '森屿灰绿', value: '#399E89' },
  { id: 'teal', label: '青石', value: '#3DB89A' },
  { id: 'mint-moss', label: '薄荷苔绿', value: '#40C8A6' },

  /* 青 / 蓝 */
  { id: 'deep-sea', label: '深海青碧', value: '#28B8C8' },
  { id: 'cyan', label: '青蓝', value: '#4ECBDE' },
  { id: 'deep-indigo', label: '深空靛蓝', value: '#3660D8' },
  { id: 'ice', label: '冰蓝', value: '#3D9BFF' },
  { id: 'mist-sky', label: '浅雾天蓝', value: '#54A4F7' },

  /* 紫 */
  { id: 'violet', label: '雾紫', value: '#7B6CFF' },
  { id: 'dusk-lavender', label: '暗薰衣草紫', value: '#8369D8' },
  { id: 'ash-violet', label: '灰调堇紫', value: '#9480E0' },

  /* 中性 / 黑 */
  { id: 'graphite-blue', label: '石墨灰蓝', value: '#687C9C' },
  { id: 'mist-platinum', label: '雾铂银', value: '#8A9BB3' },
  { id: 'cool-silver', label: '冷银灰', value: '#96A2B8' },
  { id: 'pure-black', label: '纯黑', value: '#000000' }
]

export const THEME_COLOR_VALUES = THEME_COLOR_PRESETS.map((p) => p.value)

export function nearestThemePreset(color) {
  const raw = String(color || '').trim().toUpperCase()
  const hit = THEME_COLOR_PRESETS.find((p) => p.value.toUpperCase() === raw)
  if (hit) return hit
  return THEME_COLOR_PRESETS.find((p) => p.id === 'ice') || THEME_COLOR_PRESETS[0]
}
