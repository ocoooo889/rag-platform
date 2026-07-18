import request from '@/utils/request'
import { isMockOpen } from '@/mock/flag'

const mockBranding = {
  brand_name: 'RAG 智能知识平台',
  brand_logo_url: '/uploads/branding/logo.png',
  brand_favicon_url: '/uploads/branding/favicon.ico',
  brand_theme_color: '#409EFF',
  brand_login_title: '企业知识，智能问答',
  brand_footer_text: 'Powered by RAG Platform'
}

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

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
  return unwrap(await request.get('/api/system/branding'))
}

export const updateBrandingApi = async (data) => {
  if (isMockOpen()) {
    if (data instanceof FormData) {
      for (const [key, value] of data.entries()) {
        if (typeof value === 'string') mockBranding[key] = value
      }
    } else {
      Object.assign(mockBranding, data)
    }
    return { ...mockBranding }
  }
  // 已是 FormData 时直接提交，避免 for...in 丢字段导致后端 422
  // 勿手动设 Content-Type，交给浏览器带 boundary
  return unwrap(await request.put('/api/system/branding', toFormData(data)))
}
