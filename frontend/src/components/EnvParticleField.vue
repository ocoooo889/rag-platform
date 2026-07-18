<template>
  <!-- 全屏透视网格点阵 + 共享高度场起伏（登录 / 管理后台共用环境底；上下镜像） -->
  <div
    class="env-particle-field"
    :class="{ 'env-particle-field--fixed': fixed }"
    aria-hidden="true"
  >
    <canvas ref="canvasRef" class="env-particle-field__canvas"></canvas>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { POINTER_FOCUS_VIEWPORT_RATIO } from '@/utils/pointerFocus'

const props = defineProps({
  /** 为 true 时关闭鼠标邻近聚焦（如登录弹窗打开时） */
  pausePointerFocus: { type: Boolean, default: false },
  /** 管理后台全屏环境底用 fixed，登录页用 absolute 铺满页面容器 */
  fixed: { type: Boolean, default: false }
})

const canvasRef = ref(null)

/** 设为 false 即可立刻关掉鼠标聚焦，还原纯氛围版 */
const ENABLE_POINTER_FOCUS = true

let rafId = 0
let gridPoints = []
let softDot = null
let softDotTheme = null
let softDotThemeKey = ''
let viewW = 0
let viewH = 0
let gridCols = 0
let gridRows = 0
let pauseFocus = false

const pointer = {
  x: 0,
  y: 0,
  sx: 0,
  sy: 0,
  active: false,
  focus: 0
}

watch(
  () => props.pausePointerFocus,
  (v) => {
    pauseFocus = !!v
    if (pauseFocus) pointer.active = false
  },
  { immediate: true }
)

function onPointerMove(e) {
  if (!ENABLE_POINTER_FOCUS || pauseFocus) return
  pointer.x = e.clientX
  pointer.y = e.clientY
  pointer.active = true
}

function onPointerLeaveWindow() {
  pointer.active = false
}

function onDocumentMouseOut(e) {
  if (!e.relatedTarget) onPointerLeaveWindow()
}

function fade(t) {
  return t * t * (3 - 2 * t)
}

function hash2(ix, iy) {
  const n = Math.sin(ix * 127.1 + iy * 311.7) * 43758.5453123
  return n - Math.floor(n)
}

function valueNoise(x, y) {
  const x0 = Math.floor(x)
  const y0 = Math.floor(y)
  const fx = x - x0
  const fy = y - y0
  const ux = fade(fx)
  const uy = fade(fy)
  const a = hash2(x0, y0)
  const b = hash2(x0 + 1, y0)
  const c = hash2(x0, y0 + 1)
  const d = hash2(x0 + 1, y0 + 1)
  return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy
}

function fbm(x, y) {
  let v = 0
  let a = 0.5
  let f = 1
  for (let i = 0; i < 3; i++) {
    v += a * valueNoise(x * f, y * f)
    f *= 2.02
    a *= 0.5
  }
  return v
}

/** 共享高度场：整张点布共用同一函数，粒子不单独乱抖 */
function heightField(wx, wz, t) {
  const morph = t * 0.045
  const drift = t * 0.055
  const n = fbm(wx * 0.85 + drift, wz * 0.75 + morph)
  const w1 = Math.sin(wx * 2.15 + wz * 1.05 + t * 0.28)
  const w2 = Math.sin(wx * 1.05 - wz * 1.65 + t * 0.18)
  const w3 = Math.sin(wx * 3.4 + wz * 0.4 + t * 0.12 + n * 1.2)
  return (n - 0.5) * 0.52 + w1 * 0.26 + w2 * 0.16 + w3 * 0.1
}

function readThemePrimary() {
  if (typeof window === 'undefined') return '#3D9BFF'
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue('--el-color-primary')
    .trim()
  return raw || '#3D9BFF'
}

function hexToRgb(color) {
  const raw = String(color || '').trim()
  const hexMatch = raw.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i)
  if (hexMatch) {
    let h = hexMatch[1]
    if (h.length === 3) h = h.split('').map((c) => c + c).join('')
    return {
      r: parseInt(h.slice(0, 2), 16),
      g: parseInt(h.slice(2, 4), 16),
      b: parseInt(h.slice(4, 6), 16)
    }
  }
  const rgbMatch = raw.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i)
  if (rgbMatch) {
    return {
      r: Math.round(Number(rgbMatch[1])),
      g: Math.round(Number(rgbMatch[2])),
      b: Math.round(Number(rgbMatch[3]))
    }
  }
  return { r: 61, g: 155, b: 255 }
}

function ensureSoftDot() {
  if (softDot) return softDot
  const c = document.createElement('canvas')
  c.width = 20
  c.height = 20
  const g = c.getContext('2d')
  const grd = g.createRadialGradient(10, 10, 0, 10, 10, 9)
  grd.addColorStop(0, 'rgba(255, 255, 255, 1)')
  grd.addColorStop(0.35, 'rgba(230, 230, 235, 0.9)')
  grd.addColorStop(0.7, 'rgba(190, 190, 195, 0.35)')
  grd.addColorStop(1, 'rgba(160, 160, 165, 0)')
  g.fillStyle = grd
  g.beginPath()
  g.arc(10, 10, 9, 0, Math.PI * 2)
  g.fill()
  softDot = c
  return softDot
}

/** 鼠标照亮光斑：跟随 --el-color-primary（品牌主题色） */
function ensureSoftDotTheme() {
  const key = readThemePrimary()
  if (softDotTheme && softDotThemeKey === key) return softDotTheme
  softDotThemeKey = key
  const { r, g, b } = hexToRgb(key)
  const c = document.createElement('canvas')
  c.width = 28
  c.height = 28
  const gctx = c.getContext('2d')
  const grd = gctx.createRadialGradient(14, 14, 0, 14, 14, 13)
  grd.addColorStop(0, `rgba(${Math.min(255, r + 80)}, ${Math.min(255, g + 70)}, ${Math.min(255, b + 60)}, 1)`)
  grd.addColorStop(0.25, `rgba(${r}, ${g}, ${b}, 0.88)`)
  grd.addColorStop(0.55, `rgba(${r}, ${g}, ${b}, 0.38)`)
  grd.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
  gctx.fillStyle = grd
  gctx.beginPath()
  gctx.arc(14, 14, 13, 0, Math.PI * 2)
  gctx.fill()
  softDotTheme = c
  return softDotTheme
}

function initParticleGrid(width, height) {
  gridCols = Math.max(110, Math.min(160, Math.round(width / 12)))
  gridRows = Math.max(70, Math.min(100, Math.round(height / 11)))
  gridPoints = []

  for (let j = 0; j < gridRows; j++) {
    const v = (j / (gridRows - 1)) * 1.12 - 0.02
    for (let i = 0; i < gridCols; i++) {
      const u = (i / (gridCols - 1)) * 1.36 - 0.18
      gridPoints.push({ u, v, i, j })
    }
  }
}

function resizeParticleCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  viewW = window.innerWidth
  viewH = window.innerHeight
  canvas.width = Math.floor(viewW * dpr)
  canvas.height = Math.floor(viewH * dpr)
  canvas.style.width = `${viewW}px`
  canvas.style.height = `${viewH}px`
  const ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  softDot = null
  softDotTheme = null
  softDotThemeKey = ''
  ensureSoftDot()
  ensureSoftDotTheme()
  initParticleGrid(viewW, viewH)
}

function drawParticles(ts) {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const width = viewW || window.innerWidth
  const height = viewH || window.innerHeight
  const t = (ts || 0) * 0.001
  const sprite = ensureSoftDot()
  const spriteTheme = ensureSoftDotTheme()

  const fieldDrift = t * 0.09
  const slowMorph = t * 0.035

  if (ENABLE_POINTER_FOCUS) {
    if (!pointer.sx && !pointer.sy) {
      pointer.sx = pointer.x || width * 0.5
      pointer.sy = pointer.y || height * 0.5
    }
    pointer.sx += (pointer.x - pointer.sx) * 0.14
    pointer.sy += (pointer.y - pointer.sy) * 0.14
    const targetFocus = pointer.active && !pauseFocus ? 1 : 0
    pointer.focus += (targetFocus - pointer.focus) * 0.08
  } else {
    pointer.focus = 0
  }

  const focusR = Math.min(width, height) * POINTER_FOCUS_VIEWPORT_RATIO
  const focusR2 = focusR * focusR
  const hasFocus = ENABLE_POINTER_FOCUS && pointer.focus > 0.01

  ctx.clearRect(0, 0, width, height)

  for (let n = 0; n < gridPoints.length; n++) {
    const p = gridPoints[n]
    const wx = p.u * 6.2 + fieldDrift
    const wz = p.v * 4.4
    const elev = heightField(wx, wz + slowMorph * 0.25, t)

    const depth = 0.92 + Math.max(0, Math.min(1, p.v)) * 0.85
    const persp = 1 / depth
    const xSpan = width * (1.42 + (1 - Math.min(1, Math.max(0, p.v))) * 0.55)
    const x = width * 0.5 + (p.u - 0.5) * xSpan * (0.5 + 0.5 * persp)

    const vClamped = Math.max(0, Math.min(1.15, p.v))
    const yBase = height * (-0.06 + vClamped * 1.08)
    const amp = height * (0.035 + Math.min(1, Math.max(0, p.v)) * 0.055)
    const elevScale = 0.45 + Math.min(1, Math.max(0, p.v)) * 0.45
    let y = yBase - elev * amp * elevScale * (0.8 + persp * 0.35)

    // 上下镜像：透视网格与高度场整体翻转
    y = height - y

    if (x < -40 || x > width + 40 || y < -40 || y > height + 40) continue

    const nx = x / width - 0.5
    const ny = y / height - 0.4
    const clearR = (nx * nx) / 0.28 + (ny * ny) / 0.07
    const clearFade = 0.62 + 0.38 * Math.min(1, clearR)

    const crest = 0.75 + Math.max(0, elev) * 0.85
    const farFade = 0.55 + Math.min(1, Math.max(0, p.v)) * 0.45
    let a = 0.55 * farFade * clearFade * crest
    let s = (1.05 + Math.min(1, Math.max(0, p.v)) * 1.85) * (0.9 + Math.max(0, elev) * 0.4)
    let fall = 0

    if (hasFocus) {
      const dx = x - pointer.sx
      const dy = y - pointer.sy
      fall = Math.exp(-(dx * dx + dy * dy) / focusR2) * pointer.focus
      if (fall > 0.02) {
        a *= 1 + fall * 1.15
        s *= 1 + fall * 0.5
        // 镜像后「抬升」改为向下微调，保持起伏方向观感一致
        y += fall * Math.max(0, elev) * amp * 0.18
      }
    }

    if (a < 0.08) continue

    if (fall > 0.04) {
      const mix = Math.min(1, fall * 1.35)
      ctx.globalAlpha = Math.min(0.75, a * (1 - mix * 0.55))
      ctx.drawImage(sprite, x - s, y - s, s * 2, s * 2)
      ctx.globalAlpha = Math.min(0.88, a * mix * 0.95)
      const sb = s * (1 + mix * 0.2)
      ctx.drawImage(spriteTheme, x - sb, y - sb, sb * 2, sb * 2)
    } else {
      ctx.globalAlpha = Math.min(0.92, a)
      ctx.drawImage(sprite, x - s, y - s, s * 2, s * 2)
    }
  }

  ctx.globalAlpha = 1
  rafId = window.requestAnimationFrame(drawParticles)
}

function startParticleEngine() {
  resizeParticleCanvas()
  if (rafId) window.cancelAnimationFrame(rafId)
  rafId = window.requestAnimationFrame(drawParticles)
}

function stopParticleEngine() {
  if (rafId) window.cancelAnimationFrame(rafId)
  rafId = 0
}

onMounted(() => {
  window.addEventListener('resize', resizeParticleCanvas)
  window.addEventListener('mousemove', onPointerMove, { passive: true })
  window.addEventListener('mouseleave', onPointerLeaveWindow)
  document.addEventListener('mouseout', onDocumentMouseOut)
  startParticleEngine()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeParticleCanvas)
  window.removeEventListener('mousemove', onPointerMove)
  window.removeEventListener('mouseleave', onPointerLeaveWindow)
  document.removeEventListener('mouseout', onDocumentMouseOut)
  stopParticleEngine()
})
</script>

<style scoped>
.env-particle-field {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: transparent;
}

.env-particle-field--fixed {
  position: fixed;
  z-index: 0;
}

.env-particle-field__canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
