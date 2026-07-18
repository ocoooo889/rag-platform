<template>
  <!-- 统一封装：主操作对齐文档管理「批量删除」= type="primary" 实心主题色 -->
  <el-button
    class="app-button"
    :type="type"
    :link="link"
    :disabled="disabled || loading"
    :loading="loading"
    :title="title"
    v-bind="$attrs"
    @click="onClick"
  >
    <slot>{{ displayText }}</slot>
  </el-button>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  type: { type: String, default: 'primary' },
  /** true 时为行内文字链（对齐角色管理「编辑」） */
  link: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  /** normal | upload | sse */
  loadingMode: { type: String, default: 'normal' },
  /** 按钮文案 */
  text: { type: String, default: '' },
  title: { type: String, default: '' }
})

const emit = defineEmits(['click'])

const LOADING_TEXT_MAP = {
  normal: '加载中...',
  upload: '文档上传中，请稍候',
  sse: 'AI 思考中...'
}

const displayText = computed(() => {
  if (props.loading) return LOADING_TEXT_MAP[props.loadingMode] || LOADING_TEXT_MAP.normal
  return props.text
})

function onClick(evt) {
  if (props.disabled || props.loading) return
  emit('click', evt)
}
</script>
