<template>
  <div class="hit-test" v-loading="hitStore.loading" element-loading-text="加载中...">
    <div class="page-header">
      <h2>命中率测试</h2>
      <AppButton
        type="primary"
        text="导出 CSV"
        :disabled="!canExport"
        :title="canExport ? '导出检索结果' : '暂无命中结果可导出'"
        @click="onExport"
      />
    </div>

    <!-- 无知识库时隐藏运行测试主入口 -->
    <EmptyState v-if="!hasKb" type="kb" tip="暂无知识库，无法进行命中测试" />

    <template v-else>
      <el-form label-width="96px" class="filter-form">
        <!-- 级联：知识库 -> 文档 -->
        <el-form-item label="知识库">
          <el-select
            v-model="hitStore.kbId"
            placeholder="请选择知识库"
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
            placeholder="请选择文档"
            style="width: 360px"
            :disabled="!hitStore.kbId"
          >
            <el-option
              v-for="doc in docOptions"
              :key="doc.id"
              :label="doc.file_name"
              :value="doc.id"
            />
          </el-select>
        </el-form-item>

        <!-- 检索模式：切换后清空历史结果 -->
        <el-form-item label="检索模式">
          <el-radio-group :model-value="hitStore.mode" @change="onModeChange">
            <el-radio-button label="vector">向量</el-radio-button>
            <el-radio-button label="keyword">关键词</el-radio-button>
            <el-radio-button label="hybrid">混合</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="测试问题">
          <el-input
            v-model="hitStore.query"
            type="textarea"
            :rows="3"
            maxlength="500"
            placeholder="请输入测试问题"
            style="max-width: 640px"
          />
        </el-form-item>

        <el-form-item label="TopN">
          <el-slider
            v-model="hitStore.topN"
            :min="3"
            :max="10"
            :step="1"
            show-stops
            style="max-width: 360px"
          />
        </el-form-item>

        <el-form-item>
          <!-- 无文档时主按钮置灰；点击内再做未选/空输入兜底拦截 -->
          <AppButton
            type="primary"
            text="运行测试"
            :loading="hitStore.loading"
            loading-mode="normal"
            :disabled="!canRun"
            :title="runDisabledTip"
            @click="onRunTest"
          />
        </el-form-item>
      </el-form>

      <!-- 检索结果区 -->
      <div class="result-area">
        <EmptyState
          v-if="hitStore.hasSearched && !hitStore.results.length"
          type="retrieve"
        />
        <RetrieveResultCard
          v-for="item in hitStore.results"
          :key="`${item.chunk_id}-${item.rank}`"
          :rank="item.rank"
          :score="item.score"
          :content="item.content"
          :source-doc="item.source_doc"
          :chunk-id="item.chunk_id"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useKbStore } from '@/stores/kb'
import { useDocStore } from '@/stores/doc'
import { useHitTestStore } from '@/stores/hitTest'
import { exportCSV } from '@/utils/exportCSV'
import AppButton from '@/components/AppButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import RetrieveResultCard from '@/components/RetrieveResultCard.vue'

const kbStore = useKbStore()
const docStore = useDocStore()
const hitStore = useHitTestStore()

const docOptions = ref([])

const hasKb = computed(() => kbStore.list.length > 0)
const hasDocs = computed(() => docOptions.value.length > 0)
const canRun = computed(() => hasKb.value && hasDocs.value && !!hitStore.kbId)
const canExport = computed(() => Array.isArray(hitStore.results) && hitStore.results.length > 0)

const runDisabledTip = computed(() => {
  if (!hasKb.value) return '无操作权限：暂无可用知识库'
  if (!hitStore.kbId) return '请先选择知识库'
  if (!hasDocs.value) return '无操作权限：当前知识库暂无文档'
  return '运行命中测试'
})

async function loadBase() {
  try {
    await kbStore.loadList({ page: 1, page_size: 100 })
    if (kbStore.selectedKbId) {
      hitStore.kbId = kbStore.selectedKbId
      await loadDocs(hitStore.kbId)
    }
  } catch (e) {
    // 全局 axios 处理
  }
}

async function loadDocs(kbId) {
  docOptions.value = []
  hitStore.docIds = []
  if (!kbId) return
  try {
    await docStore.loadList(kbId, { page: 1, page_size: 200 })
    // 仅展示当前库文档，跨库隔离
    docOptions.value = (docStore.list || []).filter((d) => d.status !== 'failed')
  } catch (e) {
    // 全局 axios 处理
  }
}

async function onKbChange(kbId) {
  hitStore.clearResults()
  kbStore.setSelectedKb(kbId || null)
  await loadDocs(kbId)
}

function onModeChange(mode) {
  // 切换模式清空历史结果，三种模式排序差异由后端/Mock 返回保证
  hitStore.setMode(mode)
}

/**
 * 运行测试：5 大边界拦截
 * 1) 未选文档阻断
 * 2) 空输入阻断
 * 3) 无匹配空状态（结果区）
 * 4) 模式切换清结果（setMode）
 * 5) 三种模式结果排序差异化展示（接口返回）
 */
async function onRunTest() {
  if (!hitStore.docIds.length) {
    ElMessage.warning('请先选择文档')
    return
  }
  if (!hitStore.query.trim()) {
    ElMessage.warning('请输入测试问题')
    return
  }
  try {
    await hitStore.runTest()
  } catch (e) {
    // code5001 等由全局拦截统一提示
  }
}

/** CSV 导出：前置判空 + UTF-8 BOM，字段固定 */
function onExport() {
  const ok = exportCSV(
    hitStore.results.map((item) => ({
      rank: item.rank,
      score: item.score,
      content: item.content,
      source_doc: item.source_doc,
      chunk_id: item.chunk_id
    })),
    [
      { key: 'rank', label: '排名' },
      { key: 'score', label: '相似度' },
      { key: 'content', label: '分片内容' },
      { key: 'source_doc', label: '来源文档' },
      { key: 'chunk_id', label: '分片 ID' }
    ],
    'rag检索结果'
  )
  if (!ok) {
    // 无数据不执行导出；按钮已置灰，此处兜底
    return
  }
}

onMounted(() => {
  loadBase()
})
</script>

<style scoped>
.hit-test {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  color: var(--text-color-primary);
}

.filter-form {
  margin-bottom: 12px;
}

.result-area {
  margin-top: 8px;
}
</style>
