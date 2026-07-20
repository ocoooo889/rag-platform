/**
 * 助手回答轻量 Markdown 渲染（无第三方依赖）
 * 支持：段落、换行、引用块、无序/有序列表、加粗、行内代码、标题
 * 先转义 HTML，再套安全标签，避免 XSS
 */

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** 去掉模型常误抄的噪声，避免和「查看溯源」重复 */
export function cleanAssistantAnswer(raw) {
  let text = String(raw || '')
  // 去掉 <doc ...> / </doc>
  text = text.replace(/<\/?doc\b[^>]*>/gi, '')
  // 正文末尾「出处 / 来源：xxx.md」与折叠溯源重复，去掉
  text = text.replace(
    /\n{0,2}(?:#{1,3}\s*)?(?:出处|来源)\s*[:：][\s\S]*$/i,
    ''
  )
  // 压缩过多空行
  text = text.replace(/\n{3,}/g, '\n\n').trim()
  return text
}

function inlineFormat(escapedLine) {
  // 行内代码（已转义，内容不再解析）
  let s = escapedLine.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  // 加粗 **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  return s
}

/**
 * 将助手纯文本转为安全 HTML
 */
export function renderAssistantMarkdown(raw) {
  const cleaned = cleanAssistantAnswer(raw)
  if (!cleaned) return ''

  const lines = cleaned.split(/\r?\n/)
  const html = []
  let i = 0
  let inQuote = false
  let inUl = false
  let inOl = false

  const closeLists = () => {
    if (inUl) {
      html.push('</ul>')
      inUl = false
    }
    if (inOl) {
      html.push('</ol>')
      inOl = false
    }
  }
  const closeQuote = () => {
    if (inQuote) {
      html.push('</blockquote>')
      inQuote = false
    }
  }

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // 空行：结束当前块
    if (!trimmed) {
      closeQuote()
      closeLists()
      i += 1
      continue
    }

    // 标题
    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed)
    if (heading) {
      closeQuote()
      closeLists()
      const level = heading[1].length
      html.push(
        `<h${level} class="md-h md-h${level}">${inlineFormat(escapeHtml(heading[2]))}</h${level}>`
      )
      i += 1
      continue
    }

    // 引用块
    if (/^>\s?/.test(trimmed)) {
      closeLists()
      if (!inQuote) {
        html.push('<blockquote class="md-quote">')
        inQuote = true
      }
      const body = trimmed.replace(/^>\s?/, '')
      html.push(`<p class="md-quote__p">${inlineFormat(escapeHtml(body))}</p>`)
      i += 1
      continue
    }

    // 无序列表
    if (/^[-*•]\s+/.test(trimmed)) {
      closeQuote()
      if (inOl) {
        html.push('</ol>')
        inOl = false
      }
      if (!inUl) {
        html.push('<ul class="md-ul">')
        inUl = true
      }
      const body = trimmed.replace(/^[-*•]\s+/, '')
      html.push(`<li>${inlineFormat(escapeHtml(body))}</li>`)
      i += 1
      continue
    }

    // 有序列表
    if (/^\d+[.)]\s+/.test(trimmed)) {
      closeQuote()
      if (inUl) {
        html.push('</ul>')
        inUl = false
      }
      if (!inOl) {
        html.push('<ol class="md-ol">')
        inOl = true
      }
      const body = trimmed.replace(/^\d+[.)]\s+/, '')
      html.push(`<li>${inlineFormat(escapeHtml(body))}</li>`)
      i += 1
      continue
    }

    // 普通段落（合并连续非空、非特殊行）
    closeQuote()
    closeLists()
    const para = [trimmed]
    i += 1
    while (i < lines.length) {
      const next = lines[i].trim()
      if (!next) break
      if (/^>\s?/.test(next)) break
      if (/^[-*•]\s+/.test(next)) break
      if (/^\d+[.)]\s+/.test(next)) break
      if (/^#{1,3}\s+/.test(next)) break
      para.push(next)
      i += 1
    }
    html.push(
      `<p class="md-p">${inlineFormat(escapeHtml(para.join(' ')))}</p>`
    )
  }

  closeQuote()
  closeLists()
  return html.join('')
}
