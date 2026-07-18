import { onMounted, onUnmounted } from 'vue'
import {
  nearestPointOnRect,
  pointerFocusFalloff,
  pointerFocusRadius
} from '@/utils/pointerFocus'

/**
 * 带边框面板：鼠标邻近时描边局部亮起。
 * 与 admin.css / Login 光斑层保持同步。
 */
export const GLASS_GLOW_SELECTOR = [
  'html.admin-theme .aside',
  'html.admin-theme .el-card',
  'html.admin-theme .kb-card',
  'html.admin-theme .panel',
  'html.admin-theme .filter-bar',
  'html.admin-theme .upload-area',
  'html.admin-theme .config-form',
  'html.admin-theme .config-preview',
  'html.admin-theme .modal-preview',
  'html.admin-theme .modal-preview__card',
  'html.admin-theme .composer-box',
  'html.admin-theme .chat-dialog',
  'html.admin-theme .suggest-chip',
  'html.admin-theme .chat-bubble__content',
  'html.admin-theme .stat-card',
  'html.admin-theme .chart-card',
  'html.admin-theme .status-item',
  'html.admin-theme .retrieve-card',
  'html.admin-theme .result-area',
  'html.admin-theme .crop-stage',
  'html.admin-theme .el-table',
  'html.admin-theme .app-table',
  'html.admin-theme .el-dialog',
  'html.admin-theme .el-message-box',
  'html.admin-theme .el-input__wrapper',
  'html.admin-theme .el-textarea__inner',
  'html.admin-theme .el-select__wrapper',
  'html.admin-theme .user-avatar',
  'html.admin-theme .chat-bubble__role',
  /* 登录页浮窗（无 admin-theme） */
  '.login-modal-card'
].join(',')

const GLOW_VARS = ['--glass-glow', '--glow-x', '--glow-y', '--glow-r']

export function useGlassPointerGlow() {
  let rafId = 0
  let px = 0
  let py = 0
  let sx = 0
  let sy = 0
  let active = false
  let focus = 0

  function onPointerMove(e) {
    px = e.clientX
    py = e.clientY
    active = true
  }

  function onPointerLeave() {
    active = false
  }

  function onDocumentMouseOut(e) {
    if (!e.relatedTarget) onPointerLeave()
  }

  function clearGlow(el) {
    el.style.setProperty('--glass-glow', '0')
  }

  function tick() {
    rafId = window.requestAnimationFrame(tick)

    if (!sx && !sy) {
      sx = px || window.innerWidth * 0.5
      sy = py || window.innerHeight * 0.5
    }
    sx += (px - sx) * 0.14
    sy += (py - sy) * 0.14
    focus += ((active ? 1 : 0) - focus) * 0.08

    const nodes = document.querySelectorAll(GLASS_GLOW_SELECTOR)
    if (!nodes.length || focus < 0.01) {
      nodes.forEach(clearGlow)
      return
    }

    const focusR = pointerFocusRadius(window.innerWidth, window.innerHeight)
    for (let i = 0; i < nodes.length; i++) {
      const el = nodes[i]
      const rect = el.getBoundingClientRect()
      if (rect.width < 2 || rect.height < 2) {
        clearGlow(el)
        continue
      }
      // 跳过不可见 / 折叠节点
      if (rect.bottom < -40 || rect.top > window.innerHeight + 40) {
        clearGlow(el)
        continue
      }
      const near = nearestPointOnRect(sx, sy, rect)
      const fall = pointerFocusFalloff(sx - near.x, sy - near.y, focusR) * focus
      if (fall <= 0.02) {
        clearGlow(el)
        continue
      }
      el.style.setProperty('--glow-x', `${(sx - rect.left).toFixed(1)}px`)
      el.style.setProperty('--glow-y', `${(sy - rect.top).toFixed(1)}px`)
      el.style.setProperty('--glow-r', `${focusR.toFixed(1)}px`)
      el.style.setProperty('--glass-glow', fall.toFixed(3))
    }
  }

  onMounted(() => {
    window.addEventListener('mousemove', onPointerMove, { passive: true })
    window.addEventListener('mouseleave', onPointerLeave)
    document.addEventListener('mouseout', onDocumentMouseOut)
    rafId = window.requestAnimationFrame(tick)
  })

  onUnmounted(() => {
    window.removeEventListener('mousemove', onPointerMove)
    window.removeEventListener('mouseleave', onPointerLeave)
    document.removeEventListener('mouseout', onDocumentMouseOut)
    if (rafId) window.cancelAnimationFrame(rafId)
    rafId = 0
    document.querySelectorAll(GLASS_GLOW_SELECTOR).forEach((el) => {
      GLOW_VARS.forEach((v) => el.style.removeProperty(v))
    })
  })
}
