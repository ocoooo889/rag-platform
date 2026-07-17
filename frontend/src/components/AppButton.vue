<template>
  <!-- 通用按钮：内置三类加载文案，防止重复点击 -->
  <el-button
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
  link: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  /** normal | upload | sse */
  loadingMode: { type: String, default: 'normal' },
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
