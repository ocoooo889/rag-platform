/**
 * 登录 — Mock / Real 双分支（契约：token + user）
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { MOCK_USERS } from '@/mock/data'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

/**
 * @returns {{ token: string, user: object }}
 */
export async function loginApi(data) {
  if (isMockOpen()) {
    const username = (data?.username || '').trim()
    const password = data?.password || ''
    const user = MOCK_USERS.find((u) => u.username === username)
    // 演示口令：username + 123，或契约示例 admin123
    const okPwd =
      password === `${username}123` ||
      (username === 'admin' && password === 'admin123')
    if (!user || !okPwd) {
      return mockReject(401, '用户名或密码错误')
    }
    const res = await mockResolve({
      token: `mock-jwt-${user.id}`,
      user: { ...user }
    })
    return unwrap(res)
  }

  const response = await request.post('/api/auth/login', {
    username: data.username,
    password: data.password
  })
  const payload = unwrap(response) || {}
  const token = payload.token || payload.access_token || ''
  const user = payload.user || null
  if (!token || !user) {
    throw new Error(payload.message || payload.msg || '登录失败')
  }
  return { token, user }
}
