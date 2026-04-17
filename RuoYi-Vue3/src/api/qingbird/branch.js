import request from '@/utils/request'

// 获取分公司运营概览数据
export function getBranchOverview(branchCode) {
  return request({
    url: '/qingbird/branch/overview',
    method: 'get',
    params: { branchCode },
    hideErrorMsg: true   // 后端未实现时静默，不弹错误提示
  })
}

// 获取分公司列表
export function getBranchList() {
  return request({
    url: '/qingbird/branch/list',
    method: 'get'
  })
}
