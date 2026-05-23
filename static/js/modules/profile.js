function profilePage() {
  return {
    user: {}, form: {}, settings: {},

    async init() {
      const data = await API.get('/api/auth/me');
      this.user = data?.data || {};
      this.form = { name: this.user.name, phone: this.user.phone, address: this.user.address, birth_date: this.user.birth_date };
      this.settings = this.user.settings || {};
    },

    async save() {
      const data = await API.put('/api/auth/profile', this.form);
      if (data?.success) toast('Perfil actualizado');
      else toast('Erro', 'error');
    },

    async saveSettings() {
      await API.put('/api/auth/profile', { settings: this.settings });
    },

    async uploadPhoto(event) {
      const file = event.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('photo', file);
      const data = await API.upload(`/api/employees/${this.user.id}/photo`, fd);
      if (data?.data?.photo_url) { this.user.photo_url = data.data.photo_url; toast('Foto actualizada'); }
      else toast('Erro no upload', 'error');
    },
  };
}
