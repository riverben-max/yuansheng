import request from '@/utils/request'

// 查询分公司主体档案列表 (Admin用)
export function listBranchInfo(query) {
  return request({
    url: '/qingbird/branch-info/list',
    method: 'get',
    params: query,
    hideErrorMsg: true
  })
}

// 查询分公司主体档案详细 (Admin用)
export function getBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/' + id,
    method: 'get',
    hideErrorMsg: true
  })
}

// 获取我的分公司档案 (Manager用)
export function getMyBranchInfo() {
  return request({
    url: '/qingbird/branch-info/my',
    method: 'get',
    hideErrorMsg: true
  })
}

// 直接新增分公司档案记录 (Admin用)
export function addBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info',
    method: 'post',
    data: data,
    hideErrorMsg: true
  })
}

// 修改分公司档案记录 (Admin用)
export function updateBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info',
    method: 'put',
    data: data,
    hideErrorMsg: true
  })
}

// 删除分公司档案记录 (Admin用)
export function delBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/' + id,
    method: 'delete',
    hideErrorMsg: true
  })
}

// 提交审核/新增保养
export function submitBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info/submit',
    method: 'post',
    data: data,
    hideErrorMsg: true
  })
}

// 审核通过 (Admin用)
export function approveBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/approve/' + id,
    method: 'put',
    hideErrorMsg: true
  })
}
