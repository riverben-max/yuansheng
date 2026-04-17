import request from '@/utils/request'

// 查询云文档文章列表
export function listDoc(query) {
  return request({
    url: '/qingbird/doc/list',
    method: 'get',
    params: query
  })
}

// 查询云文档文章详细
export function getDoc(id) {
  return request({
    url: '/qingbird/doc/' + id,
    method: 'get'
  })
}

// 新增云文档文章
export function addDoc(data) {
  return request({
    url: '/qingbird/doc',
    method: 'post',
    data: data
  })
}

// 修改云文档文章
export function updateDoc(data) {
  return request({
    url: '/qingbird/doc',
    method: 'put',
    data: data
  })
}

// 删除云文档文章
export function delDoc(id) {
  return request({
    url: '/qingbird/doc/' + id,
    method: 'delete'
  })
}
