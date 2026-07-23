/** Estado global e cliente da API do MC. */

// Token de proteção dos formulários
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrftoken"]');
  if (meta) return meta.getAttribute('content');
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

// Perfis de acesso
const USER_ROLE = document.querySelector('meta[name="user-role"]')?.getAttribute('content') || '';
const USER_RESTAURANT_ID = document.querySelector('meta[name="user-restaurant-id"]')?.getAttribute('content') || '';
const _SUPER_ROLES = ['admin', 'rh', 'marketing'];
const _MANAGER_ROLES = ['admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno'];
function isSuperRole() { return _SUPER_ROLES.includes(USER_ROLE); }
function isManagerOrAbove() { return _MANAGER_ROLES.includes(USER_ROLE); }

// Cliente da API
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
      if (data && typeof data === 'object') {
        Object.defineProperty(data, '_httpOk', {
          value: res.ok,
          enumerable: false,
          configurable: true,
        });
        Object.defineProperty(data, '_httpStatus', {
          value: res.status,
          enumerable: false,
          configurable: true,
        });
      }
      if (!res.ok) {
        console.error('Erro da API:', res.status, data);
      }
      return data;
    } catch (err) {
      console.error('Erro de rede:', err);
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

// Estado global da interface
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

// Funções auxiliares
function firstErrorDetail(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return firstErrorDetail(value[0]);
  if (typeof value === 'object') {
    for (const detail of Object.values(value)) {
      const message = firstErrorDetail(detail);
      if (message) return message;
    }
  }
  return '';
}

function apiError(data) {
  if (data === null || data === undefined) {
    return 'Não foi possível comunicar com o sistema. Tente novamente.';
  }
  if (data?._httpOk !== false && !data?.error && !data?.erro) return '';
  return (
    firstErrorDetail(data?.error) ||
    firstErrorDetail(data?.erro) ||
    firstErrorDetail(data?.detail) ||
    firstErrorDetail(data?.details) ||
    'Não foi possível concluir a operação.'
  );
}

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
