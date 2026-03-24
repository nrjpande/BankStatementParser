import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: API_URL,
  timeout: 120000,
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
      timeout: 300000,
    });
  },
  status: (jobId) => api.get(`/api/upload/status/${jobId}`),
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

export const tallyAPI = {
  markReady: (statementId, data) => api.post(`/api/tally/mark-ready/${statementId}`, data),
  getPending: () => api.get('/api/tally/pending'),
  confirmSync: (ids) => api.post('/api/tally/confirm-sync', ids),
};

export const exportAPI = {
  tally: (statementId, data) => api.post(`/api/export/tally/${statementId}`, data, { responseType: 'blob' }),
};

export const dashboardAPI = {
  stats: () => api.get('/api/dashboard/stats'),
};

export const ledgersAPI = {
  list: () => api.get('/api/ledgers'),
  names: () => api.get('/api/ledgers/names'),
  create: (data) => api.post('/api/ledgers', data),
  delete: (id) => api.delete(`/api/ledgers/${id}`),
  importTallyXml: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/ledgers/import-tally-xml', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export default api;
