<template>
  <!-- 全局确认弹窗：删除等危险操作二次确认 -->
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="420px"
    append-to-body
    @close="onCancel"
  >
    <p class="confirm-message">{{ message }}</p>
    <template #footer>
      <AppButton type="default" text="取消" @click="onCancel" />
      <AppButton
        type="danger"
        :loading="loading"
        loading-mode="normal"
        text="确认"
        @click="onConfirm"
      />
    </template>
  </el-dialog>
</template>

<script setup>
import AppButton from './AppButton.vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '确认执行该操作吗？' },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

function onCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

function onConfirm() {
  emit('confirm')
}
</script>

<style scoped>
.confirm-message {
  margin: 0;
  line-height: 1.6;
  color: var(--text-color-primary);
}
</style>
