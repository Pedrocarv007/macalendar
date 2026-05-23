function employeesPage() {
  return {
    employees: [], showModal: false, editId: null,
    search: '', roleFilter: '',
    isManager: isManagerOrAbove(),
    photoPreview: '/static/img/default-avatar.png',
    photoUploading: false,
    form: { name: '', email: '', phone: '', role: 'employee', position: '', birth_date: '', hire_date: '', password: '' },

    async init() { await this.load(); },

    async load() {
      const params = new URLSearchParams();
      if (this.search) params.set('search', this.search);
      if (this.roleFilter) params.set('role', this.roleFilter);
      const data = await API.get(`/api/employees/?${params}`);
      this.employees = data?.data || [];
    },

    openCreate() {
      this.editId = null;
      this.photoPreview = '/static/img/default-avatar.png';
      this.form = { name: '', email: '', phone: '', role: 'employee', position: '', birth_date: '', hire_date: '', password: '' };
      this.showModal = true;
    },

    openEdit(emp) {
      this.editId = emp.id;
      this.photoPreview = emp.photo_url || '/static/img/default-avatar.png';
      this.form = { name: emp.name, email: emp.email, phone: emp.phone || '', role: emp.role,
        position: emp.position || '', birth_date: emp.birth_date || '', hire_date: emp.hire_date || '', password: '' };
      this.showModal = true;
    },

    async save() {
      const url = this.editId ? `/api/employees/${this.editId}` : '/api/employees/';
      const method = this.editId ? 'put' : 'post';
      const body = { ...this.form };
      if (!body.password) delete body.password;
      const data = await API[method](url, body);
      if (data?.success !== false) { this.showModal = false; this.load(); toast('Guardado'); }
      else toast(data.error || 'Erro', 'error');
    },

    async uploadPhoto(event) {
      const file = event.target.files[0];
      if (!file || !this.editId) return;
      this.photoUploading = true;
      const fd = new FormData();
      fd.append('photo', file);
      const res = await API.upload(`/api/employees/${this.editId}/photo`, fd);
      this.photoUploading = false;
      if (res?.data?.photo_url) {
        this.photoPreview = res.data.photo_url + '?t=' + Date.now();
        const idx = this.employees.findIndex(e => e.id === this.editId);
        if (idx !== -1) this.employees[idx].photo_url = this.photoPreview;
        toast('Foto atualizada.');
      } else {
        toast('Erro ao carregar foto.', 'error');
      }
      event.target.value = '';
    },
  };
}
