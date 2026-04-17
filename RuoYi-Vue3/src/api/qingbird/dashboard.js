import request from '@/utils/request'

// 获取控制台大屏综合概览数据
export function getDashboardOverview() {
  return request({
    url: '/qingbird/dashboard/overview',
    method: 'get',
    hideErrorMsg: true   // 后端未实现时静默
  })
}
