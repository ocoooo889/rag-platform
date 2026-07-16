import request from '@/utils/request'

const mockRoles = [
  { id: 1, name: '管理员', permissions: 'all' },
  { id: 2, name: '编辑员', permissions: 'edit' },
  { id: 3, name: '普通用户', permissions: 'view' },
]

export const getRolesApi = async () => {
  try {
    return await request.get('/roles')
  } catch {
    return mockRoles
  }
}

export const createRoleApi = async (data) => {
  try {
    return await request.post('/roles', data)
  } catch {
    const newRole = { id: Date.now(), ...data }
    mockRoles.push(newRole)
    return newRole
  }
}

export const updateRoleApi = async (id, data) => {
  try {
    return await request.put(`/roles/${id}`, data)
  } catch {
    const idx = mockRoles.findIndex(r => r.id === id)
    if (idx !== -1) {
      mockRoles[idx] = { ...mockRoles[idx], ...data }
    }
    return mockRoles[idx]
  }
}

export const deleteRoleApi = async (id) => {
  try {
    return await request.delete(`/roles/${id}`)
  } catch {
    const idx = mockRoles.findIndex(r => r.id === id)
    if (idx !== -1) {
      mockRoles.splice(idx, 1)
    }
    return { msg: '角色删除成功' }
  }
}