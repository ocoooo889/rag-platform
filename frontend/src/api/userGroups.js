import request from '@/utils/request'
import { isMockOpen } from '@/mock/flag'

const mockGroups = [
  {
    id: 1,
    name: '研发部',
    description: '研发团队用户组',
    member_count: 3,
    kb_count: 2,
    member_ids: [1, 2, 3],
    kb_ids: [1, 2],
    created_at: '2024-01-01T00:00:00'
  },
  {
    id: 2,
    name: '产品部',
    description: '产品团队用户组',
    member_count: 2,
    kb_count: 1,
    member_ids: [4, 5],
    kb_ids: [1],
    created_at: '2024-01-02T00:00:00'
  }
]

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const getUserGroupsApi = async () => {
  if (isMockOpen()) return [...mockGroups]
  return unwrap(await request.get('/api/user-groups'))
}

export const createUserGroupApi = async (data) => {
  if (isMockOpen()) {
    const newGroup = {
      id: Date.now(),
      member_count: 0,
      kb_count: 0,
      member_ids: [],
      kb_ids: [],
      ...data,
      created_at: new Date().toISOString()
    }
    mockGroups.push(newGroup)
    return newGroup
  }
  return unwrap(await request.post('/api/user-groups', data))
}

export const updateUserGroupApi = async (id, data) => {
  if (isMockOpen()) {
    const idx = mockGroups.findIndex((g) => g.id === id)
    if (idx !== -1) mockGroups[idx] = { ...mockGroups[idx], ...data }
    return mockGroups[idx]
  }
  return unwrap(await request.put(`/api/user-groups/${id}`, data))
}

export const deleteUserGroupApi = async (id) => {
  if (isMockOpen()) {
    const idx = mockGroups.findIndex((g) => g.id === id)
    if (idx !== -1) mockGroups.splice(idx, 1)
    return { msg: '用户组删除成功' }
  }
  return unwrap(await request.delete(`/api/user-groups/${id}`))
}

export const updateGroupMembersApi = async (group_id, user_ids) => {
  if (isMockOpen()) {
    const idx = mockGroups.findIndex((g) => g.id === group_id)
    if (idx !== -1) {
      mockGroups[idx].member_ids = user_ids
      mockGroups[idx].member_count = user_ids.length
    }
    return { msg: '用户组成员更新成功', data: mockGroups[idx] }
  }
  return unwrap(await request.post(`/api/user-groups/${group_id}/members`, { user_ids }))
}

export const updateGroupKbAccessApi = async (group_id, kb_ids) => {
  if (isMockOpen()) {
    const idx = mockGroups.findIndex((g) => g.id === group_id)
    if (idx !== -1) {
      mockGroups[idx].kb_ids = kb_ids
      mockGroups[idx].kb_count = kb_ids.length
    }
    return { msg: '用户组知识库授权成功', data: mockGroups[idx] }
  }
  return unwrap(await request.post(`/api/user-groups/${group_id}/kb-access`, { kb_ids }))
}
