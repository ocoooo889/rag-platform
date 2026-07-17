/**
 * 全局 Axios 封装
 * - baseURL 统一读取 VITE_API_BASE_URL（.env.development / .env.production）
 * - 自动携带 JWT Token、env 环境标识
 * - 统一错误码提示：0/400/401/403/404/500/5001/5002 + 扩展码 4001–4003
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

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
  4003: '系统品牌配置未初始化，使用默认值'
}

/** 去掉末尾斜杠，避免与 /api/... 拼接出现双斜杠 */
function normalizeBaseUrl(url = '') {
  return String(url || '').trim().replace(/\/$/, '')
}

/**
 * 全局 API 基础地址
 * - 开发：.env.development → 如 http://127.0.0.1:8001
 * - 生产：.env.production → 同域可留空
 */
export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL || '')

function getEnvTag() {
  return localStorage.getItem('rag_env') || import.meta.env.VITE_APP_ENV || 'dev'
}

function getToken() {
  return localStorage.getItem('rag_token') || localStorage.getItem('token') || ''
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
    } else if (config.data && typeof config.data === 'object') {
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
    if (res.code === 4001 || res.code === 4002) {
      if (!silent) {
        ElMessage.warning(res.message || res.msg || ERROR_MESSAGES[res.code])
      }
      return Promise.reject(res)
    }
    const msg = ERROR_MESSAGES[res.code] || res.message || res.msg || '请求失败'
    if (!silent) ElMessage.error(msg)
    if (res.code === 401) {
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
    if (code === 401 || error?.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
export { getEnvTag, getToken, ERROR_MESSAGES }
