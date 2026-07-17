import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { MOCK_USERS, nextMockId } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

const users = MOCK_USERS.map((u) => ({ ...u }))

export const getUsersApi = async (params) => {
  if (isMockOpen()) {
    let list = [...users]
    const kw = (params?.keyword || params?.username || '').trim()
    if (kw) list = list.filter((u) => u.username.includes(kw) || (u.display_name || '').includes(kw))
    return unwrap(await mockResolve(list))
  }
  return unwrap(await request.get('/api/users', { params }))
}

export const createUserApi = async (data) => {
  if (isMockOpen()) {
    const row = {
      id: nextMockId('u'),
      username: data.username,
      display_name: data.display_name || data.username,
      role_id: data.role_id,
      role_name: data.role_name || '',
      status: data.status || '启用',
      created_at: new Date().toISOString()
    }
    users.push(row)
    return unwrap(await mockResolve({ user_id: row.id, ...row }))
  }
  return unwrap(await request.post('/api/users', data))
}

export const updateUserApi = async (id, data) => {
  if (isMockOpen()) {
    const idx = users.findIndex((u) => String(u.id) === String(id))
    if (idx === -1) return mockReject(404, '用户不存在')
    users[idx] = { ...users[idx], ...data }
    return unwrap(await mockResolve(users[idx]))
  }
  return unwrap(await request.put(`/api/users/${id}`, data))
}

export const deleteUserApi = async (id) => {
  if (isMockOpen()) {
    const idx = users.findIndex((u) => String(u.id) === String(id))
    if (idx === -1) return mockReject(404, '用户不存在')
    users[idx].status = '已停用'
    return unwrap(await mockResolve({ msg: '用户删除(停用)成功' }))
  }
  return unwrap(await request.delete(`/api/users/${id}`))
}
