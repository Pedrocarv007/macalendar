function ticketsPage() {
  return {
    tickets: [], showCreate: false, statusFilter: '',
    form: { subject: '', message: '', category: 'bug', priority: 'medium', screenshot: null },

    async init() { await this.load(); },
    async load() {
      const params = new URLSearchParams();
      if (this.statusFilter) params.set('status', this.statusFilter);
      const data = await API.get(`/api/tickets/?${params}`);
      this.tickets = data?.results || data || [];
    },

    async submit() {
      const fd = new FormData();
      fd.append('subject', this.form.subject);
      fd.append('message', this.form.message);
      fd.append('category', this.form.category);
      fd.append('priority', this.form.priority);
      if (this.form.screenshot) fd.append('screenshot', this.form.screenshot);
      const data = await API.upload('/api/tickets/', fd);
      if (data) { this.showCreate = false; this.load(); toast('Ticket submetido'); }
      else toast('Erro', 'error');
    },
  };
}
