/**
 * 公共组件统一导出入口
 * 供前端 A 页面及其他模块按需引用，避免逐文件路径导入
 */
import AppButton from './AppButton.vue'
import ConfirmDialog from './ConfirmDialog.vue'
import AppPagination from './AppPagination.vue'
import AppTable from './AppTable.vue'
import EmptyState from './EmptyState.vue'
import RetrieveResultCard from './RetrieveResultCard.vue'
import ChatBubble from './ChatBubble.vue'
import FileUploader from './FileUploader.vue'
import StreamText from './StreamText.vue'

export {
  AppButton,
  ConfirmDialog,
  AppPagination,
  AppTable,
  EmptyState,
  RetrieveResultCard,
  ChatBubble,
  FileUploader,
  StreamText
}

export default {
  AppButton,
  ConfirmDialog,
  AppPagination,
  AppTable,
  EmptyState,
  RetrieveResultCard,
  ChatBubble,
  FileUploader,
  StreamText
}
