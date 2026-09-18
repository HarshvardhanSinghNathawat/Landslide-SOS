const BASE = import.meta.env.VITE_API_BASE || '/api/v1';
export const TOKEN_KEY = 'landslide_sos_token';

const getToken = () => localStorage.getItem(TOKEN_KEY);

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const authToken = token === '' ? null : token || getToken();
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: { email, password }, token: '' }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  me: () => request('/auth/me'),

  zones: () => request('/zones'),
  swiTimeline: (id) =>
    request(`/zones/${id}/swi`).then((data) => (data && data.points) || []),

  alerts: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
    const q = qs.toString();
    return request(`/alerts${q ? `?${q}` : ''}`);
  },
  recentAlerts: () => request('/alerts?limit=5'),
  unreadCount: () =>
    request('/alerts?limit=50').then((items) => ({
      count: Array.isArray(items) ? items.filter((a) => a.status === 'pending').length : 0,
    })),
  acknowledgeAlert: (id) =>
    request(`/alerts/${id}/acknowledge`, { method: 'PATCH', body: {} }),

  rainfall: (zoneId, hours) => {
    const params = new URLSearchParams();
    if (zoneId) params.set('zone_id', zoneId);
    if (hours) params.set('hours', hours);
    const qs = params.toString();
    return request(`/rainfall${qs ? `?${qs}` : ''}`);
  },

  dashboardStats: () => request('/dashboard/stats'),
  publicStats: () => request('/dashboard/stats'),

  sendSos: (payload) => request('/alerts/sos', { method: 'POST', body: payload }),

  adminHealth: () => request('/system/health'),
  adminUsers: () => request('/admin/users'),
  adminMetrics: () => request('/admin/model/performance'),
  adminCreateUser: (payload) => request('/admin/users', { method: 'POST', body: payload }),
  adminUpdateUser: (id, payload) => request(`/admin/users/${id}`, { method: 'PUT', body: payload }),

  planRoute: (payload) => request('/routes/plan', { method: 'POST', body: payload }),
};