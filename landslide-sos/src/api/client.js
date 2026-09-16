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
  zone: (id) => request(`/zones/${id}`),
  swiTimeline: (id) => request(`/zones/${id}/swi-timeline`),

  alerts: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
    const q = qs.toString();
    return request(`/alerts${q ? `?${q}` : ''}`);
  },
  recentAlerts: () => request('/alerts/recent'),
  unreadCount: () => request('/alerts/unread-count'),
  acknowledgeAlert: (id) => request(`/alerts/${id}/ack`, { method: 'PATCH' }),

  rainfall: (zoneId) =>
    request(`/rainfall${zoneId ? `?zone_id=${zoneId}` : ''}`),
  rainfallHeatmap: () => request('/rainfall/heatmap'),

  dashboardStats: () => request('/dashboard/stats'),
  publicStats: () => request('/stats/public'),

  sendSos: (payload) => request('/sos/send', { method: 'POST', body: payload }),

  adminHealth: () => request('/admin/health'),
  adminUsers: () => request('/admin/users'),
  adminMetrics: () => request('/admin/metrics'),
  adminModelPerformance: () => request('/admin/model-performance'),
};