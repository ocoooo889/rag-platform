import request from '@/utils/request'

const mockRoles = [
  { id: 1, name: '管理员', permissions: 'all' },
  { id: 2, name: '编辑员', permissions: 'edit' },
  { id: 3, name: '普通用户', permissions: 'view' }
]

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const getRolesApi = async () => {
  try {
    return unwrap(await request.get('/api/roles')) || mockRoles
  } catch {
    return mockRoles
  }
}

export const createRoleApi = async (data) => {
  try {
    return unwrap(await request.post('/api/roles', data))
  } catch {
    const newRole = { id: Date.now(), ...data }
    mockRoles.push(newRole)
    return newRole
  }
}

export const updateRoleApi = async (id, data) => {
  try {
    return unwrap(await request.put(`/api/roles/${id}`, data))
  } catch {
    const idx = mockRoles.findIndex((r) => r.id === id)
    if (idx !== -1) {
      mockRoles[idx] = { ...mockRoles[idx], ...data }
    }
    return mockRoles[idx]
  }
}

export const deleteRoleApi = async (id) => {
  try {
    return unwrap(await request.delete(`/api/roles/${id}`))
  } catch {
    const idx = mockRoles.findIndex((r) => r.id === id)
    if (idx !== -1) {
      mockRoles.splice(idx, 1)
    }
    return { msg: '角色删除成功' }
  }
}
