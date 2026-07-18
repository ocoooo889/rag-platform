import request from '@/utils/request'
import { isMockOpen } from '@/mock/flag'

const mockBranding = {
  brand_name: 'RAG 智能知识平台',
  brand_logo_url: '/uploads/branding/logo.png',
  brand_favicon_url: '/uploads/branding/favicon.ico',
  brand_theme_color: '#409EFF',
  brand_login_title: '企业知识，智能问答',
  brand_footer_text: 'Powered by RAG Platform',
  brand_logo_history: []
}

function unwrap(res) {
  if (res && typeof res === 'object') {
    if ('code' in res && 'data' in res) {
      return res.data
    }
    if (res.data !== undefined && typeof res.data === 'object') {
      if ('code' in res.data && 'data' in res.data) {
        return res.data.data
      }
      return res.data
    }
  }
  return res
}

/** 已是 FormData 则原样返回，避免 for...in FormData 丢字段导致后端 422 */
function toFormData(data) {
  if (data instanceof FormData) return data
  const formData = new FormData()
  if (!data || typeof data !== 'object') return formData
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) continue
    formData.append(key, value)
  }
  return formData
}

export const getBrandingApi = async () => {
  if (isMockOpen()) {
    return { ...mockBranding }
  }
  try {
    const res = await request.get('/api/system/branding', { cache: 'no-cache' })
    const data = unwrap(res)
    if (!data || typeof data !== 'object' || !data.brand_name) {
      return { ...mockBranding }
    }
    return data
  } catch (error) {
    console.error('getBrandingApi error:', error)
    return { ...mockBranding }
  }
}

export const updateBrandingApi = async (data) => {
  if (isMockOpen()) {
    if (data instanceof FormData) {
      for (const [key, value] of data.entries()) {
        if (typeof value === 'string') mockBranding[key] = value
        if (key === 'brand_logo' && value instanceof File) {
          const url = `/uploads/branding/logo_${Date.now()}.png?v=${Date.now()}`
          mockBranding.brand_logo_url = url
          const hist = Array.isArray(mockBranding.brand_logo_history)
            ? mockBranding.brand_logo_history
            : []
          mockBranding.brand_logo_history = [url, ...hist.filter((u) => u !== url)].slice(0, 3)
        }
        if (key === 'brand_logo_history_pick' && typeof value === 'string') {
          mockBranding.brand_logo_url = value
          const hist = Array.isArray(mockBranding.brand_logo_history)
            ? mockBranding.brand_logo_history
            : []
          mockBranding.brand_logo_history = [value, ...hist.filter((u) => u !== value)].slice(0, 3)
        }
      }
    } else {
      Object.assign(mockBranding, data)
    }
    return { ...mockBranding, brand_logo_history: [...(mockBranding.brand_logo_history || [])] }
  }
  // 勿手动设 Content-Type，交给浏览器带 boundary
  const formData = toFormData(data)
  try {
    return unwrap(await request.put('/api/system/branding', formData))
  } catch (error) {
    console.error('updateBrandingApi error:', error)
    throw error
  }
}
