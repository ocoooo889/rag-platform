import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')

  // 端口明细0720：Day1 代理 8001（FastAPI）；Day2 压测改 8080（Nginx 网关）
  // 禁止指向 8000（Chroma）。优先 VITE_API_PROXY，兼容 VITE_API_PROXY_TARGET
  const apiTarget =
    env.VITE_API_PROXY ||
    env.VITE_API_PROXY_TARGET ||
    'http://127.0.0.1:8001'

  // 端口明细0720：Vite 固定 127.0.0.1:5173；并行可用 VITE_DEV_PORT / --port 覆盖
  const devPort = Number(env.VITE_DEV_PORT) || 5173

  // [LUO-D02] Mock 由 VITE_USE_MOCK 控制（应用层 isMockOpen，非 vite-plugin-mock）
  // 仅当 === 'true' 时走 Mock；默认关闭避免联调假绿
  const useMock = env.VITE_USE_MOCK === 'true' || env.VITE_MOCK_OPEN === 'true'
  if (mode === 'development') {
    console.info(`[vite] API proxy → ${apiTarget}; Mock=${useMock}; port=${devPort}`)
  }

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    },
    server: {
      host: '127.0.0.1',
      port: devPort,
      // 占用时直接失败，避免静默改到非 5173 端口（与端口明细不一致）
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          // SSE：禁止代理缓冲，避免「先几个字 → 卡住 → 整段弹出」
          timeout: 0,
          proxyTimeout: 0,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes, req, res) => {
              const ct = String(proxyRes.headers['content-type'] || '')
              const isStream =
                ct.includes('text/event-stream') ||
                String(req.url || '').includes('/chat/stream')
              if (!isStream) return
              // 关闭可能的压缩缓冲
              if (proxyRes.headers['content-encoding']) {
                delete proxyRes.headers['content-encoding']
              }
              res.setHeader('Cache-Control', 'no-cache, no-transform')
              res.setHeader('X-Accel-Buffering', 'no')
              // 立刻写出响应头，后续 chunk 边到边推
              if (typeof res.flushHeaders === 'function') {
                res.flushHeaders()
              }
            })
          }
        },
        '/uploads': {
          target: apiTarget,
          changeOrigin: true
        }
      }
    }
  }
})
