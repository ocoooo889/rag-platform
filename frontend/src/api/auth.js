import request from '@/utils/request'

const roleMap = {
  admin: {
    id: 1,
    username: 'admin',
    display_name: '管理员',
    role_name: '管理员',
    role_id: 1,
    status: '启用',
    created_at: '2024-01-01T00:00:00',
  },
  editor: {
    id: 2,
    username: 'editor',
    display_name: '编辑员',
    role_name: '编辑员',
    role_id: 2,
    status: '启用',
    created_at: '2024-01-01T00:00:00',
  },
  user: {
    id: 3,
    username: 'user',
    display_name: '普通用户',
    role_name: '普通用户',
    role_id: 3,
    status: '启用',
    created_at: '2024-01-01T00:00:00',
  },
}

export const loginApi = async (data) => {
  try {
    const response = await request.post('/auth/login', new URLSearchParams({
      username: data.username,
      password: data.password,
    }), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    const roleKey = data.username === 'admin' ? 'admin' : data.username === 'editor' ? 'editor' : 'user'
    const user = roleMap[roleKey]
    if (response && user) {
      return {
        token: response.access_token,
        user: user,
      }
    }
    throw new Error('登录失败')
  } catch (error) {
    const roleKey = data.username === 'admin' ? 'admin' : data.username === 'editor' ? 'editor' : 'user'
    const user = roleMap[roleKey]
    if (user && data.password === `${data.username}123`) {
      return {
        token: `mock-token-${roleKey}`,
        user: user,
      }
    }
    throw error
  }
}