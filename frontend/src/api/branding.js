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

export const getBrandingApi = async () => {
  if (isMockOpen()) {
    return { ...mockBranding }
  }
  return unwrap(await request.get('/api/system/branding'))
}

export const updateBrandingApi = async (data) => {
  if (isMockOpen()) {
    Object.assign(mockBranding, data)
    return { ...mockBranding }
  }
  const formData = new FormData()
  for (const key in data) {
    if (data[key] !== null && data[key] !== undefined) {
      formData.append(key, data[key])
    }
  }
  return unwrap(await request.put('/api/system/branding', formData))
}
