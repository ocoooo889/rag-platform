<template>
  <!-- 全局确认弹窗：删除等危险操作二次确认 -->
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="420px"
    align-center
    append-to-body
    @close="onCancel"
  >
    <p class="confirm-message">{{ message }}</p>
    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
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
  color: var(--admin-text, var(--text-color-regular));
}
</style>
