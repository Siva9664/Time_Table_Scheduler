import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (username, password) => api.post('/auth/login', new URLSearchParams({ username, password })),
  register: (data) => api.post('/auth/register', data),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
};

export const batchAPI = {
  getAll: () => api.get('/batches'),
  create: (data) => api.post('/batches', data),
  update: (id, data) => api.put(`/batches/${id}`, data),
  delete: (id) => api.delete(`/batches/${id}`)
};

export const departmentAPI = {
  getAll: () => api.get('/departments'),
  create: (data) => api.post('/departments', data),
  delete: (id) => api.delete(`/departments/${id}`)
};

export const classAPI = {
  getAll: () => api.get('/classes'),
  create: (data) => api.post('/classes', data),
  delete: (id) => api.delete(`/classes/${id}`)
};

export const subjectAPI = {
  getAll: () => api.get('/subjects'),
  create: (data) => api.post('/subjects', data),
  update: (id, data) => api.put(`/subjects/${id}`, data),
  delete: (id) => api.delete(`/subjects/${id}`)
};

export const facultyAPI = {
  getAll: () => api.get('/faculty'),
  create: (data) => api.post('/faculty', data),
  delete: (id) => api.delete(`/faculty/${id}`)
};

export const roomAPI = {
  getAll: () => api.get('/rooms'),
  create: (data) => api.post('/rooms', data),
  delete: (id) => api.delete(`/rooms/${id}`)
};

export const timetableAPI = {
  generate: (data) => api.post('/generate', data),
  getAll: () => api.get('/timetables/'),
  getById: (id) => api.get(`/timetables/${id}`),
  delete: (id) => api.delete(`/timetables/${id}`)
};

export default api;
