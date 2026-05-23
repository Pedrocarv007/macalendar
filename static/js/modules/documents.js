function documentsPage() {
  return {
    documents: [], search: '', typeFilter: '',
    showUpload: false, showGenerator: false, showPreview: false,
    previewUrl: null,
    employees: [], workers: [], restaurants: [],
    uploadForm: { title: '', document_type: 'memo', file: null },
    genForm: {
      template: 'birthday',
      person_type: 'employee',
      employee_id: '',
      worker_id: '',
      restaurant_id: '',
      message: '',
    },

    async init() {
      await this.load();
      // Load people lists for the generator
      const [empData, wrkData, resData] = await Promise.all([
        API.get('/api/employees/'),
        API.get('/api/workers/'),
        API.get('/api/restaurants/'),
      ]);
      this.employees = empData?.data || [];
      this.workers = Array.isArray(wrkData) ? wrkData : (wrkData?.results || []);
      this.restaurants = resData?.results || [];
    },

    async load() {
      const params = new URLSearchParams();
      if (this.search) params.set('search', this.search);
      if (this.typeFilter) params.set('type', this.typeFilter);
      const data = await API.get(`/api/documents/?${params}`);
      this.documents = data?.results || data || [];
    },

    openUpload() {
      this.uploadForm = { title: '', document_type: 'memo', file: null };
      this.showUpload = true;
    },

    openGenerator() {
      this.genForm = { template: 'birthday', person_type: 'employee', employee_id: '', worker_id: '', restaurant_id: '', message: '' };
      this.showGenerator = true;
    },

    async upload() {
      const fd = new FormData();
      fd.append('title', this.uploadForm.title);
      fd.append('document_type', this.uploadForm.document_type);
      if (this.uploadForm.file) fd.append('file', this.uploadForm.file);
      const data = await API.upload('/api/documents/', fd);
      if (data) { this.showUpload = false; this.load(); toast('Documento carregado'); }
      else toast('Erro no upload', 'error');
    },

    async generate() {
      const payload = { ...this.genForm };
      const data = await API.post('/api/documents/generate', payload);
      if (data?.id) {
        this.showGenerator = false;
        this.load();
        toast('Documento gerado com sucesso');
        // Show preview
        if (data.file_url) {
          this.previewUrl = data.file_url;
          this.showPreview = true;
        }
      } else {
        toast(data?.error || 'Erro na geração', 'error');
      }
    },

    async deleteDoc(id) {
      if (!confirm('Apagar este documento?')) return;
      await API.delete(`/api/documents/${id}`);
      this.load();
      toast('Apagado');
    },

    templateLabel(t) {
      return { birthday: 'Aniversário', welcome: 'Boas-Vindas', employee_month: 'Funcionário do Mês' }[t] || t;
    },
  };
}
