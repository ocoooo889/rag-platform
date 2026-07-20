/**
 * 登录 — Mock / Real 双分支
 * Real: POST /api/auth/login（form）→ data: { access_token, user }
 */
import request from '@/utils/request'
import { isMockOpen, mockResolve, mockReject } from '@/mock/flag'
import { MOCK_USERS } from '@/mock/data'
import { roleCodeToLabel } from '@/utils/role'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && ('code' in res || 'message' in res || 'msg' in res)) {
    return res.data
  }
  return res
}

function normalizeUser(user) {
  if (!user) return null
  const role = user.role || (user.role_name === '管理员' ? 'admin' : user.role_name === '普通用户' ? 'user' : '')
  return {
    ...user,
    role,
    role_name: user.role_name || roleCodeToLabel(role)
  }
}

/**
 * @returns {{ token: string, user: object }}
 */
export async function loginApi(data) {
  if (isMockOpen()) {
    const username = (data?.username || '').trim()
    const password = data?.password || ''
    const user = MOCK_USERS.find((u) => u.username === username)
    const okPwd =
      password === `${username}123` ||
      (username === 'admin' && password === 'admin123')
    if (!user || !okPwd) {
      return mockReject(401, '用户名或密码错误')
    }
    const role = user.role || (user.role_name === '管理员' ? 'admin' : 'user')
    const res = await mockResolve({
      token: `mock-jwt-${user.id}`,
      user: normalizeUser({ ...user, role, role_name: roleCodeToLabel(role) })
    })
    return unwrap(res)
  }

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
        },
        // 登录失败由页面提示，避免全局 401 跳转/「登录已过期」文案
        silent: true
      }
    )
    const payload = unwrap(response) || {}
    const token = payload.token || payload.access_token || ''
    if (!token) {
      const err = new Error(payload.message || payload.msg || '用户名或密码错误，请重新输入')
      err.code = response?.code || 401
      throw err
    }
    const user = normalizeUser(payload.user)
    if (!user) {
      throw new Error('登录响应缺少用户信息')
    }
    return { token, user }
  } catch (e) {
    const raw =
      e?.msg ||
      e?.message ||
      e?.response?.data?.msg ||
      e?.response?.data?.message ||
      ''
    const err = new Error('用户名或密码错误，请重新输入')
    err.code = e?.code || e?.response?.data?.code || e?.response?.status || 401
    err.detail = raw
    throw err
  }
}

/** 拉取当前用户（需已登录） */
export async function fetchMeApi() {
  if (isMockOpen()) {
    return null
  }
  // silent：由 ensureUserInfo / 全局 401 统一处理，避免重复弹窗
  const response = await request.get('/api/auth/me', { silent: true })
  return normalizeUser(unwrap(response))
}

/** 当前用户上传头像 */
export async function uploadAvatarApi(file) {
  if (isMockOpen()) {
    const url = URL.createObjectURL(file)
    return unwrap(
      await mockResolve({
        avatar_url: url,
        id: 'mock'
      })
    )
  }
  const form = new FormData()
  form.append('avatar', file)
  const response = await request.post('/api/auth/avatar', form)
  return normalizeUser(unwrap(response))
}

/** 当前用户修改资料 */
export async function updateProfileApi(data) {
  if (isMockOpen()) {
    return unwrap(
      await mockResolve({
        display_name: data.display_name,
        avatar_url: data.avatar_url || ''
      })
    )
  }
  const response = await request.put('/api/auth/profile', data)
  return normalizeUser(unwrap(response))
}
