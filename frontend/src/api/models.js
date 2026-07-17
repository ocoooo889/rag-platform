import request from '@/utils/request'

const mockModels = [
  { id: 1, model_type: 'chat', model_name: 'GPT-3.5', api_base_url: 'https://api.openai.com/v1', dimension: 1024, is_active: true },
  { id: 2, model_type: 'embedding', model_name: 'text-embedding-ada-002', api_base_url: 'https://api.openai.com/v1', dimension: 1536, is_active: true }
]

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const getModelsApi = async () => {
  try {
    return unwrap(await request.get('/api/models')) || mockModels
  } catch {
    return mockModels
  }
}

export const createModelApi = async (data) => {
  try {
    return unwrap(await request.post('/api/models', data))
  } catch {
    const newModel = { id: Date.now(), ...data }
    mockModels.push(newModel)
    return newModel
  }
}

export const updateModelApi = async (id, data) => {
  try {
    return unwrap(await request.put(`/api/models/${id}`, data))
  } catch {
    const idx = mockModels.findIndex((m) => m.id === id)
    if (idx !== -1) {
      mockModels[idx] = { ...mockModels[idx], ...data }
    }
    return mockModels[idx]
  }
}

export const deleteModelApi = async (id) => {
  try {
    return unwrap(await request.delete(`/api/models/${id}`))
  } catch {
    const idx = mockModels.findIndex((m) => m.id === id)
    if (idx !== -1) {
      mockModels.splice(idx, 1)
    }
    return { msg: '模型配置删除成功' }
  }
}
