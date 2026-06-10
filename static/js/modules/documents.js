function documentsPage() {
  return {
    documents: [], search: '', typeFilter: '',
    activeFolder: 'all',
    showUpload: false, showGenerator: false, showPreview: false,
    showPicker: false, pickerSearch: '', selectedPerson: null,
    previewUrl: null,
    employees: [], workers: [], restaurants: [],
    folders: [
      {
        key: 'all',
        label: 'Tudo',
        description: 'Visão completa da biblioteca com todos os tipos de documento.',
        types: [],
        badgeClass: 'badge-gray',
        accentClass: 'is-all',
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M3 7h5l2 2h11v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>',
      },
      {
        key: 'birthday',
        label: 'Aniversários',
        description: 'Cartões de aniversário gerados para colaboradores e funcionários.',
        types: ['birthday'],
        badgeClass: 'badge-orange',
        accentClass: 'is-birthday',
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M12 7v13m-5-8v8m10-8v8M7 7h10l-1 13H8L7 7zm4.5-3.5C10.7 2.7 9 3.3 9 5c0 1 .8 2 3 2 2.2 0 3-1 3-2 0-1.7-1.7-2.3-2.5-1.5L12 4l-.5-.5z"/></svg>',
      },
      {
        key: 'employee_month',
        label: 'Funcionário do Mês',
        description: 'Materiais de destaque mensal para equipas e restaurantes.',
        types: ['employee_month'],
        badgeClass: 'badge-gold',
        accentClass: 'is-employee-month',
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M12 3l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 15.8 7.2 18l.9-5.4L4.2 8.7l5.4-.8L12 3z"/></svg>',
      },
      {
        key: 'uploads',
        label: 'Uploads',
        description: 'Ficheiros carregados manualmente como memorandos, fotos e certificados.',
        types: ['memo', 'photo', 'certificate', 'other'],
        badgeClass: 'badge-blue',
        accentClass: 'is-upload',
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M12 16V4m0 0l-4 4m4-4l4 4M5 20h14"/></svg>',
      },
    ],
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
      const data = await API.get(`/api/documents/?${params}`);
      this.documents = data?.results || data || [];
    },

    filteredDocuments() {
      let items = this.documents;
      if (this.activeFolder !== 'all') {
        const folder = this.folders.find(item => item.key === this.activeFolder);
        const allowedTypes = folder?.types || [];
        items = items.filter(doc => allowedTypes.includes(doc.document_type));
      }
      if (this.typeFilter) {
        items = items.filter(doc => doc.document_type === this.typeFilter);
      }
      return items;
    },

    folderCount(folderKey) {
      if (folderKey === 'all') return this.documents.length;
      const folder = this.folders.find(item => item.key === folderKey);
      const allowedTypes = folder?.types || [];
      return this.documents.filter(doc => allowedTypes.includes(doc.document_type)).length;
    },

    selectFolder(folderKey) {
      this.activeFolder = folderKey;
      if (folderKey === 'all') {
        this.typeFilter = '';
        return;
      }
      const folder = this.folders.find(item => item.key === folderKey);
      if (!folder || folder.types.length !== 1) {
        this.typeFilter = '';
        return;
      }
      this.typeFilter = folder.types[0];
    },

    onTypeFilterChange() {
      if (!this.typeFilter) {
        this.activeFolder = 'all';
        return;
      }
      const exactFolder = this.folders.find(folder => folder.types.length === 1 && folder.types[0] === this.typeFilter);
      this.activeFolder = exactFolder?.key || 'uploads';
    },

    activeCategoryLabel() {
      if (this.typeFilter) return this.templateLabel(this.typeFilter);
      const folder = this.folders.find(item => item.key === this.activeFolder);
      return folder?.label || 'Tudo';
    },

    openUpload() {
      this.uploadForm = { title: '', document_type: 'memo', file: null };
      this.showUpload = true;
    },

    openGenerator() {
      this.genForm = { template: 'birthday', person_type: 'employee', employee_id: '', worker_id: '', restaurant_id: '', message: '' };
      this.selectedPerson = null;
      this.showGenerator = true;
    },

    // ── Picker ───────────────────────────────────────────────────────────────

    openPicker() {
      this.pickerSearch = '';
      this.showPicker = true;
    },

    peopleList() {
      const list = this.genForm.person_type === 'employee' ? this.employees : this.workers;
      const q = this.pickerSearch.trim().toLowerCase();
      if (!q) return list;
      return list.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.restaurant_name || '').toLowerCase().includes(q)
      );
    },

    pickPerson(person) {
      this.selectedPerson = person;
      if (this.genForm.person_type === 'employee') {
        this.genForm.employee_id = person.id;
        this.genForm.worker_id = '';
      } else {
        this.genForm.worker_id = person.id;
        this.genForm.employee_id = '';
      }
      this.showPicker = false;
    },

    switchPersonType(type) {
      this.genForm.person_type = type;
      // Resetar seleção ao trocar de tipo
      this.selectedPerson = null;
      this.genForm.employee_id = '';
      this.genForm.worker_id = '';
    },

    // ── Upload / Generate ────────────────────────────────────────────────────

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
      return {
        birthday: 'Aniversário',
        welcome: 'Boas-Vindas',
        employee_month: 'Funcionário do Mês',
        memo: 'Memorando',
        photo: 'Foto',
        certificate: 'Certificado',
        other: 'Outro',
      }[t] || t;
    },
  };
}
