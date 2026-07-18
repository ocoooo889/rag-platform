/** 角色码 ↔ 展示名（库内英文码，UI 中文） */
const ROLE_MAP = {
  admin: '管理员',
  user: '普通用户'
}

export function roleCodeToLabel(code) {
  return ROLE_MAP[code] || code || '未知'
}

export function isAdminRole(code) {
  return code === 'admin'
}

/** 从 userInfo 解析角色 code（兼容仅有 role_name 的旧缓存） */
export function resolveRoleCode(user) {
  if (!user) return ''
  if (user.role === 'admin' || user.role === 'user') return user.role
  if (user.role_name === '管理员') return 'admin'
  if (user.role_name === '普通用户') return 'user'
  return user.role || ''
}
