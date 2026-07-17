import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getBrandingApi } from '@/api/branding'

const BRANDING_KEY = 'rag_branding'

const DEFAULTS = {
  brand_name: 'RAG 智能知识平台',
  brand_logo_url: '/uploads/branding/logo.png',
  brand_favicon_url: '/uploads/branding/favicon.ico',
  brand_theme_color: '#409EFF',
  brand_login_title: '企业知识，智能问答',
  brand_footer_text: 'Powered by RAG Platform'
}

function readCachedBranding() {
  try {
    const raw = localStorage.getItem(BRANDING_KEY)
    return raw ? JSON.parse(raw) : { ...DEFAULTS }
  } catch (e) {
    return { ...DEFAULTS }
  }
}

function saveBrandingToCache(data) {
  try {
    localStorage.setItem(BRANDING_KEY, JSON.stringify(data))
  } catch (e) {
    console.error('Failed to save branding to localStorage', e)
  }
}

export const useBrandingStore = defineStore('branding', () => {
  const config = ref(readCachedBranding())

  const brandName = computed(() => config.value.brand_name || DEFAULTS.brand_name)
  const brandLogoUrl = computed(() => config.value.brand_logo_url || DEFAULTS.brand_logo_url)
  const brandFaviconUrl = computed(() => config.value.brand_favicon_url || DEFAULTS.brand_favicon_url)
  const brandThemeColor = computed(() => config.value.brand_theme_color || DEFAULTS.brand_theme_color)
  const brandLoginTitle = computed(() => config.value.brand_login_title || DEFAULTS.brand_login_title)
  const brandFooterText = computed(() => config.value.brand_footer_text || DEFAULTS.brand_footer_text)

  function setConfig(newConfig) {
    config.value = { ...DEFAULTS, ...newConfig }
    saveBrandingToCache(config.value)
  }

  function applyBranding() {
    if (typeof window !== 'undefined') {
      document.title = brandName.value
      const favicon = document.querySelector('link[rel="icon"]') || document.querySelector('link[rel="shortcut icon"]')
      if (favicon) {
        favicon.href = brandFaviconUrl.value
      }
      document.documentElement.style.setProperty('--el-color-primary', brandThemeColor.value)
    }
  }

  async function fetchBranding() {
    try {
      const data = await getBrandingApi()
      setConfig(data)
      applyBranding()
      return data
    } catch (error) {
      console.error('Failed to fetch branding:', error)
      applyBranding()
      throw error
    }
  }

  function resetToDefaults() {
    setConfig({ ...DEFAULTS })
    applyBranding()
  }

  return {
    config,
    brandName,
    brandLogoUrl,
    brandFaviconUrl,
    brandThemeColor,
    brandLoginTitle,
    brandFooterText,
    setConfig,
    applyBranding,
    fetchBranding,
    resetToDefaults
  }
})