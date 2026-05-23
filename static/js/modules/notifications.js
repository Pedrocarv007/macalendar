function notificationsPage() {
  return {
    notifications: [],
    async init() { await this.load(); },
    async load() {
      const data = await API.get('/api/notifications/');
      this.notifications = data?.results || data || [];
    },
    async markRead(n) {
      if (n.read_at) return;
      await API.post('/api/notifications/mark-read', { ids: [n.id] });
      n.read_at = new Date().toISOString();
    },
    async markAllRead() {
      await API.post('/api/notifications/mark-read', { ids: [] });
      this.notifications.forEach(n => { if (!n.read_at) n.read_at = new Date().toISOString(); });
    },
  };
}
