import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')

  // [LUO-D01/R1] 代理默认 8001（FastAPI），勿指向 8000（Chroma）
  // 优先 VITE_API_PROXY（测试报告约定），兼容 VITE_API_PROXY_TARGET
  const apiTarget =
    env.VITE_API_PROXY ||
    env.VITE_API_PROXY_TARGET ||
    'http://127.0.0.1:8001'

  // [LUO-A03] 默认 5173；可用 --port 5174 或 VITE_DEV_PORT 覆盖（多前端并行）
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
      // 允许 CLI：npm run dev -- --port 5174
      strictPort: false,
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
