/**
 * MAC Calendar - Documents Module
 * VERSÃO RESTAURADA: Stats, Filtros e templateRow originais garantidos + Correção de Paginação.
 */

const DocumentsModule = {
    data: [],
    filteredData: [],
    currentUser: null,
    currentView: 'list', 
    allEmployees: [],
    selectedEmployee: null,
    searchTimer: null,
    currentPage: 1, // Página atual controlada pelo módulo

    async init() {
        try {
            this.currentUser = await api.get('/auth/user');
            this.setupHandlers();
            await this.loadDocuments();
            console.log("🚀 DocumentsModule iniciado com sucesso.");
        } catch (error) {
            console.warn('Erro na inicialização:', error);
        }
    },

    setupHandlers() {
        // 1. BUSCA (Debounce)
        const searchInput = document.getElementById('searchDocument');
        if (searchInput) {
            searchInput.oninput = () => {
                DocumentsModule.currentPage = 1; 
                clearTimeout(DocumentsModule.searchTimer);
                DocumentsModule.searchTimer = setTimeout(() => DocumentsModule.filterAndDisplay(), 300);
            };
        }

        // 2. FILTROS (Restaurados um a um para não haver erro de ID)
        const fType = document.getElementById('filterType');
        if (fType) {
            fType.onchange = () => {
                DocumentsModule.currentPage = 1;
                DocumentsModule.filterAndDisplay();
            };
        }

        const fCat = document.getElementById('filterCategory');
        if (fCat) {
            fCat.onchange = () => {
                DocumentsModule.currentPage = 1;
                DocumentsModule.filterAndDisplay();
            };
        }

        const fSort = document.getElementById('sortBy');
        if (fSort) {
            fSort.onchange = () => {
                DocumentsModule.filterAndDisplay();
            };
        }

        // 3. CONTROLES DE VISUALIZAÇÃO
        const gridBtn = document.getElementById('gridViewBtn');
        if (gridBtn) gridBtn.onclick = () => DocumentsModule.toggleView('grid');

        const listBtn = document.getElementById('listViewBtn');
        if (listBtn) listBtn.onclick = () => DocumentsModule.toggleView('list');

        const clearBtn = document.getElementById('clearFiltersBtn');
        if (clearBtn) {
            clearBtn.onclick = () => {
                document.getElementById('searchDocument').value = '';
                document.getElementById('filterType').value = '';
                document.getElementById('filterCategory').value = '';
                document.getElementById('sortBy').value = 'name';
                DocumentsModule.currentPage = 1;
                DocumentsModule.filterAndDisplay();
            };
        }

        // 4. FORMULÁRIO (Protegido com referência direta ao objeto)
        const docForm = document.getElementById('documentForm');
        if (docForm) {
            docForm.onsubmit = function(e) {
                e.preventDefault();
                DocumentsModule.saveDocument();
            };
        }

        // 5. DELEGAÇÃO DE EVENTOS (Tabela e Grid)
        const handleActions = (e) => {
            const target = e.target;
            const editBtn = target.closest('.doc-edit-btn');
            const checkbox = target.closest('.doc-check');
            if (editBtn) DocumentsModule.editDocument(editBtn.getAttribute('data-id'));
            if (checkbox) DocumentsModule.updateBulkActionButton();
        };

        const tableBody = document.getElementById('documentsTableBody');
        const gridContainer = document.getElementById('documentsGridContainer');
        if (tableBody) tableBody.onclick = handleActions;
        if (gridContainer) gridContainer.onclick = handleActions;

        // 6. SELEÇÃO E GERAÇÃO
        const selectAll = document.getElementById('selectAll');
        if (selectAll) selectAll.onchange = () => DocumentsModule.toggleSelectAll();

        const bulkBtn = document.getElementById('bulkDownloadBtn');
        if (bulkBtn) bulkBtn.onclick = () => DocumentsModule.downloadSelected();

        const genBtn = document.getElementById('generateAndDownloadBtn');
        if (genBtn) genBtn.onclick = () => DocumentsModule.generateAndDownloadDocument();
    },

    toggleView(view) {
        this.currentView = view;

        // Controla a visibilidade do botão "Selecionar Todos" do Grid
        const gridActions = document.getElementById('gridActions');
        if (gridActions) {
            // Só mostra se for 'grid'. Se for 'list', esconde porque a tabela já tem o seu checkbox no topo.
            gridActions.style.display = view === 'grid' ? 'block' : 'none';
        }

        this.render();
    },

    async loadDocuments(queryString = '') {
        const loading = document.getElementById('documentsLoading');
        if (loading) loading.style.display = 'block';

        const params = new URLSearchParams(queryString);
        // Garante que a página atual é enviada
        if (!params.has('page')) params.append('page', this.currentPage);

        try {
            const response = await api.get(`/documents?${params.toString()}`);
            this.data = response.documents || [];
            
            this.render();
            // CHAMA AS FUNÇÕES DE STATS E PAGINAÇÃO
            this.updateStats(response.stats);
            this.updatePagination(response.stats);
        } catch (error) {
            Thecarv.notify('Erro ao carregar', 'error');
        } finally {
            if (loading) loading.style.display = 'none';
        }
    },

    // --- LÓGICA DE STATS (RESTAURADA E EXPLÍCITA) ---
    updateStats(stats) {
        if (!stats) return;

        const totalSize = this.data.reduce((acc, doc) => acc + (doc.file_size || 0), 0);
        
        const elTotal = document.getElementById('totalDocuments');
        const elPdf = document.getElementById('pdfCount');
        const elImg = document.getElementById('imageCount');
        const elSize = document.getElementById('totalSize');

        if (elTotal) elTotal.textContent = stats.total || 0;
        if (elPdf) elPdf.textContent = stats.pdf || 0;
        if (elImg) elImg.textContent = stats.image || 0;
        if (elSize) elSize.textContent = Utils.formatFileSize(totalSize);
    },

    // --- PAGINAÇÃO ---
    updatePagination(stats) {
        const container = document.getElementById('paginationControls');
        if (!container || !stats || !stats.pages) return;

        container.innerHTML = `
            <div class="d-flex align-items-center justify-content-center mt-4">
                <button class="btn btn-sm btn-outline-secondary me-2" ${stats.current_page <= 1 ? 'disabled' : ''} onclick="DocumentsModule.changePage(${stats.current_page - 1})">Anterior</button>
                <span class="mx-3 fw-bold">Página ${stats.current_page} de ${stats.pages}</span>
                <button class="btn btn-sm btn-outline-secondary ms-2" ${stats.current_page >= stats.pages ? 'disabled' : ''} onclick="DocumentsModule.changePage(${stats.current_page + 1})">Próximo</button>
            </div>`;
    },

    // ADICIONADO: Função para trocar de página
    changePage(p) {
        this.currentPage = p;
        window.scrollTo({ top: 0, behavior: 'smooth' });
        this.filterAndDisplay();
    },

    filterAndDisplay() {
        const params = new URLSearchParams({
            search: document.getElementById('searchDocument')?.value || '',
            type: document.getElementById('filterType')?.value || '',
            document_type: document.getElementById('filterCategory')?.value || '',
            sortBy: document.getElementById('sortBy')?.value || 'upload_date',
            page: this.currentPage // Importante: incluir a página atual aqui
        });
        this.loadDocuments(params.toString());
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
        container.innerHTML = this.data.map(doc =>
            this.currentView === 'list' ? this.templateRow(doc) : this.templateCard(doc)
        ).join('');
        this.updateBulkActionButton();
    },

    templateRow(doc) {
        return `
            <tr>
                <td><input type="checkbox" class="doc-check form-check-input" value="${doc.id}"></td>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="fas ${Utils.getFileIcon(doc.filename)} me-2 text-${Utils.getFileColor(doc.filename)}"></i>
                        <div>
                            <strong>${doc.title}</strong>
                            <br><small class="text-muted">${Utils.truncate(doc.description, 40)}</small>
                        </div>
                    </div>
                </td>
                <td><span class="badge bg-${Utils.getFileColor(doc.filename)}">${Utils.getFileTypeLabel(doc.filename)}</span></td>
                <td><span class="badge bg-${Utils.getFileColor(doc.filename)}">${doc.document_type}</span></td>
                <td>${Utils.formatFileSize(doc.file_size)}</td>
                <td>${Utils.formatDate(new Date(doc.created_at))}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" onclick="DocumentsModule.download(${doc.id})"><i class="fas fa-download"></i></button>
                        <button class="btn btn-sm btn-outline-warning doc-edit-btn" data-id="${doc.id}"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="DocumentsModule.deleteDocument(${doc.id})"><i class="fas fa-trash"></i></button>
                    </div>
                </td>
            </tr>`;
    },

    templateCard(doc) {
        const icon = Utils.getFileIcon(doc.filename);
        const color = Utils.getFileColor(doc.filename);
        return `
            <div class="col-md-4 col-lg-3 mb-4">
                <div class="card h-100 shadow-sm border-top border-${color} border-4">
                    <div class="position-absolute top-0 end-0 p-2">
                         <input type="checkbox" class="doc-check form-check-input" value="${doc.id}">
                    </div>
                    <div class="card-body text-center">
                        <i class="fas ${icon} fa-3x text-${color} mb-3"></i>
                        <h6 class="card-title text-truncate" title="${doc.title}">${doc.title}</h6>
                        <span class="badge bg-${color} mb-3">${doc.document_type}</span>
                        <div class="btn-group w-100">
                            <button class="btn btn-sm btn-outline-primary" onclick="DocumentsModule.download(${doc.id})"><i class="fas fa-download"></i></button>
                            <button class="btn btn-sm btn-outline-warning doc-edit-btn" data-id="${doc.id}"><i class="fas fa-edit"></i></button>
                        </div>
                    </div>
                </div>
            </div>`;
    },

    async saveDocument() {
        const form = document.getElementById('documentForm');
        const formData = new FormData(form);
        const docId = document.getElementById('documentId').value;

        Thecarv.loading('A guardar...');
        try {
            if (docId) await api.put(`/documents/${docId}`, formData);
            else await api.post('/documents', formData);
            Thecarv.notify('Salvo!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('documentModal'));
            if (modal) modal.hide();
            await this.loadDocuments();
        } catch (error) {
            Thecarv.notify('Erro ao salvar', 'error');
        } 
    },

    async editDocument(id) {
        const doc = this.data.find(d => String(d.id) === String(id));
        if (!doc) return;
        document.getElementById('documentId').value = doc.id;
        document.getElementById('documentName').value = doc.title || '';
        document.getElementById('documentCategory').value = doc.document_type || '';
        document.getElementById('documentDescription').value = doc.description || '';
        document.getElementById('documentTags').value = doc.tags || '';
        document.getElementById('documentPublic').checked = !!doc.is_public;
        document.getElementById('documentModalTitle').textContent = 'Editar Documento';
        document.getElementById('documentFile').required = false;
        new bootstrap.Modal(document.getElementById('documentModal')).show();
    },

    download(id) { window.open(`${window.API_BASE_URL}/documents/${id}/download`, '_blank'); },
    
    toggleSelectAll() {
        const selectAll = document.getElementById('selectAll');
        document.querySelectorAll('.doc-check').forEach(cb => cb.checked = selectAll.checked);
        this.updateBulkActionButton();
    },

    updateBulkActionButton() {
        const selected = document.querySelectorAll('.doc-check:checked');
        const bulkBtn = document.getElementById('bulkDownloadBtn');
        if (bulkBtn) {
            bulkBtn.disabled = selected.length === 0;
            bulkBtn.innerHTML = `<i class="fas fa-download me-1"></i>Download (${selected.length})`;
        }
    },

    // Adicionado apenas para garantir que não falta no teu objeto
    async deleteDocument(id) {
        const res = await Thecarv.confirm('Apagar Documento?', 'Esta ação não pode ser desfeita.');
        if (res.isConfirmed) {
            Thecarv.loading('A eliminar...');
            try {
                await api.delete(`/documents/${id}`);
                Thecarv.notify('Removido!', 'success');
                await this.loadDocuments();
            } catch (error) {
                Thecarv.notify('Erro ao eliminar', 'error');
            } finally {
                Thecarv.close();
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => DocumentsModule.init());