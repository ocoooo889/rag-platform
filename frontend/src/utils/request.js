/**
 * 全局 Axios 封装（全项目共用）
 * - baseURL：VITE_API_BASE_URL（开发建议留空，走 Vite /api 代理）
 * - 预留 Mock 判断：MOCK_OPEN / isMockOpen（业务双分支在 api/* 内，不在拦截器里假造数据）
 * - 自动携带 JWT、env；统一错误码提示
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { MOCK_OPEN, isMockOpen } from '@/mock/flag'

const ERROR_MESSAGES = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '无操作权限',
  404: '资源不存在',
  500: '服务异常，请稍后重试',
  5001: '向量库服务异常，请稍后重试或联系管理员',
  5002: '大模型服务异常，请稍后重试',
  4001: '您尚未被分配到任何用户组，请联系管理员',
  4002: '文档正在处理中，请等待处理完成后再试',
  4003: '系统品牌配置未初始化，使用默认值',
  4004: '该文档仅支持关键词/混合检索，请切换模式或重新向量化'
}

/** 去掉末尾斜杠，避免与 /api/... 拼接出现双斜杠 */
function normalizeBaseUrl(url = '') {
  return String(url || '').trim().replace(/\/$/, '')
}

/**
 * 全局 API 基础地址
 * - 空字符串：相对路径 /api/* → Vite proxy（VITE_API_PROXY：Day1=8001，Day2 压测=8080）
 * - 绝对地址：直连后端（需 CORS）
 */
export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL || '')

/** 预留：业务层 if (MOCK_OPEN()) 双分支判断 */
export { MOCK_OPEN, isMockOpen }

function getEnvTag() {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('rag_env') || import.meta.env.VITE_APP_ENV || 'dev'
    }
  } catch (e) {
    // Node 冒烟环境无 localStorage
  }
  return import.meta.env.VITE_APP_ENV || 'dev'
}

function getToken() {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('rag_token') || localStorage.getItem('token') || ''
    }
  } catch (e) {
    // ignore
  }
  return ''
}

function isOnLoginPage() {
  try {
    return typeof window !== 'undefined' && window.location?.pathname === '/login'
  } catch (e) {
    return false
  }
}

/** 防止 401 风暴：清 token 前若不清，路由会因仍有 token 把 /login 踢回后台形成死循环 */
let redirecting401 = false

function clearAuthStorage() {
  try {
    ;['rag_token', 'token', 'rag_user', 'userInfo', 'currentRole'].forEach((k) => {
      localStorage.removeItem(k)
    })
  } catch (e) {
    /* ignore */
  }
}

function handleUnauthorized() {
  if (isOnLoginPage() || redirecting401) return
  redirecting401 = true
  clearAuthStorage()
  window.location.href = '/login'
}

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000
})

/** 全局加载计数（页面可订阅；默认不强制全屏遮罩） */
let loadingCount = 0
const loadingListeners = new Set()

function emitLoading() {
  loadingListeners.forEach((fn) => {
    try {
      fn(loadingCount > 0, loadingCount)
    } catch (e) {
      /* ignore */
    }
  })
}

export function onRequestLoading(listener) {
  loadingListeners.add(listener)
  return () => loadingListeners.delete(listener)
}

export function getRequestLoading() {
  return loadingCount > 0
}

const DEFAULT_RETRY = 1

request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    const env = getEnvTag()
    if (config.method === 'get') {
      config.params = { ...(config.params || {}), env }
    } else if (config.data instanceof FormData) {
      config.params = { ...(config.params || {}), env }
    } else if (config.data && typeof config.data === 'object' && !(config.data instanceof URLSearchParams)) {
      config.data = { ...config.data, env }
    } else {
      config.params = { ...(config.params || {}), env }
    }
    if (config.showLoading !== false && !config.silent && !(config.__retryCount > 0)) {
      loadingCount += 1
      emitLoading()
    }
    if (config.__retryCount == null) config.__retryCount = 0
    if (config.__retryMax == null) {
      config.__retryMax = config.retry != null ? Number(config.retry) : DEFAULT_RETRY
    }
    return config
  },
  (error) => Promise.reject(error)
)

function endLoading(config) {
  if (!config) return
  if (config.showLoading !== false && !config.silent) {
    loadingCount = Math.max(0, loadingCount - 1)
    emitLoading()
  }
}

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      endLoading(response.config)
      return response.data
    }
    const silent = response.config.silent === true
    const res = response.data
    if (!res || typeof res.code === 'undefined') {
      endLoading(response.config)
      return res
    }
    endLoading(response.config)
    if (res.code === 0) {
      return res
    }
    if (res.code === 4003) {
      if (!silent) ElMessage.warning(ERROR_MESSAGES[4003])
      return res
    }
    if (res.code === 4001 || res.code === 4002 || res.code === 4004) {
      if (!silent) {
        ElMessage.warning(res.message || res.msg || ERROR_MESSAGES[res.code])
      }
      return Promise.reject(res)
    }
    if (res.code === 401) {
      if (!silent) ElMessage.error(ERROR_MESSAGES[401])
      handleUnauthorized()
      return Promise.reject(res)
    }
    const msg = ERROR_MESSAGES[res.code] || res.message || res.msg || '请求失败'
    if (!silent) ElMessage.error(msg)
    return Promise.reject(res)
  },
  async (error) => {
    const cfg = error?.config
    if (axios.isCancel?.(error) || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
      endLoading(cfg)
      return Promise.reject(error)
    }

    const status = error?.response?.status
    const bodyCode = error?.response?.data?.code
    const isUnauthorized = status === 401 || bodyCode === 401

    const canRetry =
      cfg &&
      !isUnauthorized &&
      (cfg.__retryCount || 0) < (cfg.__retryMax || 0) &&
      (!status || status >= 500 || error?.code === 'ECONNABORTED' || error?.message === 'Network Error')
    if (canRetry) {
      cfg.__retryCount = (cfg.__retryCount || 0) + 1
      await new Promise((r) => setTimeout(r, 400 * cfg.__retryCount))
      return request(cfg)
    }

    endLoading(cfg)
    const silent = cfg?.silent === true

    if (isUnauthorized) {
      if (!silent) ElMessage.error(ERROR_MESSAGES[401])
      handleUnauthorized()
      return Promise.reject(error)
    }

    let msg =
      ERROR_MESSAGES[bodyCode] ||
      error?.response?.data?.message ||
      error?.response?.data?.msg ||
      null
    if (!msg) {
      if (error?.code === 'ECONNABORTED') msg = '请求超时，请稍后重试'
      else if (error?.message === 'Network Error') msg = '网络异常，请检查网络后重试'
      else msg = error.message || '网络异常，请稍后重试'
    }
    if (!silent) ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
export { getEnvTag, getToken, clearAuthStorage, ERROR_MESSAGES }
