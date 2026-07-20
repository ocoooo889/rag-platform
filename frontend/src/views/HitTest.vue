<template>
  <div class="hit-test page-shell">
    <div class="page-header">
      <h2>命中率测试</h2>
      <el-button
        type="primary"
        :disabled="!canExport"
        :title="canExport ? '导出检索结果' : '暂无命中结果可导出'"
        @click="onExport"
      >
        导出 CSV
      </el-button>
    </div>

    <div class="page-body">
    <EmptyState v-if="pageError" type="error" :tip="pageError">
      <el-button type="primary" @click="loadBase">重新加载</el-button>
    </EmptyState>

    <EmptyState v-else-if="!hasKb && !bootLoading" type="kb" tip="暂无知识库，无法进行命中测试" />

    <div v-else v-loading="bootLoading" element-loading-text="加载中..." class="hit-test__body">
      <!-- 筛选区 -->
      <section class="panel filter-panel">
        <el-form label-width="88px" class="filter-form" @submit.prevent>
          <el-form-item label="知识库">
            <el-select
              v-model="hitStore.kbId"
              placeholder="请选择知识库"
              filterable
              style="width: 280px"
              @change="onKbChange"
            >
              <el-option
                v-for="kb in kbStore.list"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="文档">
            <el-select
              v-model="hitStore.docIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择已完成文档（非 completed 不可选）"
              style="width: 460px"
              :disabled="!hitStore.kbId || docsLoading"
              :loading="docsLoading"
            >
              <el-option
                v-for="doc in docOptions"
                :key="doc.id"
                :label="formatDocLabel(doc)"
                :value="doc.id"
                :disabled="!isDocSelectable(doc.status)"
              >
                <div class="doc-option">
                  <span class="doc-option__name">{{ doc.filename || doc.file_name || doc.id }}</span>
                  <el-tag size="small" :type="getDocStatusTagType(doc.status)" effect="plain">
                    {{ getDocStatusLabel(doc.status) }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="测试问题">
            <el-input
              v-model="hitStore.query"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="请输入测试问题"
              style="max-width: 640px"
              :disabled="hitStore.loading"
            />
            <p v-if="querySafetyTip" class="input-safety-tip">{{ querySafetyTip }}</p>
          </el-form-item>

          <el-form-item label="TopN">
            <div class="topn-field">
              <el-slider
                v-model="hitStore.topN"
                :min="3"
                :max="10"
                :step="1"
                show-stops
                show-tooltip
                :disabled="hitStore.loading"
              />
              <span class="topn-value">{{ hitStore.topN }}</span>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="hitStore.loading"
              :disabled="!canRun"
              :title="runDisabledTip"
              @click="onRunTest"
            >
              {{ hitStore.loading ? '加载中...' : '运行测试' }}
            </el-button>
          </el-form-item>
        </el-form>
      </section>

      <!-- 三模式 Tab -->
      <section class="panel mode-panel">
        <el-tabs
          :model-value="hitStore.searchType"
          class="mode-tabs"
          @tab-change="onModeChange"
        >
          <el-tab-pane
            v-for="tab in MODE_TABS"
            :key="tab.name"
            :label="tab.label"
            :name="tab.name"
            :disabled="hitStore.loading || (tab.name === 'vector' && !vectorModeAllowed)"
          >
            <div class="mode-tip">
              {{
                tab.name === 'vector' && !vectorModeAllowed
                  ? '所选文档含「仅关键词」状态，请改用关键词/混合检索，或先重新向量化。'
                  : tab.tip
              }}
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 结果区：加载 / 报错 / 空 / 列表 -->
        <div class="result-area" v-loading="hitStore.loading" element-loading-text="检索中...">
          <EmptyState
            v-if="hitStore.errorMsg && !hitStore.loading"
            type="error"
            :tip="hitStore.errorMsg"
          >
            <el-button type="primary" :disabled="!canRun" @click="onRunTest">重试</el-button>
          </EmptyState>

          <EmptyState
            v-else-if="hitStore.hasSearched && !hitStore.results.length && !hitStore.loading"
            type="retrieve"
          />

          <div v-else-if="!hitStore.hasSearched && !hitStore.loading" class="result-placeholder">
            选择文档并输入问题后，点击「运行测试」查看命中结果
          </div>

          <RetrieveResultCard
            v-for="item in hitStore.results"
            :key="`${item.chunk_id}-${item.rank}`"
            :rank="item.rank"
            :score="item.score"
            :content="item.content"
            :source-doc="item.source_doc"
            :chunk-id="item.chunk_id"
            :method="item.method"
          />
        </div>
      </section>
    </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { useHitTestStore } from '@/stores/hitTest'
import { exportCSV } from '@/utils/exportCSV'
import {
  canUseVectorSearch,
  getDocStatusLabel,
  getDocStatusTagType,
  isDocSelectable
} from '@/utils/docStatus'
import { canSubmitInput, INPUT_MAX_LENGTH_SHORT, processUserInput } from '@/utils/inputFilter'
import EmptyState from '@/components/EmptyState.vue'
import RetrieveResultCard from '@/components/RetrieveResultCard.vue'

const MODE_TABS = [
  {
    name: 'vector',
    label: '向量检索',
    tip: '基于语义向量相似度召回，适合表述不同但含义相近的问题。'
  },
  {
    name: 'keyword',
    label: '关键词检索',
    tip: '基于关键词匹配召回，适合专有名词、编号等精确查询。'
  },
  {
    name: 'hybrid',
    label: '混合检索',
    tip: '融合向量与关键词结果，兼顾语义覆盖与精确命中。'
  }
]

const kbStore = useKbStore()
const docStore = useDocStore()
const hitStore = useHitTestStore()

const docOptions = ref([])
const bootLoading = ref(false)
const docsLoading = ref(false)
const pageError = ref('')
/** 知识库切换前一值（v-model 更新后 @change 已拿不到旧值） */
const hitKbPrev = ref(null)

const hasKb = computed(() => kbStore.list.length > 0)
const readyDocs = computed(() => docOptions.value.filter((d) => isDocSelectable(d.status)))

const selectedDocs = computed(() =>
  readyDocs.value.filter((d) => hitStore.docIds.some((id) => String(id) === String(d.id)))
)

/** 所选文档全部 completed 才允许纯向量 */
const vectorModeAllowed = computed(() => {
  if (!selectedDocs.value.length) return true
  return selectedDocs.value.every((d) => canUseVectorSearch(d.status))
})

watch(vectorModeAllowed, (ok) => {
  if (!ok && hitStore.searchType === 'vector') {
    hitStore.setMode('keyword')
    ElMessage.warning('所选文档仅支持关键词/混合检索，已自动切换')
  }
})

/** 输入无内容、加载中、未选可测文档 → 按钮置灰 */
const canRun = computed(() => {
  if (bootLoading.value || hitStore.loading) return false
  if (!hasKb.value || !hitStore.kbId) return false
  if (!readyDocs.value.length) return false
  if (!hitStore.docIds.length) return false
  if (hitStore.searchType === 'vector' && !vectorModeAllowed.value) return false
  const check = canSubmitInput(hitStore.query, INPUT_MAX_LENGTH_SHORT)
  return check.ok
})

const canExport = computed(
  () => Array.isArray(hitStore.results) && hitStore.results.length > 0 && !hitStore.loading
)

const querySafetyTip = computed(() => {
  const dual = processUserInput(hitStore.query, INPUT_MAX_LENGTH_SHORT)
  if (dual.blocked || dual.overLimit) return dual.tip
  return ''
})

const runDisabledTip = computed(() => {
  if (hitStore.loading) return '检索进行中'
  if (!hasKb.value) return '暂无可用知识库'
  if (!hitStore.kbId) return '请先选择知识库'
  if (!readyDocs.value.length) return '暂无可用文档（completed / degraded 可测）'
  if (!hitStore.docIds.length) return '请选择至少一篇可用文档'
  if (!hitStore.query.trim()) return '请输入测试问题'
  const check = canSubmitInput(hitStore.query, INPUT_MAX_LENGTH_SHORT)
  if (!check.ok) return check.tip
  if (hitStore.searchType === 'vector' && !vectorModeAllowed.value) {
    return '所选文档含「仅关键词」状态，请切换检索模式'
  }
  return '运行命中测试'
})

function formatDocLabel(doc) {
  const name = doc.filename || doc.file_name || doc.id
  if (isDocSelectable(doc.status)) return name
  return `${name}（${getDocStatusLabel(doc.status)}，不可测）`
}

async function loadBase() {
  pageError.value = ''
  bootLoading.value = true
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (kbStore.selectedKbId) {
      hitStore.kbId = kbStore.selectedKbId
      hitKbPrev.value = hitStore.kbId
      await loadDocs(hitStore.kbId)
    } else if (kbStore.list.length) {
      hitStore.kbId = kbStore.list[0].id
      hitKbPrev.value = hitStore.kbId
      kbStore.setSelectedKb(hitStore.kbId)
      await loadDocs(hitStore.kbId)
    }
  } catch (e) {
    pageError.value = e?.message || e?.msg || '页面加载失败，请重试'
  } finally {
    bootLoading.value = false
  }
}

async function loadDocs(kbId) {
  docOptions.value = []
  hitStore.docIds = []
  if (!kbId) return
  docsLoading.value = true
  try {
    await docStore.loadList(kbId, { page: 1, page_size: 200 })
    docOptions.value = [...(docStore.list || [])]
  } catch (e) {
    ElMessage.error(e?.message || e?.msg || '文档列表加载失败')
  } finally {
    docsLoading.value = false
  }
}

async function onKbChange(kbId) {
  // @change 触发时 v-model 已更新，需用显式参数作为 next，上一值靠闭包缓存
  const prevKbId = hitKbPrev.value
  hitKbPrev.value = kbId || null
  hitStore.clearResults()
  kbStore.setSelectedKb(kbId || null)
  import('@/utils/cacheLifecycle')
    .then((m) => {
      const prev =
        prevKbId != null && prevKbId !== '' && String(prevKbId) !== String(kbId || '')
          ? m.buildCacheScope(prevKbId)
          : null
      const next = kbId != null && kbId !== '' ? m.buildCacheScope(kbId) : null
      return m.onKbSwitch(prev, next)
    })
    .catch(() => {})
  await loadDocs(kbId)
}

function onModeChange(mode) {
  if (hitStore.loading) return
  hitStore.setMode(mode)
}

async function onRunTest() {
  const validIds = hitStore.docIds.filter((id) =>
    readyDocs.value.some((d) => String(d.id) === String(id))
  )
  hitStore.docIds = validIds

  if (!canRun.value && !hitStore.loading) {
    ElMessage.warning(runDisabledTip.value)
    return
  }

  const check = canSubmitInput(hitStore.query, INPUT_MAX_LENGTH_SHORT)
  if (!check.ok) {
    ElMessage.warning(check.tip)
    return
  }
  // 请求参数使用原始输入
  hitStore.query = check.dual.raw

  try {
    await hitStore.runTest()
  } catch (e) {
    // 错误文案已写入 hitStore.errorMsg，页面展示兜底 UI
  }
}

function onExport() {
  if (!canExport.value) return
  exportCSV(
    hitStore.results.map((item) => ({
      rank: item.rank,
      score: item.score,
      method: item.method || '',
      content: item.content,
      source_doc: item.source_doc,
      chunk_id: item.chunk_id
    })),
    [
      { key: 'rank', label: '排名' },
      { key: 'score', label: '相似度' },
      { key: 'method', label: '检索方式' },
      { key: 'content', label: '分片内容' },
      { key: 'source_doc', label: '来源文档' },
      { key: 'chunk_id', label: '分片 ID' }
    ],
    'rag检索结果'
  )
}

onMounted(() => {
  loadBase()
})
</script>

<style scoped>
.input-safety-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-color-warning);
  max-width: 640px;
}
.hit-test {
  /* page-shell 由 admin.css 统一 */
}

.page-header {
  /* 标题样式由 admin.css 统一 */
}

.page-header h2 {
  /* 由 admin.css 统一 */
}

.hit-test__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 320px;
}

.panel {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 18px;
}

.filter-form {
  margin-bottom: 0;
}

.topn-field {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 400px;
}

.topn-field :deep(.el-slider) {
  flex: 1;
  min-width: 0;
}

.topn-value {
  flex-shrink: 0;
  min-width: 1.5em;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: var(--admin-text, var(--text-color-primary));
  line-height: 1;
  text-align: right;
}

.doc-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.doc-option__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mode-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.mode-tip {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--bg-color-page);
  color: var(--text-color-regular);
  font-size: 13px;
  line-height: 1.5;
}

.result-area {
  min-height: 180px;
  position: relative;
}

.result-placeholder {
  padding: 48px 16px;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 13px;
}
</style>
