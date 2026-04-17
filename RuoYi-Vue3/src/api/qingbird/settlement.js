import request from '@/utils/request'

// 查询结算信息列表
export function listSettlement(query) {
  return request({
    url: '/qingbird/settlement/list',
    method: 'get',
    params: query
  })
}

// 查询结算信息详细
export function getSettlement(id) {
  return request({
    url: '/qingbird/settlement/' + id,
    method: 'get'
  })
}

// 新增结算信息
export function addSettlement(data) {
  return request({
    url: '/qingbird/settlement',
    method: 'post',
    data: data
  })
}

// 修改结算信息
export function updateSettlement(data) {
  return request({
    url: '/qingbird/settlement',
    method: 'put',
    data: data
  })
}

// 删除结算信息
export function delSettlement(id) {
  return request({
    url: '/qingbird/settlement/' + id,
    method: 'delete'
  })
}
