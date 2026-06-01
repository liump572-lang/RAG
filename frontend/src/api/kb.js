import request from './request'

export function uploadDocument(formData) {
  return request.post('/kb/upload', formData)
}

export function getDocumentList(params) {
  return request.get('/kb', { params })
}

export function getDocument(id) {
  return request.get(`/kb/${id}`)
}

export function deleteDocument(id) {
  return request.delete(`/kb/${id}`)
}

export function reparseDocument(id) {
  return request.post(`/kb/${id}/reparse`)
}

export function getDocumentChunks(id) {
  return request.get(`/kb/${id}/chunks`)
}

export function retrievalTest(params) {
  return request.post('/kb/retrieval-test', null, { params })
}
