/**
 * 品牌主题色预设（按日间 / 夜间分列）
 * 保存字段仍为 brand_theme_color
 */

/** 日间：基础色 + 浅色系 */
export const THEME_COLOR_PRESETS_LIGHT = [
  /* 红 / 暖 */
  { id: 'garnet', label: '石榴暗红', value: '#A63D4A' },
  { id: 'terra-orange', label: '陶土暖橙', value: '#C97C48' },
  { id: 'cream-peach', label: '奶油蜜桃粉', value: '#E8A994' },
  { id: 'apricot-cream', label: '浅杏奶黄', value: '#E6C98A' },
  { id: 'mist-coral', label: '雾桃珊瑚', value: '#E8907A' },

  /* 绿 / 青 */
  { id: 'teal', label: '青石', value: '#3DB89A' },
  { id: 'deep-sea', label: '深海青碧', value: '#28B8C8' },

  /* 蓝 */
  { id: 'deep-indigo', label: '深空靛蓝', value: '#3660D8' },
  { id: 'ice', label: '冰蓝', value: '#3D9BFF' },

  /* 紫 */
  { id: 'ash-violet', label: '灰调堇紫', value: '#9480E0' },

  /* 中性 */
  { id: 'graphite-blue', label: '石墨灰蓝', value: '#687C9C' },
  { id: 'cool-silver', label: '冷银灰', value: '#96A2B8' }
]

/** 夜间：基础十色 + 暗薰衣草紫 + 纯黑 */
export const THEME_COLOR_PRESETS_DARK = [
  /* 红 / 暖 */
  { id: 'garnet', label: '石榴暗红', value: '#A63D4A' },
  { id: 'terra-orange', label: '陶土暖橙', value: '#C97C48' },
  { id: 'matte-gold', label: '哑光浅鎏金', value: '#D4B060' },

  /* 绿 / 青 */
  { id: 'teal', label: '青石', value: '#3DB89A' },
  { id: 'deep-sea', label: '深海青碧', value: '#28B8C8' },

  /* 蓝 */
  { id: 'deep-indigo', label: '深空靛蓝', value: '#3660D8' },
  { id: 'ice', label: '冰蓝', value: '#3D9BFF' },

  /* 紫 */
  { id: 'ash-violet', label: '灰调堇紫', value: '#9480E0' },
  { id: 'dusk-lavender', label: '暗薰衣草紫', value: '#8369D8' },

  /* 中性 / 黑 */
  { id: 'graphite-blue', label: '石墨灰蓝', value: '#687C9C' },
  { id: 'cool-silver', label: '冷银灰', value: '#96A2B8' },
  { id: 'pure-black', label: '纯黑', value: '#000000' }
]

/** 全量并集（校验 / 就近匹配用） */
export const THEME_COLOR_PRESETS = (() => {
  const map = new Map()
  for (const p of [...THEME_COLOR_PRESETS_DARK, ...THEME_COLOR_PRESETS_LIGHT]) {
    if (!map.has(p.id)) map.set(p.id, p)
  }
  return [...map.values()]
})()

export const THEME_COLOR_VALUES = THEME_COLOR_PRESETS.map((p) => p.value)

export function themePresetsForMode(mode) {
  return mode === 'light' ? THEME_COLOR_PRESETS_LIGHT : THEME_COLOR_PRESETS_DARK
}

export function nearestThemePreset(color, mode) {
  const list = mode ? themePresetsForMode(mode) : THEME_COLOR_PRESETS
  const raw = String(color || '').trim().toUpperCase()
  const hit = list.find((p) => p.value.toUpperCase() === raw)
  if (hit) return hit
  // 当前模式列表没有时，在全量里找（例如夜间选的纯黑切到日间）
  const any = THEME_COLOR_PRESETS.find((p) => p.value.toUpperCase() === raw)
  if (any) {
    const inMode = list.find((p) => p.id === any.id)
    if (inMode) return inMode
  }
  return list.find((p) => p.id === 'ice') || list[0]
}
