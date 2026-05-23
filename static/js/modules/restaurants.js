function restaurantsPage() {
  return {
    restaurants: [], showModal: false, editId: null,
    form: { name: '', address: '', phone: '', email: '', capacity: '', opening_hours: '' },

    async init() { await this.load(); },
    async load() {
      const data = await API.get('/api/restaurants/');
      this.restaurants = data?.results || data || [];
    },

    openCreate() { this.editId = null; this.form = { name: '', address: '', phone: '', email: '', capacity: '', opening_hours: '' }; this.showModal = true; },
    openEdit(r) { this.editId = r.id; this.form = { name: r.name, address: r.address, phone: r.phone, email: r.email, capacity: r.capacity, opening_hours: r.opening_hours }; this.showModal = true; },

    async save() {
      const url = this.editId ? `/api/restaurants/${this.editId}` : '/api/restaurants/';
      const method = this.editId ? 'put' : 'post';
      const data = await API[method](url, this.form);
      if (data?.id || data) { this.showModal = false; this.load(); toast('Guardado'); }
      else toast('Erro', 'error');
    },
  };
}
