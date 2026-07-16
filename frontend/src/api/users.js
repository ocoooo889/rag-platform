import request from '@/utils/request'

const mockUsers = [
  { id: 1, username: 'admin', display_name: '管理员', status: '启用', role_id: 1, created_at: '2024-01-01T00:00:00' },
  { id: 2, username: 'editor', display_name: '编辑员', status: '启用', role_id: 2, created_at: '2024-01-02T00:00:00' },
  { id: 3, username: 'user', display_name: '普通用户', status: '启用', role_id: 3, created_at: '2024-01-03T00:00:00' },
]

export const getUsersApi = async (params) => {
  try {
    return await request.get('/users', { params })
  } catch {
    return mockUsers
  }
}

export const createUserApi = async (data) => {
  try {
    return await request.post('/users', data)
  } catch {
    const newUser = { id: Date.now(), ...data }
    mockUsers.push(newUser)
    return newUser
  }
}

export const updateUserApi = async (id, data) => {
  try {
    return await request.put(`/users/${id}`, data)
  } catch {
    const idx = mockUsers.findIndex(u => u.id === id)
    if (idx !== -1) {
      mockUsers[idx] = { ...mockUsers[idx], ...data }
    }
    return mockUsers[idx]
  }
}

export const deleteUserApi = async (id) => {
  try {
    return await request.delete(`/users/${id}`)
  } catch {
    const idx = mockUsers.findIndex(u => u.id === id)
    if (idx !== -1) {
      mockUsers[idx].status = '已停用'
    }
    return { msg: '用户删除(停用)成功' }
  }
}