import request from '@/utils/request'

// 获取薪资预览数据
export function getSalaryPreview(params) {
  return request({
    url: '/qingbird/salary/preview',
    method: 'get',
    params,
    hideErrorMsg: true   // 后端未实现时静默
  })
}

// 获取薪资核算大表
export function getSalaryTable(params) {
  return request({
    url: '/qingbird/salary/table',
    method: 'get',
    params,
    hideErrorMsg: true
  })
}
