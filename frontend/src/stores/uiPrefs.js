/**
 * 界面偏好：系统文字大 / 中 / 小（本地持久化）
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY = 'rag-ui-font-size'
export const UI_FONT_OPTIONS = [
  { value: 'large', label: '大' },
  { value: 'medium', label: '中' },
  { value: 'small', label: '小' }
]

function readFontSize() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'large' || raw === 'medium' || raw === 'small') return raw
  } catch {
    /* ignore */
  }
  return 'medium'
}

function writeFontSize(value) {
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* ignore */
  }
}

export const useUiPrefsStore = defineStore('uiPrefs', () => {
  const fontSize = ref(readFontSize())

  const fontSizeLabel = computed(() => {
    const hit = UI_FONT_OPTIONS.find((o) => o.value === fontSize.value)
    return hit ? hit.label : '中'
  })

  function applyFontSize(value = fontSize.value) {
    if (typeof document === 'undefined') return
    const next = value === 'large' || value === 'small' || value === 'medium' ? value : 'medium'
    document.documentElement.setAttribute('data-ui-font', next)
  }

  function setFontSize(value) {
    const next = value === 'large' || value === 'small' || value === 'medium' ? value : 'medium'
    fontSize.value = next
    writeFontSize(next)
    applyFontSize(next)
  }

  function init() {
    applyFontSize(fontSize.value)
  }

  return {
    fontSize,
    fontSizeLabel,
    setFontSize,
    applyFontSize,
    init,
    options: UI_FONT_OPTIONS
  }
})
