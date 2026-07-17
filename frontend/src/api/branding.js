import request from '@/utils/request'

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
  try {
    return unwrap(await request.get('/api/system/branding')) || mockBranding
  } catch {
    return mockBranding
  }
}

export const updateBrandingApi = async (data) => {
  try {
    const formData = new FormData()
    for (const key in data) {
      if (data[key] !== null && data[key] !== undefined) {
        formData.append(key, data[key])
      }
    }
    return unwrap(await request.put('/api/system/branding', formData))
  } catch {
    Object.assign(mockBranding, data)
    return mockBranding
  }
}