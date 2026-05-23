import request from '@/utils/request'

const endpointNotReadyFallback = {
  hideErrorCodes: [404]
}

// 查询分公司主体档案列表 (Admin用)
export function listBranchInfo(query) {
  return request({
    url: '/qingbird/branch-info/list',
    method: 'get',
    params: query,
    ...endpointNotReadyFallback
  })
}

// 查询分公司主体档案详细 (Admin用)
export function getBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/' + id,
    method: 'get',
    ...endpointNotReadyFallback
  })
}

// 获取我的分公司档案 (Manager用)
export function getMyBranchInfo() {
  return request({
    url: '/qingbird/branch-info/my',
    method: 'get',
    ...endpointNotReadyFallback
  })
}

// 直接新增分公司档案记录 (Admin用)
export function addBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info',
    method: 'post',
    data: data,
    ...endpointNotReadyFallback
  })
}

// 修改分公司档案记录 (Admin用)
export function updateBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info',
    method: 'put',
    data: data,
    ...endpointNotReadyFallback
  })
}

// 删除分公司档案记录 (Admin用)
export function delBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/' + id,
    method: 'delete',
    ...endpointNotReadyFallback
  })
}

// 提交审核/新增保养
export function submitBranchInfo(data) {
  return request({
    url: '/qingbird/branch-info/submit',
    method: 'post',
    data: data,
    ...endpointNotReadyFallback
  })
}

// 审核通过 (Admin用)
export function approveBranchInfo(id) {
  return request({
    url: '/qingbird/branch-info/approve/' + id,
    method: 'put',
    ...endpointNotReadyFallback
  })
}
