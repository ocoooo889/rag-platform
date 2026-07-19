/**
 * 表格列均分并钉死：table-layout:fixed + colgroup 等宽百分比。
 * 用法：v-equal-table 挂在 el-table / .el-table 根上。
 */
function findTable(el) {
  if (!el) return null
  if (el.classList?.contains('el-table')) return el
  return el.querySelector?.('.el-table') || null
}

function equalize(el) {
  const table = findTable(el)
  if (!table) return
  table.style.tableLayout = 'fixed'
  table.style.width = '100%'
  table.querySelectorAll('colgroup').forEach((group) => {
    const cols = [...group.querySelectorAll('col')]
    if (!cols.length) return
    const w = `${(100 / cols.length).toFixed(4)}%`
    cols.forEach((col) => {
      col.removeAttribute('width')
      col.style.width = w
      col.style.minWidth = w
    })
  })
}

function schedule(el) {
  const run = () => equalize(el)
  requestAnimationFrame(() => {
    run()
    requestAnimationFrame(run)
  })
}

const stateMap = new WeakMap()

export default {
  mounted(el) {
    schedule(el)
    const table = findTable(el) || el
    const state = { mo: null, ro: null, onResize: null, timer: null }

    // EP doLayout 会改 col 宽度；短暂防抖后重新钉死，避免与自身 Mutation 死循环
    const onMutate = () => {
      if (state.timer) clearTimeout(state.timer)
      state.timer = setTimeout(() => schedule(el), 16)
    }

    if (typeof MutationObserver !== 'undefined') {
      state.mo = new MutationObserver(onMutate)
      state.mo.observe(table, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'width']
      })
    }
    if (typeof ResizeObserver !== 'undefined') {
      state.ro = new ResizeObserver(() => schedule(el))
      state.ro.observe(table)
    }
    state.onResize = () => schedule(el)
    window.addEventListener('resize', state.onResize)
    stateMap.set(el, state)
  },
  updated(el) {
    schedule(el)
  },
  unmounted(el) {
    const state = stateMap.get(el)
    if (!state) return
    if (state.timer) clearTimeout(state.timer)
    state.mo?.disconnect()
    state.ro?.disconnect()
    if (state.onResize) window.removeEventListener('resize', state.onResize)
    stateMap.delete(el)
  }
}
