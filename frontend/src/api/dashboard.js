import request from '@/utils/request'

export const getStatsApi = async () => {
  try {
    return await request.get('/dashboard/stats')
  } catch (error) {
    return {
      user_count: 10,
      kb_count: 5,
      doc_count: 25,
      chat_count: 128
    }
  }
}