import request from './request'

export function getWrongQuestions(params) {
  return request.get('/wq', { params })
}

export function getWrongQuestion(id) {
  return request.get(`/wq/${id}`)
}

export function createWrongQuestion(data) {
  return request.post('/wq', data)
}

export function updateWrongQuestion(id, data) {
  return request.put(`/wq/${id}`, data)
}

export function deleteWrongQuestion(id) {
  return request.delete(`/wq/${id}`)
}

export function getWrongStats() {
  return request.get('/wq/stats')
}

export function getPracticeSet(params) {
  return request.get('/wq/practice', { params })
}

export function reviewWrongQuestion(id, data) {
  return request.post(`/wq/${id}/review`, data)
}
