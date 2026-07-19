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
 * - 空字符串：相对路径 /api/* → Vite proxy（VITE_API_PROXY，默认 8001）
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

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000
})

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
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }
    const silent = response.config.silent === true
    const res = response.data
    if (!res || typeof res.code === 'undefined') {
      return res
    }
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
    const msg = ERROR_MESSAGES[res.code] || res.message || res.msg || '请求失败'
    if (!silent) ElMessage.error(msg)
    if (res.code === 401 && !silent && !isOnLoginPage()) {
      window.location.href = '/login'
    }
    return Promise.reject(res)
  },
  (error) => {
    if (axios.isCancel?.(error) || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
      return Promise.reject(error)
    }
    const silent = error?.config?.silent === true
    const code = error?.response?.data?.code
    const msg =
      ERROR_MESSAGES[code] ||
      error?.response?.data?.message ||
      error?.response?.data?.msg ||
      error.message ||
      '网络异常，请稍后重试'
    if (!silent) ElMessage.error(msg)
    if ((code === 401 || error?.response?.status === 401) && !silent && !isOnLoginPage()) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
export { getEnvTag, getToken, ERROR_MESSAGES }
