import request from './request'

export function getSubjects() {
  return request.get('/subjects')
}

export function createSubject(data) {
  return request.post('/admin/subjects', data)
}

export function updateSubject(id, data) {
  return request.put(`/admin/subjects/${id}`, data)
}

export function deleteSubject(id) {
  return request.delete(`/admin/subjects/${id}`)
}
