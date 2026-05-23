/**
 * Mac Calendar — Global App State & API Client
 */

// ─── CSRF Token ────────────────────────────────────────────────────────────
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrftoken"]');
  if (meta) return meta.getAttribute('content');
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

// ─── User role helpers ─────────────────────────────────────────────────────
const USER_ROLE = document.querySelector('meta[name="user-role"]')?.getAttribute('content') || '';
const USER_RESTAURANT_ID = document.querySelector('meta[name="user-restaurant-id"]')?.getAttribute('content') || '';
const _SUPER_ROLES = ['admin', 'rh', 'marketing'];
const _MANAGER_ROLES = ['admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno'];
function isSuperRole() { return _SUPER_ROLES.includes(USER_ROLE); }
function isManagerOrAbove() { return _MANAGER_ROLES.includes(USER_ROLE); }

// ─── API Client ────────────────────────────────────────────────────────────
const API = {
  _headers() {
    return {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    };
  },

  async request(method, url, body = null, multipart = false) {
    const opts = {
      method,
      credentials: 'same-origin',
    };
    if (!multipart) {
      opts.headers = this._headers();
    } else {
      opts.headers = { 'X-CSRFToken': getCsrfToken() };
    }
    if (body) {
      opts.body = multipart ? body : JSON.stringify(body);
    }
    try {
      const res = await fetch(url, opts);
      if (res.status === 401) {
        window.location.href = '/auth/login';
        return null;
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        console.error('API error:', res.status, data);
      }
      return data;
    } catch (err) {
      console.error('Network error:', err);
      return null;
    }
  },

  get(url) { return this.request('GET', url); },
  post(url, body) { return this.request('POST', url, body); },
  put(url, body) { return this.request('PUT', url, body); },
  patch(url, body) { return this.request('PATCH', url, body); },
  delete(url) { return this.request('DELETE', url); },
  upload(url, formData) { return this.request('POST', url, formData, true); },
};

// ─── Alpine.js Global State ────────────────────────────────────────────────
function appState() {
  return {
    darkMode: localStorage.getItem('darkMode') === 'true',
    unreadCount: 0,
    _pollInterval: null,

    toggleDark() {
      this.darkMode = !this.darkMode;
      localStorage.setItem('darkMode', this.darkMode);
    },

    async fetchUnreadCount() {
      const data = await API.get('/api/notifications/unread-count');
      if (data) this.unreadCount = data.count || 0;
    },

    init() {
      this.fetchUnreadCount();
      this._pollInterval = setInterval(() => this.fetchUnreadCount(), 30000);
    },
  };
}

// ─── Global helpers ────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(8px)';
    el.style.transition = 'all 0.2s ease';
    setTimeout(() => el.remove(), 200);
  }, 2800);
}
