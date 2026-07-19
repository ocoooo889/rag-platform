/**
 * 界面偏好：字号 + 日夜间（仅管理后台；登录页不同步）
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const FONT_KEY = 'rag-ui-font-size'
const COLOR_MODE_KEY = 'rag-ui-color-mode'

export const UI_FONT_OPTIONS = [
  { value: 'large', label: '大' },
  { value: 'medium', label: '中' },
  { value: 'small', label: '小' }
]

/** dark=夜间（默认）；light=日间 */
export const UI_COLOR_MODE_OPTIONS = [
  { value: 'dark', label: '夜间' },
  { value: 'light', label: '日间' }
]

function readFontSize() {
  try {
    const raw = localStorage.getItem(FONT_KEY)
    if (raw === 'large' || raw === 'medium' || raw === 'small') return raw
  } catch {
    /* ignore */
  }
  return 'medium'
}

function writeFontSize(value) {
  try {
    localStorage.setItem(FONT_KEY, value)
  } catch {
    /* ignore */
  }
}

function readColorMode() {
  try {
    const raw = localStorage.getItem(COLOR_MODE_KEY)
    if (raw === 'light' || raw === 'dark') return raw
  } catch {
    /* ignore */
  }
  return 'dark'
}

function writeColorMode(value) {
  try {
    localStorage.setItem(COLOR_MODE_KEY, value)
  } catch {
    /* ignore */
  }
}

export const useUiPrefsStore = defineStore('uiPrefs', () => {
  const fontSize = ref(readFontSize())
  const colorMode = ref(readColorMode())

  const fontSizeLabel = computed(() => {
    const hit = UI_FONT_OPTIONS.find((o) => o.value === fontSize.value)
    return hit ? hit.label : '中'
  })

  const colorModeLabel = computed(() => {
    const hit = UI_COLOR_MODE_OPTIONS.find((o) => o.value === colorMode.value)
    return hit ? hit.label : '夜间'
  })

  const isLight = computed(() => colorMode.value === 'light')

  function applyFontSize(value = fontSize.value) {
    if (typeof document === 'undefined') return
    const next = value === 'large' || value === 'small' || value === 'medium' ? value : 'medium'
    document.documentElement.setAttribute('data-ui-font', next)
  }

  /**
   * 仅在管理后台挂载 data-color-mode；登录页不调用 / 离开后台时 clear。
   */
  function applyColorMode(value = colorMode.value, { admin = true } = {}) {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    if (!admin) {
      root.removeAttribute('data-color-mode')
      return
    }
    const next = value === 'light' ? 'light' : 'dark'
    root.setAttribute('data-color-mode', next)
  }

  function clearAdminColorMode() {
    if (typeof document === 'undefined') return
    document.documentElement.removeAttribute('data-color-mode')
  }

  function setFontSize(value) {
    const next = value === 'large' || value === 'small' || value === 'medium' ? value : 'medium'
    fontSize.value = next
    writeFontSize(next)
    applyFontSize(next)
  }

  function setColorMode(value) {
    const next = value === 'light' ? 'light' : 'dark'
    colorMode.value = next
    writeColorMode(next)
    // 仅当当前在后台（有 admin-theme）时立刻作用到 DOM
    if (document.documentElement.classList.contains('admin-theme')) {
      applyColorMode(next, { admin: true })
    }
  }

  function toggleColorMode() {
    setColorMode(colorMode.value === 'light' ? 'dark' : 'light')
  }

  function init() {
    applyFontSize(fontSize.value)
    if (document.documentElement.classList.contains('admin-theme')) {
      applyColorMode(colorMode.value, { admin: true })
    }
  }

  return {
    fontSize,
    fontSizeLabel,
    colorMode,
    colorModeLabel,
    isLight,
    setFontSize,
    setColorMode,
    toggleColorMode,
    applyFontSize,
    applyColorMode,
    clearAdminColorMode,
    init,
    options: UI_FONT_OPTIONS,
    colorModeOptions: UI_COLOR_MODE_OPTIONS
  }
})
