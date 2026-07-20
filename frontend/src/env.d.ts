/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_PROXY?: string
  readonly VITE_API_PROXY_TARGET?: string
  readonly VITE_USE_MOCK?: string
  readonly VITE_MOCK_OPEN?: string
  readonly VITE_APP_ENV?: string
  readonly VITE_DEV_PORT?: string
  readonly VITE_CHAT_SESSION_API?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 静默：不弹全局错误/loading */
    silent?: boolean
    /** 是否显示全局 loading（默认 true） */
    showLoading?: boolean
    /** 失败重试次数 */
    retry?: number
    __retryCount?: number
    __retryMax?: number
  }
}
