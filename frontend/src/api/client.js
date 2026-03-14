import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('b2t_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('b2t_token');
      localStorage.removeItem('b2t_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  me: () => api.get('/api/auth/me'),
};

export const uploadAPI = {
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const statementsAPI = {
  list: () => api.get('/api/statements'),
  delete: (id) => api.delete(`/api/statements/${id}`),
};

export const transactionsAPI = {
  get: (statementId) => api.get(`/api/transactions/${statementId}`),
  update: (id, data) => api.put(`/api/transactions/${id}`, data),
  bulkUpdate: (data) => api.put('/api/transactions/bulk/update', data),
};

export const rulesAPI = {
  list: () => api.get('/api/mapping-rules'),
  create: (data) => api.post('/api/mapping-rules', data),
  delete: (id) => api.delete(`/api/mapping-rules/${id}`),
  apply: (statementId) => api.post(`/api/apply-rules/${statementId}`),
};

export const exportAPI = {
  tally: (statementId, data) => api.post(`/api/export/tally/${statementId}`, data, { responseType: 'blob' }),
};

export const dashboardAPI = {
  stats: () => api.get('/api/dashboard/stats'),
};

export const ledgersAPI = {
  list: () => api.get('/api/ledgers'),
};

export default api;
