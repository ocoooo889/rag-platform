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

export const getBrandingApi = async () => {

  if (isMockOpen()) {
    return { ...mockBranding }

  try {
    const res = await request.get('/api/system/branding', { cache: 'no-cache' })
    const data = unwrap(res)
    console.log('getBrandingApi - raw response:', res)
    console.log('getBrandingApi - unwrapped data:', data)
    if (!data || typeof data !== 'object' || !data.brand_name) {
      console.warn('getBrandingApi - invalid data, using mock:', data)
      return mockBranding
    }
    return data
  } catch (error) {
    console.error('getBrandingApi error:', error)
    return mockBranding

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

  try {
    let formData = data
    if (!(data instanceof FormData)) {
      formData = new FormData()
      for (const key in data) {
        if (data[key] !== null && data[key] !== undefined) {
          formData.append(key, data[key])
        }
      }
    }
    const res = await request.put('/api/system/branding', formData)
    const result = unwrap(res)
    console.log('updateBrandingApi - raw response:', res)
    console.log('updateBrandingApi - unwrapped result:', result)
    return result
  } catch (error) {
    console.error('updateBrandingApi error:', error)
    if (data instanceof FormData) {
      const plainData = {}
      data.forEach((value, key) => {
        if (!(value instanceof File)) {
          plainData[key] = value
        }
      })
      Object.assign(mockBranding, plainData)
    } else {
      Object.assign(mockBranding, data)
    }
    throw error
  }

}
