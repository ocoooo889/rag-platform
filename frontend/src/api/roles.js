import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { MOCK_ROLES, nextMockId } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

const roles = [...MOCK_ROLES]

export const getRolesApi = async () => {
  if (isMockOpen()) return unwrap(await mockResolve(roles))
  return unwrap(await request.get('/api/roles'))
}

export const createRoleApi = async (data) => {
  if (isMockOpen()) {
    const row = {
      id: nextMockId('r'),
      name: data.name,
      description: data.description || '',
      permissions: data.permissions || [],
      created_at: new Date().toISOString()
    }
    roles.push(row)
    return unwrap(await mockResolve(row))
  }
  return unwrap(await request.post('/api/roles', data))
}

export const updateRoleApi = async (id, data) => {
  if (isMockOpen()) {
    const idx = roles.findIndex((r) => String(r.id) === String(id))
    if (idx === -1) return mockReject(404, '角色不存在')
    roles[idx] = { ...roles[idx], ...data }
    return unwrap(await mockResolve(roles[idx]))
  }
  return unwrap(await request.put(`/api/roles/${id}`, data))
}

export const deleteRoleApi = async (id) => {
  if (isMockOpen()) {
    const idx = roles.findIndex((r) => String(r.id) === String(id))
    if (idx === -1) return mockReject(404, '角色不存在')
    roles.splice(idx, 1)
    return unwrap(await mockResolve(null))
  }
  return unwrap(await request.delete(`/api/roles/${id}`))
}
