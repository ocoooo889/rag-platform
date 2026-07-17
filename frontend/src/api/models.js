import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { MOCK_MODELS, nextMockId } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

const models = MOCK_MODELS.map((m) => ({ ...m }))

export const getModelsApi = async () => {
  if (isMockOpen()) return unwrap(await mockResolve(models))
  return unwrap(await request.get('/api/models'))
}

export const createModelApi = async (data) => {
  if (isMockOpen()) {
    const row = { id: nextMockId('m'), ...data }
    models.push(row)
    return unwrap(await mockResolve(row))
  }
  return unwrap(await request.post('/api/models', data))
}

export const updateModelApi = async (id, data) => {
  if (isMockOpen()) {
    const idx = models.findIndex((m) => String(m.id) === String(id))
    if (idx === -1) return mockReject(404, '模型不存在')
    models[idx] = { ...models[idx], ...data }
    return unwrap(await mockResolve(models[idx]))
  }
  return unwrap(await request.put(`/api/models/${id}`, data))
}

export const deleteModelApi = async (id) => {
  if (isMockOpen()) {
    const idx = models.findIndex((m) => String(m.id) === String(id))
    if (idx === -1) return mockReject(404, '模型不存在')
    models.splice(idx, 1)
    return unwrap(await mockResolve(null))
  }
  return unwrap(await request.delete(`/api/models/${id}`))
}
