import request from '@/utils/request'

export const getStatsApi = () => request.get('/dashboard/stats')