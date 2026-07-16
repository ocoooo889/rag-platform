import request from '@/utils/request'

const mockModels = [
  { id: 1, model_type: 'chat', model_name: 'GPT-3.5', api_base_url: 'https://api.openai.com/v1', dimension: 1024, is_active: true },
  { id: 2, model_type: 'embedding', model_name: 'text-embedding-ada-002', api_base_url: 'https://api.openai.com/v1', dimension: 1536, is_active: true },
]

export const getModelsApi = async () => {
  try {
    return await request.get('/models')
  } catch {
    return mockModels
  }
}

export const createModelApi = async (data) => {
  try {
    return await request.post('/models', data)
  } catch {
    const newModel = { id: Date.now(), ...data }
    mockModels.push(newModel)
    return newModel
  }
}

export const updateModelApi = async (id, data) => {
  try {
    return await request.put(`/models/${id}`, data)
  } catch {
    const idx = mockModels.findIndex(m => m.id === id)
    if (idx !== -1) {
      mockModels[idx] = { ...mockModels[idx], ...data }
    }
    return mockModels[idx]
  }
}

export const deleteModelApi = async (id) => {
  try {
    return await request.delete(`/models/${id}`)
  } catch {
    const idx = mockModels.findIndex(m => m.id === id)
    if (idx !== -1) {
      mockModels.splice(idx, 1)
    }
    return { msg: '模型配置删除成功' }
  }
}