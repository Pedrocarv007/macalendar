/**
 * MAC Calendar - Documents Module
 * VERSÃO RESTAURADA E COMPLETA: 
 * - Filtro Local (Instantâneo)
 * - Download em Lote (Thecarv + Sem janela)
 * - Geração de Cartão (Com campos extras Mês/Motivo)
 * - Auto-Reset da Modal ao sair
 */

const DocumentsModule = {
    data: [],
    allEmployees: [], 
    currentUser: null,
    currentView: 'list', 
    currentPage: 1,
    searchTimer: null,
    selectedEmployee: null,

    async init() {
        try {
            this.currentUser = await api.get('/auth/user');
            this.setupHandlers();
            await this.loadDocuments();
            await this.loadRestaurantsForAdmin();
            console.log("🚀 DocumentsModule iniciado com sucesso.");
        } catch (error) {
            console.warn('Erro na inicialização:', error);
        }
    },

    setupHandlers() {
        const self = this;

        // --- HANDLERS DA MODAL DE GERAÇÃO (Limpeza e Carregamento) ---
        const genModal = document.getElementById('generateDocumentModal');
        if (genModal) {
            genModal.addEventListener('show.bs.modal', () => {
                self.loadEmployeesForGeneration();
            });

            genModal.addEventListener('hidden.bs.modal', () => {
                const form = document.getElementById('generateDocumentForm');
                if (form) form.reset();
                document.getElementById('genEmployeeId').value = '';
                document.getElementById('employeeDropdown').style.display = 'none';
                document.getElementById('employeeInfo').style.display = 'none';
                document.getElementById('selectedEmployeeName').style.display = 'none';
                self.selectedEmployee = null;
            });
        }

        // 1. BUSCA DE DOCUMENTOS
        const searchInput = document.getElementById('searchDocument');
        if (searchInput) {
            searchInput.oninput = () => {
                self.currentPage = 1; 
                clearTimeout(self.searchTimer);
                self.searchTimer = setTimeout(() => self.filterAndDisplay(), 300);
            };
        }

        // 2. FILTROS
        ['filterType', 'filterCategory', 'sortBy'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.onchange = () => {
                if (id !== 'sortBy') self.currentPage = 1;
                self.filterAndDisplay();
            };
        });

        // 3. CONTROLES DE VISUALIZAÇÃO E AÇÕES
        document.getElementById('gridViewBtn').onclick = () => self.toggleView('grid');
        document.getElementById('listViewBtn').onclick = () => self.toggleView('list');
        // Botão Selecionar Todos (visual, funciona em ambas as views)
        const gridActionsBtn = document.querySelector('#gridActions button');
        if (gridActionsBtn) gridActionsBtn.onclick = () => self.toggleSelectAll();
        document.getElementById('bulkDownloadBtn').onclick = () => self.downloadSelected();
        document.getElementById('generateAndDownloadBtn').onclick = () => self.generateAndDownloadDocument();

        // 4. PESQUISA DE FUNCIONÁRIOS (Filtro Local)
        const empSearch = document.getElementById('genEmployeeSearch');
        if (empSearch) {
            empSearch.oninput = (e) => self.handleEmployeeSearch(e.target.value.toLowerCase().trim());
        }

        const genType = document.getElementById('genDocumentType');
        if (genType) {
            genType.onchange = (e) => {
                const fields = document.getElementById('employeeOfMonthFields');
                if (fields) fields.style.display = e.target.value === 'funcionario_mes' ? 'block' : 'none';
            };
        }

        // 5. DELEGAÇÃO DE EVENTOS
        const handleActions = (e) => {
            const target = e.target;
            const editBtn = target.closest('.doc-edit-btn');
            const checkbox = target.closest('.doc-check');
            if (editBtn) self.editDocument(editBtn.getAttribute('data-id'));
            if (checkbox) self.updateBulkActionButton();
        };

        document.getElementById('documentsTableBody').onclick = handleActions;
        document.getElementById('documentsGridContainer').onclick = handleActions;

        const docForm = document.getElementById('documentForm');
        if (docForm) docForm.onsubmit = (e) => { e.preventDefault(); self.saveDocument(); };
    },

    // --- LÓGICA DE FUNCIONÁRIOS (RESTAURADA) ---

    async loadEmployeesForGeneration() {
        try {
            const response = await api.get('/employees');
            const employees = (response.employees || []).map(e => ({ ...e, is_worker: false }));
            const workers = (response.workers || []).map(w => ({ ...w, is_worker: true }));
            this.allEmployees = [...employees, ...workers];
        } catch (error) { console.error('Erro colaboradores:', error); }
    },

    handleEmployeeSearch(term) {
        const dropdown = document.getElementById('employeeDropdown');
        if (term.length < 1) { dropdown.style.display = 'none'; return; }

        const filtered = this.allEmployees.filter(emp => 
            emp.name.toLowerCase().includes(term) || (emp.email && emp.email.toLowerCase().includes(term))
        );

        if (filtered.length > 0) {
            dropdown.innerHTML = filtered.map(emp => `
                <button type="button" class="list-group-item list-group-item-action" 
                    onclick='DocumentsModule.selectEmployee(${JSON.stringify(emp).replace(/'/g, "&apos;")})'>
                    <div class="d-flex w-100 justify-content-between align-items-center">
                        <strong>${emp.name}${emp.is_worker ? ' <span class="badge bg-warning text-dark">Worker</span>' : ''}</strong>
                        <small class="text-muted">${emp.role || 'N/A'}</small>
                    </div>
                </button>`).join('');
            dropdown.style.display = 'block';
        } else {
            dropdown.innerHTML = '<div class="list-group-item disabled text-center">Nenhum resultado</div>';
            dropdown.style.display = 'block';
        }
    },

    selectEmployee(emp) {
        this.selectedEmployee = emp;
        document.getElementById('genEmployeeId').value = emp.id;
        document.getElementById('genEmployeeIsWorker').value = emp.is_worker;
        document.getElementById('genEmployeeSearch').value = emp.name;
        document.getElementById('employeeDropdown').style.display = 'none';
        document.getElementById('infoEmployeeName').textContent = emp.name + (emp.is_worker ? ' (Worker)' : '');
        document.getElementById('employeeInfo').style.display = 'block';
        Thecarv.notify(`Selecionado: ${emp.name}`, 'info');
    },

    // --- GERAÇÃO E DOWNLOAD (RESTAURADA E COMPLETA) ---

    async generateAndDownloadDocument() {
        const docType = document.getElementById('genDocumentType').value;
        const employeeId = document.getElementById('genEmployeeId').value;
        const monthYear = document.getElementById('genMonthYear')?.value;
        const reason = document.getElementById('genReason')?.value;

        if (!docType || !employeeId) return Thecarv.notify('Selecione o tipo e o funcionário', 'warning');

        Thecarv.loading('A gerar cartão...');
        try {
            const payload = {
                document_type: docType,
                employee_id: parseInt(employeeId),
                restaurant_id: this.selectedEmployee.restaurant_id,
                is_worker: document.getElementById('genEmployeeIsWorker').value === 'true',
                month_year: monthYear || '',
                reason: reason || ''
            };

            const result = await api.post('/documents/generate-auto', payload);
            
            if (result?.document?.filename) {
                const url = `${window.APP_PREFIX || ''}/uploads/generated/${result.document.filename}`;
                const link = document.createElement('a');
                link.href = url;
                link.download = `cartao_${docType}_${this.selectedEmployee.name.replace(/\s+/g, '_')}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                bootstrap.Modal.getInstance(document.getElementById('generateDocumentModal')).hide();
                await this.loadDocuments();
                Thecarv.notify('Cartão gerado!', 'success');
            }
        } catch (error) { Thecarv.notify('Erro na geração', 'error'); }
        finally { Thecarv.close(); }
    },

    // --- DOCUMENTOS E PAGINAÇÃO ---

    async loadDocuments(queryString = '') {
        const loading = document.getElementById('documentsLoading');
        if (loading) loading.style.display = 'block';
        const params = new URLSearchParams(queryString);
        if (!params.has('page')) params.append('page', this.currentPage);
        try {
            const response = await api.get(`/documents?${params.toString()}`);
            this.data = response.items || [];
            this.render();
            this.updateStats(response);
            this.updatePagination(response);
        } catch (error) { Thecarv.notify('Erro ao carregar', 'error'); }
        finally { if (loading) loading.style.display = 'none'; }
    },

    updatePagination(stats) {
        const container = document.getElementById('paginationControls');
        if (!container || !stats || stats.pages <= 1) { if (container) container.innerHTML = ''; return; }
        container.innerHTML = `
            <button class="btn btn-sm btn-outline-secondary me-2" ${stats.current_page <= 1 ? 'disabled' : ''} onclick="DocumentsModule.changePage(${stats.current_page - 1})">Anterior</button>
            <span class="mx-2 fw-bold text-muted">${stats.current_page} / ${stats.pages}</span>
            <button class="btn btn-sm btn-outline-secondary ms-2" ${stats.current_page >= stats.pages ? 'disabled' : ''} onclick="DocumentsModule.changePage(${stats.current_page + 1})">Próximo</button>`;
    },

    changePage(p) { this.currentPage = p; window.scrollTo({ top: 0, behavior: 'smooth' }); this.filterAndDisplay(); },

   filterAndDisplay() {
    // 1. Pegamos os elementos
    const searchInput = document.getElementById('searchDocument');
    const categorySelect = document.getElementById('filterCategory');
    const restaurantSelect = document.getElementById('filterRestaurant'); // Pode ser null se não for admin
    const sortSelect = document.getElementById('sortBy');

    // 2. Criamos os parâmetros
    const params = new URLSearchParams();
    
    if (searchInput?.value) params.append('search', searchInput.value);
    
    // Só envia o filtro se não for "todos"
    if (categorySelect?.value && categorySelect.value !== 'todos') {
        params.append('document_type', categorySelect.value);
    }

    if (restaurantSelect?.value && restaurantSelect.value !== 'todos') {
        params.append('restaurant_id', restaurantSelect.value);
    }

    params.append('sortBy', sortSelect?.value || 'upload_date');
    params.append('page', this.currentPage || 1);

    // 3. Chama o carregamento com a string formatada: ?search=...&document_type=...
    this.loadDocuments(params.toString());
    this.updateStats()
},

        async clearFilters() {
        // 1. Limpa os valores dos campos
        if (document.getElementById('filterRestaurant')) document.getElementById('filterRestaurant').value = 'todos';
        if (document.getElementById('filterCategory')) document.getElementById('filterCategory').value = 'todos';
        if (document.getElementById('searchDocument')) document.getElementById('searchDocument').value = '';
        
        // 2. Reseta a página para a primeira
        this.currentPage = 1; 
        
        // 3. Atualiza a exibição
        await this.filterAndDisplay();
    },
    // Chame esta função no init() para carregar os restaurantes se for Admin
    async loadRestaurantsForAdmin() {
        const select = document.getElementById('filterRestaurant');
        if (!select) return; // Se não existe o campo, não é admin

        try {
            const response = await api.get('/restaurants'); // Rota que você deve ter no Python
            // response deve ser uma lista de {id, name}
           const lista = response.restaurants || [];

        lista.forEach(res => {
            const opt = document.createElement('option');
            opt.value = res.id;
            opt.textContent = res.name;
            select.appendChild(opt);
        });
            
        } catch (error) {
            Thecarv.notify("Erro ao carregar lista de restaurantes", 'error');
        }
    },

        render() {
        const container = document.getElementById(this.currentView === 'list' ? 'documentsTableBody' : 'documentsGridContainer');
        const noResults = document.getElementById('noDocuments');
        document.getElementById('documentsList').style.display = this.currentView === 'list' ? '' : 'none';
        document.getElementById('documentsGrid').style.display = this.currentView === 'grid' ? '' : 'none';

        if (this.data.length === 0) {
            if (noResults) noResults.style.display = 'block';
            if (container) container.innerHTML = '';
            return;
        }
        if (noResults) noResults.style.display = 'none';
        container.innerHTML = this.data.map(doc => this.currentView === 'list' ? this.templateRow(doc) : this.templateCard(doc)).join('');
        this.updateBulkActionButton();
    },

    templateRow(doc) {
        return `<tr>
            <td><input type="checkbox" class="doc-check form-check-input" value="${doc.id}"></td>
            <td><div class="d-flex align-items-center"><i class="fas ${Utils.getFileIcon(doc.filename)} me-2 text-${Utils.getFileColor(doc.filename)}"></i>
            <div><strong>${doc.title}</strong><br><small class="text-muted">${Utils.truncate(doc.description, 40)}</small></div></div></td>
            <td><span class="badge bg-${Utils.getFileColor(doc.filename)}">${Utils.getFileTypeLabel(doc.filename)}</span></td>
            <td><span class="badge bg-${Utils.getFileColor(doc.filename)}">${doc.document_type}</span></td>
            <td>${Utils.formatFileSize(doc.file_size)}</td>
            <td>${Utils.formatDate(new Date(doc.created_at))}</td>
            <td><div class="btn-group">
                <button class="btn btn-sm btn-outline-primary" onclick="DocumentsModule.download(${doc.id})"><i class="fas fa-download"></i></button>
                <button class="btn btn-sm btn-outline-warning doc-edit-btn" data-id="${doc.id}"><i class="fas fa-edit"></i></button>
            </div></td>
        </tr>`;
    },

    templateCard(doc) {
        const color = Utils.getFileColor(doc.filename);
        return `<div class="col-md-4 col-lg-3 mb-4">
            <div class="card h-100 shadow-sm border-top border-${color} border-4">
                <div class="position-absolute top-0 end-0 p-2"><input type="checkbox" class="doc-check form-check-input" value="${doc.id}"></div>
                <div class="card-body text-center">
                    <i class="fas ${Utils.getFileIcon(doc.filename)} fa-3x text-${color} mb-3"></i>
                    <h6 class="card-title text-truncate">${doc.title}</h6>
                    <span class="badge bg-${color} mb-3">${doc.document_type}</span>
                    <div class="btn-group w-100">
                        <button class="btn btn-sm btn-outline-primary" onclick="DocumentsModule.download(${doc.id})"><i class="fas fa-download"></i></button>
                        <button class="btn btn-sm btn-outline-warning doc-edit-btn" data-id="${doc.id}"><i class="fas fa-edit"></i></button>
                    </div>
                </div>
            </div>
        </div>`;
    },

    updateStats(response) {
        if (!response) return;
        
        // Mapeamento manual para evitar erros de substituição de string
        const mapeamento = {
            'totalDocuments': response.total || 0,
            'pdfCount': response.pdf || 0,
            'imageCount': response.fotos || response.image || 0 // Tenta 'fotos' ou 'image'
        };

        Object.keys(mapeamento).forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = mapeamento[id];
        });
            // Atualiza o tamanho total
            const elSize = document.getElementById('totalSize');
            if (elSize) {
                const totalSize = (this.data || []).reduce((acc, doc) => acc + (doc.file_size || 0), 0);
                elSize.textContent = Utils.formatFileSize(totalSize);
            }
        },

    toggleView(view) {
        this.currentView = view;
        const btnGrid = document.getElementById('gridViewBtn');
        const btnList = document.getElementById('listViewBtn');
        const gridActions = document.getElementById('gridActions');
        btnGrid?.classList.toggle('btn-primary', view === 'grid');
        btnGrid?.classList.toggle('btn-outline-primary', view !== 'grid');
        btnList?.classList.toggle('btn-primary', view === 'list');
        btnList?.classList.toggle('btn-outline-primary', view !== 'list');
        if (gridActions) gridActions.style.display = view === 'grid' ? 'block' : 'none';
        this.render();
    },

    download(id) {
        const link = document.createElement('a');
        link.href = `${window.API_BASE_URL}/documents/${id}/download`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    toggleSelectAll() {
        // Alterna seleção de todos os checkboxes
        const allChecks = document.querySelectorAll('.doc-check');
        const allChecked = Array.from(allChecks).every(cb => cb.checked);
        allChecks.forEach(cb => cb.checked = !allChecked);
        this.updateBulkActionButton();

        // Atualiza cor do botão Selecionar Todos
        const gridActionsBtn = document.querySelector('#gridActions button');
        if (gridActionsBtn) {
            if (!allChecked) {
                gridActionsBtn.classList.remove('btn-outline-secondary');
                gridActionsBtn.classList.add('btn-primary');
            } else {
                gridActionsBtn.classList.remove('btn-primary');
                gridActionsBtn.classList.add('btn-outline-secondary');
            }
        }
    },

    updateBulkActionButton() {
        const selected = document.querySelectorAll('.doc-check:checked').length;
        const btn = document.getElementById('bulkDownloadBtn');
        if (btn) {
            btn.disabled = selected === 0;
            btn.innerHTML = `<i class="fas fa-download me-1"></i>Download (${selected})`;
        }
    },

    async downloadSelected() {
        const ids = Array.from(document.querySelectorAll('.doc-check:checked')).map(cb => cb.value);
        if (ids.length === 0) return;
        window.location.href = `${window.API_BASE_URL}/documents/bulk-download?ids=${ids.join(',')}`;
    },

    async saveDocument() {
        const formData = new FormData(document.getElementById('documentForm'));
        const docId = document.getElementById('documentId').value;
        Thecarv.loading('A guardar...');
        try {
            if (docId) await api.put(`/documents/${docId}`, formData);
            else await api.post('/documents', formData);
            Thecarv.notify('Salvo!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('documentModal')).hide();
            await this.loadDocuments();
        } catch (e) { Thecarv.notify('Erro ao salvar', 'error'); }
    },

    async editDocument(id) {
        const doc = this.data.find(d => String(d.id) === String(id));
        if (!doc) return;
        document.getElementById('documentId').value = doc.id;
        document.getElementById('documentName').value = doc.title || '';
        document.getElementById('documentCategory').value = doc.document_type || '';
        document.getElementById('documentModalTitle').textContent = 'Editar Documento';
        new bootstrap.Modal(document.getElementById('documentModal')).show();
    }
};

document.addEventListener('DOMContentLoaded', () => DocumentsModule.init());