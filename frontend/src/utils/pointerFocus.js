/**
 * 与 EnvParticleField 鼠标邻近聚焦共用的半径与衰减，
 * 保证卡片描边亮起范围和粒子亮起范围一致。
 */
export const POINTER_FOCUS_VIEWPORT_RATIO = 0.2

export function pointerFocusRadius(viewW = window.innerWidth, viewH = window.innerHeight) {
  return Math.min(viewW || 1, viewH || 1) * POINTER_FOCUS_VIEWPORT_RATIO
}

/** 高斯衰减：距焦点越近越接近 1（与粒子场 fall 公式一致） */
export function pointerFocusFalloff(dx, dy, focusR) {
  if (!focusR || focusR <= 0) return 0
  return Math.exp(-(dx * dx + dy * dy) / (focusR * focusR))
}

/** 点到矩形的最近点（指针在矩形内时距离为 0） */
export function nearestPointOnRect(x, y, rect) {
  return {
    x: Math.max(rect.left, Math.min(x, rect.right)),
    y: Math.max(rect.top, Math.min(y, rect.bottom))
  }
}
