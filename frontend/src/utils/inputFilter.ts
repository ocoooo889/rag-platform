/**
 * 提示词防注入 - 前端前置拦截工具（全局唯一入口）
 *
 * 安全分层：
 * - 请求参数必须使用 DualTextInput.raw（原始输入）
 * - 页面渲染使用 DualTextInput.display（转义后）
 * - 前端仅第一层防护，不能替代后端二次校验
 */
import type { DualTextInput } from '@/types'

/** 全局统一输入长度阈值（字符） */
export const INPUT_MAX_LENGTH = 1000

/** 命中测试等短输入阈值 */
export const INPUT_MAX_LENGTH_SHORT = 500

const DANGEROUS_PATTERNS: RegExp[] = [
  /<\s*script\b/i,
  /<\/\s*script\s*>/i,
  /javascript\s*:/i,
  /on\w+\s*=/i,
  /<\s*iframe\b/i,
  /<\s*object\b/i,
  /<\s*embed\b/i,
  /data\s*:\s*text\/html/i,
  /expression\s*\(/i,
  /vbscript\s*:/i
]

/**
 * HTML 特殊字符转义（仅用于展示，不可回写为请求参数）
 */
export function escapeHtml(input: string): string {
  return String(input || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 检测是否包含危险脚本/注入特征（不修改原文）
 */
export function hasDangerousScript(input: string): boolean {
  const text = String(input || '')
  return DANGEROUS_PATTERNS.some((re) => re.test(text))
}

/**
 * 统一处理用户输入，产出「原始 / 展示」双份数据
 * @param input 用户原始输入
 * @param maxLength 长度阈值，默认 INPUT_MAX_LENGTH
 */
export function processUserInput(
  input: string,
  maxLength: number = INPUT_MAX_LENGTH
): DualTextInput {
  const raw = String(input ?? '')
  const blocked = hasDangerousScript(raw)
  const overLimit = raw.length > maxLength
  let tip = ''
  if (blocked) {
    tip = '输入内容包含不安全脚本特征，请修改后再试'
  } else if (overLimit) {
    tip = `输入内容超出长度限制（最多 ${maxLength} 字）`
  }

  return {
    raw,
    display: escapeHtml(raw),
    blocked,
    overLimit,
    tip
  }
}

/**
 * 发送前置校验：通过返回 true；失败写出 tip
 */
export function canSubmitInput(
  input: string,
  maxLength: number = INPUT_MAX_LENGTH
): { ok: boolean; tip: string; dual: DualTextInput } {
  const dual = processUserInput(input, maxLength)
  if (dual.blocked || dual.overLimit) {
    return { ok: false, tip: dual.tip, dual }
  }
  if (!dual.raw.trim()) {
    return { ok: false, tip: '请输入内容', dual }
  }
  return { ok: true, tip: '', dual }
}
