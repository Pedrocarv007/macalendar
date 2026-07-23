function documentsPage() {
  return {
    documents: [],
    search: '',
    typeFilter: '',
    activeFolder: 'all',
    folders: [],
    templateCatalog: [],
    showUpload: false,
    showGenerator: false,
    showPreview: false,
    showPicker: false,
    pickerSearch: '',
    selectedPerson: null,
    selectedPhotoBroken: false,
    selectedPhotoAvailable: null,
    selectedPhotoPreview: '',
    previewUrl: null,
    previewDownloadUrl: null,
    previewTitle: '',
    previewLoading: false,
    previewError: false,
    workers: [],
    restaurants: [],
    generating: false,
    uploading: false,
    uploadForm: {
      title: '',
      document_type: 'memo',
      restaurant: '',
      file: null,
    },
    genForm: {
      template: 'birthday',
      person_type: 'worker',
      employee_id: '',
      worker_id: '',
      restaurant_id: '',
      message: '',
      photoFile: null,
    },

    async init() {
      const [documentsData, templateData, workerData, restaurantData] = await Promise.all([
        API.get('/api/documents/'),
        API.get('/api/documents/templates'),
        API.get('/api/workers/'),
        API.get('/api/restaurants/'),
      ]);

      this.documents = documentsData?.results || documentsData || [];
      this.templateCatalog = templateData?.modelos || this.fallbackTemplates();
      this.workers = Array.isArray(workerData) ? workerData : (workerData?.results || []);
      this.restaurants = restaurantData?.results || restaurantData || [];
      this.buildFolders();
    },

    fallbackTemplates() {
      return [
        { key: 'birthday', label: 'Aniversário', description: 'Cartão de aniversário do colaborador.', accent: '#FFBC0D' },
        { key: 'welcome', label: 'Boas-vindas', description: 'Cartão de acolhimento para novas pessoas.', accent: '#2D2D2D' },
        { key: 'employee_month', label: 'Funcionário do Mês', description: 'Destaque mensal de um membro da equipa.', accent: '#FFBC0D' },
      ];
    },

    buildFolders() {
      const folderNames = {
        birthday: 'Aniversários',
        welcome: 'Boas-vindas',
        employee_month: 'Funcionário do Mês',
      };
      const badgeClasses = {
        birthday: 'badge-gold',
        welcome: 'badge-green',
        employee_month: 'badge-gold',
      };
      const accentClasses = {
        birthday: 'is-birthday',
        welcome: 'is-welcome',
        employee_month: 'is-employee-month',
      };
      const iconPaths = {
        birthday: 'M12 7v13m-5-8v8m10-8v8M7 7h10l-1 13H8L7 7zm4.5-3.5C10.7 2.7 9 3.3 9 5c0 1 .8 2 3 2 2.2 0 3-1 3-2 0-1.7-1.7-2.3-2.5-1.5L12 4l-.5-.5z',
        welcome: 'M4 5h16v14H4V5zm4 4h8m-8 4h5',
        employee_month: 'M12 3l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 15.8 7.2 18l.9-5.4L4.2 8.7l5.4-.8L12 3z',
      };

      const generatedFolders = this.templateCatalog.map(template => ({
        key: template.key,
        label: folderNames[template.key] || template.label,
        description: template.description,
        types: [template.key],
        badgeClass: badgeClasses[template.key] || 'badge-gray',
        accentClass: accentClasses[template.key] || '',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="${iconPaths[template.key] || 'M4 5h16v14H4V5z'}"/></svg>`,
      }));

      this.folders = [
        {
          key: 'all',
          label: 'Tudo',
          description: 'Biblioteca completa de templates e documentos.',
          types: [],
          badgeClass: 'badge-gray',
          accentClass: 'is-all',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M3 7h5l2 2h11v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>',
        },
        ...generatedFolders,
        {
          key: 'uploads',
          label: 'Ficheiros carregados',
          description: 'Memorandos, fotografias, certificados e outros ficheiros.',
          types: ['memo', 'photo', 'certificate', 'other'],
          badgeClass: 'badge-blue',
          accentClass: 'is-upload',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M12 16V4m0 0l-4 4m4-4l4 4M5 20h14"/></svg>',
        },
      ];
    },

    async load() {
      const params = new URLSearchParams();
      if (this.search) params.set('search', this.search);
      const data = await API.get(`/api/documents/?${params}`);
      const error = apiError(data);
      if (error) {
        toast(error, 'error');
        return;
      }
      this.documents = data?.results || data || [];
    },

    canPreview(doc) {
      return ['.png', '.jpg', '.jpeg', '.webp'].includes(
        String(doc?.file_extension || '').toLocaleLowerCase('pt-PT'),
      );
    },

    openPreview({ url, downloadUrl = '', title = '' }) {
      this.previewUrl = url;
      this.previewDownloadUrl = downloadUrl || url;
      this.previewTitle = title;
      this.previewLoading = true;
      this.previewError = false;
      this.showPreview = true;
    },

    openDocumentPreview(doc) {
      if (!this.canPreview(doc)) return;
      this.openPreview({
        url: `/api/documents/${doc.id}/view`,
        downloadUrl: `/api/documents/${doc.id}/download`,
        title: doc.title,
      });
    },

    closePreview() {
      this.showPreview = false;
      this.previewLoading = false;
      this.previewError = false;
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
      const folder = this.folders.find(item => item.key === folderKey);
      this.typeFilter = folder?.types?.length === 1 ? folder.types[0] : '';
    },

    onTypeFilterChange() {
      if (!this.typeFilter) {
        this.activeFolder = 'all';
        return;
      }
      const exactFolder = this.folders.find(folder => (
        folder.types.length === 1 && folder.types[0] === this.typeFilter
      ));
      this.activeFolder = exactFolder?.key || 'uploads';
    },

    activeCategoryLabel() {
      if (this.typeFilter) return this.templateLabel(this.typeFilter);
      return this.folders.find(item => item.key === this.activeFolder)?.label || 'Tudo';
    },

    resultsLabel() {
      const count = this.filteredDocuments().length;
      return `${count} ${count === 1 ? 'resultado' : 'resultados'}`;
    },

    openUpload() {
      this.uploadForm = {
        title: '',
        document_type: 'memo',
        restaurant: USER_RESTAURANT_ID || '',
        file: null,
      };
      this.showUpload = true;
    },

    openGenerator() {
      const defaultTemplate = this.templateCatalog[0]?.key || 'birthday';
      this.genForm = {
        template: defaultTemplate,
        person_type: 'worker',
        employee_id: '',
        worker_id: '',
        restaurant_id: USER_RESTAURANT_ID || '',
        message: this.currentMonthLabel(),
        photoFile: null,
      };
      this.selectedPerson = null;
      this.selectedPhotoBroken = false;
      this.selectedPhotoAvailable = null;
      this.clearSelectedPhotoPreview();
      this.showGenerator = true;
    },

    currentMonthLabel() {
      const text = new Intl.DateTimeFormat('pt-PT', {
        month: 'long',
        year: 'numeric',
      }).format(new Date());
      return text.charAt(0).toUpperCase() + text.slice(1);
    },

    openPicker() {
      this.pickerSearch = '';
      this.showPicker = true;
    },

    peopleList() {
      const list = this.workers;
      const query = this.pickerSearch.trim().toLocaleLowerCase('pt-PT');
      if (!query) return list;
      return list.filter(person => (
        (person.name || '').toLocaleLowerCase('pt-PT').includes(query)
        || (person.restaurant_name || '').toLocaleLowerCase('pt-PT').includes(query)
      ));
    },

    async pickPerson(person) {
      this.selectedPerson = person;
      this.selectedPhotoBroken = false;
      this.selectedPhotoAvailable = null;
      this.clearSelectedPhotoPreview();
      this.genForm.worker_id = person.id;
      this.genForm.employee_id = '';
      this.genForm.photoFile = null;
      this.showPicker = false;
      await this.validateSelectedPhoto();
    },

    selectedPhotoUrl() {
      return this.selectedPhotoPreview || this.selectedPerson?.photo_url || '';
    },

    handlePhotoChange(event) {
      const file = event.target.files?.[0] || null;
      this.genForm.photoFile = file;
      this.selectedPhotoBroken = false;
      this.selectedPhotoAvailable = file ? true : this.selectedPhotoAvailable;
      this.clearSelectedPhotoPreview();
      if (file) this.selectedPhotoPreview = URL.createObjectURL(file);
    },

    clearSelectedPhotoPreview() {
      if (this.selectedPhotoPreview?.startsWith('blob:')) {
        URL.revokeObjectURL(this.selectedPhotoPreview);
      }
      this.selectedPhotoPreview = '';
    },

    async validateSelectedPhoto() {
      if (!this.selectedPerson) {
        this.selectedPhotoAvailable = null;
        return;
      }
      const params = new URLSearchParams();
      params.set('worker_id', this.selectedPerson.id);
      const result = await API.get(`/api/documents/photo-status?${params}`);
      if (apiError(result)) {
        this.selectedPhotoAvailable = false;
        return;
      }
      this.selectedPhotoAvailable = Boolean(result.available);
      this.selectedPhotoBroken = !result.available;
    },

    async uploadSelectedPhoto() {
      if (!this.genForm.photoFile || !this.selectedPerson) return true;
      const personId = this.selectedPerson.id;
      const url = `/api/workers/${personId}/photo/`;
      const formData = new FormData();
      formData.append('photo', this.genForm.photoFile);
      const result = await API.upload(url, formData);
      const error = apiError(result);
      if (error) {
        toast(`Não foi possível guardar a fotografia: ${error}`, 'error');
        return false;
      }

      const photoUrl = result?.data?.photo_url || result?.photo_url;
      if (photoUrl) this.selectedPerson.photo_url = photoUrl;
      this.genForm.photoFile = null;
      this.selectedPhotoBroken = false;
      this.selectedPhotoAvailable = true;
      this.clearSelectedPhotoPreview();
      toast('Fotografia atualizada.');
      return true;
    },

    async upload() {
      if (!this.uploadForm.title.trim()) {
        toast('Indique o título do documento.', 'error');
        return;
      }
      if (!this.uploadForm.file) {
        toast('Selecione o ficheiro a carregar.', 'error');
        return;
      }
      if (!this.uploadForm.restaurant) {
        toast('Selecione o restaurante.', 'error');
        return;
      }

      this.uploading = true;
      try {
        const formData = new FormData();
        formData.append('title', this.uploadForm.title);
        formData.append('document_type', this.uploadForm.document_type);
        formData.append('restaurant', this.uploadForm.restaurant);
        formData.append('file', this.uploadForm.file);
        const data = await API.upload('/api/documents/', formData);
        const error = apiError(data);
        if (error) {
          toast(error, 'error');
          return;
        }
        this.showUpload = false;
        await this.load();
        toast('Documento carregado.');
      } finally {
        this.uploading = false;
      }
    },

    async generate() {
      if (!this.selectedPerson) {
        toast('Selecione a pessoa do cartão.', 'error');
        return;
      }
      if (!this.genForm.restaurant_id) {
        toast('Selecione o restaurante.', 'error');
        return;
      }

      this.generating = true;
      try {
        if (!(await this.uploadSelectedPhoto())) return;
        const payload = { ...this.genForm };
        delete payload.photoFile;
        const data = await API.post('/api/documents/generate', payload);
        const error = apiError(data);
        if (error) {
          toast(error, 'error');
          return;
        }
        this.showGenerator = false;
        await this.load();
        toast('Template gerado com sucesso.');
        if (data.file_url) {
          this.openPreview({
            url: data.file_url,
            downloadUrl: data.id ? `/api/documents/${data.id}/download` : data.file_url,
            title: data.title || 'Template gerado',
          });
        }
      } finally {
        this.generating = false;
      }
    },

    async deleteDoc(id) {
      if (!confirm('Apagar este documento?')) return;
      const data = await API.delete(`/api/documents/${id}`);
      const error = apiError(data);
      if (error) {
        toast(error, 'error');
        return;
      }
      await this.load();
      toast('Documento apagado.');
    },

    templateLabel(type) {
      const configured = this.templateCatalog.find(template => template.key === type);
      if (configured) return configured.label;
      return {
        memo: 'Memorando',
        photo: 'Fotografia',
        certificate: 'Certificado',
        other: 'Outro',
      }[type] || 'Documento';
    },
  };
}
