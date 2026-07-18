<template>
  <el-dialog
    :model-value="modelValue"
    title="裁剪图片"
    width="560px"
    align-center
    append-to-body
    destroy-on-close
    :close-on-click-modal="false"
    class="logo-crop-dialog"
    @close="onCancel"
  >
    <div ref="stageRef" class="crop-stage">
      <img
        v-if="imageUrl"
        ref="imgRef"
        class="crop-image"
        :src="imageUrl"
        alt=""
        draggable="false"
        :style="imageStyle"
        @load="onImageLoad"
      />
      <div v-if="ready" class="crop-shade" :style="shadeStyle" />
      <div
        v-if="ready"
        class="crop-box"
        :style="boxStyle"
        @pointerdown.stop="onBoxPointerDown"
      >
        <span class="crop-handle" data-handle="nw" @pointerdown.stop="onHandlePointerDown($event, 'nw')" />
        <span class="crop-handle" data-handle="ne" @pointerdown.stop="onHandlePointerDown($event, 'ne')" />
        <span class="crop-handle" data-handle="sw" @pointerdown.stop="onHandlePointerDown($event, 'sw')" />
        <span class="crop-handle" data-handle="se" @pointerdown.stop="onHandlePointerDown($event, 'se')" />
      </div>
    </div>

    <div class="crop-zoom">
      <el-icon class="crop-zoom__icon" @click="nudgeZoom(-0.1)"><ZoomOut /></el-icon>
      <el-slider
        v-model="zoom"
        class="crop-zoom__slider"
        :min="1"
        :max="3"
        :step="0.01"
        :show-tooltip="false"
        @input="onZoomInput"
      />
      <el-icon class="crop-zoom__icon" @click="nudgeZoom(0.1)"><ZoomIn /></el-icon>
    </div>

    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button type="primary" :loading="exporting" @click="onConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ZoomIn, ZoomOut } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  imageUrl: { type: String, default: '' },
  outputSize: { type: Number, default: 512 }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const stageRef = ref(null)
const imgRef = ref(null)
const ready = ref(false)
const exporting = ref(false)
const zoom = ref(1)

/** 缩放 1 时图片在 stage 内的适配尺寸 */
const baseFit = ref({ width: 0, height: 0 })
/** 图片在 stage 内的显示矩形（含缩放） */
const display = ref({ left: 0, top: 0, width: 0, height: 0 })
const crop = ref({ x: 0, y: 0, size: 0 })
const natural = ref({ width: 0, height: 0 })

const imageStyle = computed(() => {
  if (!baseFit.value.width) return {}
  return {
    width: `${baseFit.value.width * zoom.value}px`,
    height: `${baseFit.value.height * zoom.value}px`,
    maxWidth: 'none',
    maxHeight: 'none'
  }
})

const boxStyle = computed(() => ({
  left: `${crop.value.x}px`,
  top: `${crop.value.y}px`,
  width: `${crop.value.size}px`,
  height: `${crop.value.size}px`
}))

const shadeStyle = computed(() => ({
  left: `${crop.value.x}px`,
  top: `${crop.value.y}px`,
  width: `${crop.value.size}px`,
  height: `${crop.value.size}px`,
  boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.55)'
}))

let dragMode = null
let dragStart = { x: 0, y: 0, crop: null }
let resizeObserver = null
let cropCenterRatio = { x: 0.5, y: 0.5 }

function stageSize() {
  const stage = stageRef.value
  if (!stage) return { w: 0, h: 0 }
  return { w: stage.clientWidth, h: stage.clientHeight }
}

function computeBaseFit() {
  const { w: sw, h: sh } = stageSize()
  const n = natural.value
  if (!sw || !sh || !n.width) return { width: 0, height: 0 }
  const scale = Math.min(sw / n.width, sh / n.height)
  return { width: n.width * scale, height: n.height * scale }
}

function syncDisplayFromZoom() {
  const { w: sw, h: sh } = stageSize()
  const width = baseFit.value.width * zoom.value
  const height = baseFit.value.height * zoom.value
  display.value = {
    left: (sw - width) / 2,
    top: (sh - height) / 2,
    width,
    height
  }
}

function visibleImageBounds() {
  const { w: sw, h: sh } = stageSize()
  const d = display.value
  return {
    left: Math.max(d.left, 0),
    top: Math.max(d.top, 0),
    right: Math.min(d.left + d.width, sw),
    bottom: Math.min(d.top + d.height, sh)
  }
}

function clampCrop(next) {
  const v = visibleImageBounds()
  const maxW = Math.max(0, v.right - v.left)
  const maxH = Math.max(0, v.bottom - v.top)
  const minSize = 40
  const size = Math.max(minSize, Math.min(next.size, maxW, maxH))
  const x = Math.min(Math.max(next.x, v.left), v.right - size)
  const y = Math.min(Math.max(next.y, v.top), v.bottom - size)
  return { x, y, size }
}

function placeDefaultCrop() {
  const v = visibleImageBounds()
  const side = Math.min(v.right - v.left, v.bottom - v.top)
  crop.value = {
    x: v.left + (v.right - v.left - side) / 2,
    y: v.top + (v.bottom - v.top - side) / 2,
    size: side
  }
  rememberCropCenter()
}

function rememberCropCenter() {
  const d = display.value
  if (d.width < 1 || d.height < 1) return
  cropCenterRatio = {
    x: (crop.value.x + crop.value.size / 2 - d.left) / d.width,
    y: (crop.value.y + crop.value.size / 2 - d.top) / d.height
  }
}

function restoreCropAroundCenter() {
  const d = display.value
  const size = crop.value.size
  const cx = d.left + d.width * cropCenterRatio.x
  const cy = d.top + d.height * cropCenterRatio.y
  crop.value = clampCrop({
    x: cx - size / 2,
    y: cy - size / 2,
    size
  })
}

function measureLayout({ resetCrop = false } = {}) {
  const img = imgRef.value
  const stage = stageRef.value
  if (!img || !stage || !img.naturalWidth) return

  natural.value = { width: img.naturalWidth, height: img.naturalHeight }
  baseFit.value = computeBaseFit()
  syncDisplayFromZoom()

  if (resetCrop || !ready.value) {
    placeDefaultCrop()
  } else {
    restoreCropAroundCenter()
  }
  ready.value = true
}

function onImageLoad() {
  nextTick(() => measureLayout({ resetCrop: true }))
}

function onZoomInput() {
  if (!ready.value) return
  rememberCropCenter()
  syncDisplayFromZoom()
  // 放大后选区相对变小：按显示比例缩放选区边长
  const side = Math.min(
    crop.value.size,
    visibleImageBounds().right - visibleImageBounds().left,
    visibleImageBounds().bottom - visibleImageBounds().top
  )
  crop.value = clampCrop({ ...crop.value, size: side })
  restoreCropAroundCenter()
}

function nudgeZoom(delta) {
  zoom.value = Math.min(3, Math.max(1, Number((zoom.value + delta).toFixed(2))))
  onZoomInput()
}

function onBoxPointerDown(e) {
  if (e.button !== 0) return
  dragMode = 'move'
  dragStart = { x: e.clientX, y: e.clientY, crop: { ...crop.value } }
  e.currentTarget.setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function onHandlePointerDown(e, handle) {
  if (e.button !== 0) return
  dragMode = handle
  dragStart = { x: e.clientX, y: e.clientY, crop: { ...crop.value } }
  e.currentTarget.setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function onPointerMove(e) {
  if (!dragMode || !dragStart.crop) return
  const dx = e.clientX - dragStart.x
  const dy = e.clientY - dragStart.y
  const c0 = dragStart.crop

  if (dragMode === 'move') {
    crop.value = clampCrop({ x: c0.x + dx, y: c0.y + dy, size: c0.size })
    rememberCropCenter()
    return
  }

  let size = c0.size
  let x = c0.x
  let y = c0.y

  if (dragMode === 'se') {
    size = c0.size + (dx + dy) / 2
    x = c0.x
    y = c0.y
  } else if (dragMode === 'nw') {
    size = c0.size - (dx + dy) / 2
    x = c0.x + c0.size - size
    y = c0.y + c0.size - size
  } else if (dragMode === 'ne') {
    size = c0.size + (-dy + dx) / 2
    x = c0.x
    y = c0.y + c0.size - size
  } else if (dragMode === 'sw') {
    size = c0.size + (dy - dx) / 2
    x = c0.x + c0.size - size
    y = c0.y
  }

  crop.value = clampCrop({ x, y, size })
  rememberCropCenter()
}

function onPointerUp() {
  dragMode = null
  dragStart = { x: 0, y: 0, crop: null }
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
}

function displayToNatural(px, py, sizePx) {
  const d = display.value
  const n = natural.value
  const scaleX = n.width / d.width
  const scaleY = n.height / d.height
  return {
    sx: (px - d.left) * scaleX,
    sy: (py - d.top) * scaleY,
    sw: sizePx * scaleX,
    sh: sizePx * scaleY
  }
}

async function onConfirm() {
  const img = imgRef.value
  if (!img || !ready.value) return
  exporting.value = true
  try {
    const { sx, sy, sw, sh } = displayToNatural(crop.value.x, crop.value.y, crop.value.size)
    const out = Math.max(64, props.outputSize)
    const canvas = document.createElement('canvas')
    canvas.width = out
    canvas.height = out
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, out, out)
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, out, out)

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (b) => (b ? resolve(b) : reject(new Error('导出失败'))),
        'image/png',
        0.92
      )
    })
    const file = new File([blob], 'logo.png', { type: 'image/png' })
    const previewUrl = URL.createObjectURL(blob)
    emit('confirm', { file, previewUrl })
    emit('update:modelValue', false)
  } catch (err) {
    console.error(err)
    ElMessage.error('裁剪失败，请换一张图片重试')
  } finally {
    exporting.value = false
  }
}

function onCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

watch(
  () => [props.modelValue, props.imageUrl],
  async ([open]) => {
    ready.value = false
    zoom.value = 1
    if (!open) return
    await nextTick()
    if (imgRef.value?.complete && imgRef.value.naturalWidth) {
      measureLayout({ resetCrop: true })
    }
    if (stageRef.value && !resizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        if (props.modelValue && imgRef.value?.naturalWidth) {
          measureLayout({ resetCrop: false })
        }
      })
      resizeObserver.observe(stageRef.value)
    }
  }
)

onBeforeUnmount(() => {
  onPointerUp()
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<style scoped>
.crop-stage {
  position: relative;
  width: 100%;
  height: 360px;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--glass-border, var(--border-color));
  user-select: none;
  touch-action: none;
}

.crop-image {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: block;
  pointer-events: none;
  object-fit: fill;
}

.crop-shade {
  position: absolute;
  pointer-events: none;
  border-radius: 2px;
}

.crop-box {
  position: absolute;
  box-sizing: border-box;
  border: 2px solid rgba(140, 190, 255, 0.95);
  cursor: move;
  border-radius: 2px;
  z-index: 2;
}

.crop-handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #fff;
  border: 2px solid rgba(64, 158, 255, 0.95);
  border-radius: 2px;
  box-sizing: border-box;
}

.crop-handle[data-handle='nw'] {
  left: -6px;
  top: -6px;
  cursor: nwse-resize;
}

.crop-handle[data-handle='ne'] {
  right: -6px;
  top: -6px;
  cursor: nesw-resize;
}

.crop-handle[data-handle='sw'] {
  left: -6px;
  bottom: -6px;
  cursor: nesw-resize;
}

.crop-handle[data-handle='se'] {
  right: -6px;
  bottom: -6px;
  cursor: nwse-resize;
}

.crop-zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding: 0 4px;
}

.crop-zoom__slider {
  flex: 1;
}

.crop-zoom__icon {
  font-size: 18px;
  color: var(--admin-text-muted, rgba(200, 205, 220, 0.7));
  cursor: pointer;
  flex-shrink: 0;
}

.crop-zoom__icon:hover {
  color: var(--el-color-primary);
}
</style>

<style>
/* teleported dialog：标题居中 */
.logo-crop-dialog.el-dialog .el-dialog__header {
  text-align: center;
  margin-right: 0;
  padding-right: 16px;
}

.logo-crop-dialog.el-dialog .el-dialog__title {
  width: 100%;
  text-align: center;
}

.logo-crop-dialog.el-dialog .el-dialog__headerbtn {
  top: 50%;
  transform: translateY(-50%);
}
</style>
