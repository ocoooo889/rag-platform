import request from '@/utils/request'

const roleMap = {
  admin: {
    id: 1,
    username: 'admin',
    display_name: '管理员',
    role_name: '管理员',
    role_id: 1,
    status: '启用',
    created_at: '2024-01-01T00:00:00'
  },
  editor: {
    id: 2,
    username: 'editor',
    display_name: '编辑员',
    role_name: '编辑员',
    role_id: 2,
    status: '启用',
    created_at: '2024-01-01T00:00:00'
  },
  user: {
    id: 3,
    username: 'user',
    display_name: '普通用户',
    role_name: '普通用户',
    role_id: 3,
    status: '启用',
    created_at: '2024-01-01T00:00:00'
  }
}

/** 兼容完整返回体 {code,data} 与直接 data */
function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

export const loginApi = async (data) => {
  try {
    const response = await request.post(
      '/api/auth/login',
      new URLSearchParams({
        username: data.username,
        password: data.password
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    )
    const payload = unwrap(response) || {}
    const user = roleMap[data.role]
    if (payload && user) {
      return {
        token: payload.access_token || payload.token,
        user
      }
    }
    throw new Error('登录失败')
  } catch (error) {
    // 本地演示兜底：密码规则 username123
    const user = roleMap[data.role]
    if (user && data.password === `${data.username}123`) {
      return {
        token: `mock-token-${data.role}`,
        user
      }
    }
    throw error
  }
}
