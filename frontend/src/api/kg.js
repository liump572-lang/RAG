import request from './request'

export function getSubgraph(params) {
  return request.get('/kg/subgraph', { params })
}

export function searchKnowledge(params) {
  return request.get('/kg/search', { params })
}

export function getPoints(params) {
  return request.get('/kg/points', { params })
}

export function createPoint(data) {
  return request.post('/kg/points', data)
}

export function updatePoint(id, data) {
  return request.put(`/kg/points/${id}`, data)
}

export function deletePoint(id) {
  return request.delete(`/kg/points/${id}`)
}

export function getRelations(params) {
  return request.get('/kg/relations', { params })
}

export function createRelation(data) {
  return request.post('/kg/relations', data)
}

export function deleteRelation(id) {
  return request.delete(`/kg/relations/${id}`)
}

export function searchSubgraph(params) {
  return request.get('/kg/search-subgraph', { params })
}

export function generateDocument(data) {
  return request.post('/kg/generate-document', data)
}
