/**
 * 用户 Pinia Store
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchMeApi, loginApi } from '@/api/auth'
import { useChatStore } from '@/stores/chat'
import { roleCodeToLabel, resolveRoleCode } from '@/utils/role'

const TOKEN_KEY = 'rag_token'
const USER_KEY = 'rag_user'
const LEGACY_TOKEN_KEY = 'token'
const LEGACY_USER_KEY = 'userInfo'

function readCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY) || localStorage.getItem(LEGACY_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

function normalizeUser(nextUser) {
  if (!nextUser) return null
  const role = resolveRoleCode(nextUser)
  return {
    ...nextUser,
    role,
    role_name: nextUser.role_name || roleCodeToLabel(role)
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY) || '')
  const userInfo = ref(normalizeUser(readCachedUser()))

  const isLoggedIn = computed(() => !!token.value)
  const roleCode = computed(() => resolveRoleCode(userInfo.value))

  function setSession(nextToken, nextUser = null) {
    token.value = nextToken || ''
    userInfo.value = normalizeUser(nextUser)

    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken)
      localStorage.setItem(LEGACY_TOKEN_KEY, nextToken)
    } else {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(LEGACY_TOKEN_KEY)
    }

    if (userInfo.value) {
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo.value))
      localStorage.setItem(LEGACY_USER_KEY, JSON.stringify(userInfo.value))
    } else {
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(LEGACY_USER_KEY)
    }
  }

  function setToken(nextToken) {
    setSession(nextToken, userInfo.value)
  }

  function setUserInfo(nextUser) {
    setSession(token.value, nextUser)
  }

  function clearAccountScopedState() {
    const chatStore = useChatStore()
    chatStore.resetState()
  }

  async function ensureUserInfo() {
    if (!token.value) return null
    try {
      const me = await fetchMeApi()
      if (me) setUserInfo(me)
      return userInfo.value
    } catch (e) {
      const status = e?.response?.status || e?.code
      // 会话失效时清本地态，避免路由因残留 token 把登录页踢回后台
      if (status === 401) {
        setSession('', null)
      } else {
        console.error('fetch /api/auth/me failed', e)
      }
      return userInfo.value
    }
  }

  async function login(credentials) {
    const prevUid = userInfo.value?.id ?? userInfo.value?.user_id ?? null
    clearAccountScopedState()
    // 必须走 loginApi：后端 /api/auth/login 要 OAuth2 表单，不能直接 POST JSON（会 422）
    const data = await loginApi(credentials)
    setSession(data.token, data.user)
    const nextUid = userInfo.value?.id ?? userInfo.value?.user_id ?? null
    // 切换账号时清理上一用户分区缓存（等待完成，避免首屏串读）
    try {
      const m = await import('@/utils/cacheLifecycle')
      await m.onUserSwitch(
        prevUid != null ? String(prevUid) : null,
        nextUid != null ? String(nextUid) : null
      )
    } catch {
      /* ignore */
    }
    return data
  }

  function logout() {
    const uid = userInfo.value?.id || userInfo.value?.user_id || null
    clearAccountScopedState()
    // 退出登录清理对应用户分区缓存（异步，不阻塞跳转）
    import('@/utils/cacheLifecycle')
      .then((m) => m.onLogoutClear(uid != null ? String(uid) : null))
      .catch(() => {})
    setSession('', null)
    localStorage.removeItem('currentRole')
    window.location.href = '/login'
  }

  return {
    token,
    userInfo,
    roleCode,
    isLoggedIn,
    setSession,
    setToken,
    setUserInfo,
    ensureUserInfo,
    login,
    logout,
    clearAccountScopedState
  }
})
