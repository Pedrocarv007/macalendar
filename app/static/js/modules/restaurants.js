
/**
 * MAC Calendar - Restaurants Module
 * Versão Unificada e Otimizada
 */
const RestaurantsModule = {
    // --- Estado ---
    data: [],
    filteredData: [],
    currentView: 'list',
    
    // --- Configurações ---
    config: {
        appPrefix: (window.APP_PREFIX || '').replace(/\/$/, ''),
        get apiBase() { return this.appPrefix ? `${this.appPrefix}/api` : '/api' },
        get staticBase() { return this.appPrefix ? `${this.appPrefix}/static` : '/static' },
        get placeholder() { return `${this.staticBase}/images/placeholder-user.jpg` }
    },

    // --- Inicialização ---
    init() {
        this.setupEventListeners();
        this.loadRestaurants();
    },

    setupEventListeners() {
        // Eventos de clique em botões fixos
        const actions = {
            'exportRestaurantsBtn': () => this.exportToCSV(),
            'clearFiltersBtn': () => this.clearFilters(),
            'listViewBtn': () => this.toggleView('list'),
            'gridViewBtn': () => this.toggleView('grid'),
            'saveRestaurantBtn': () => this.save(),
            'deleteRestaurantBtn': () => this.deleteFromModal(),
            'removeRestaurantPhotoBtn': () => this.removePhoto()
        };

        Object.entries(actions).forEach(([id, func]) => {
            document.getElementById(id)?.addEventListener('click', func);
        });

        // Filtros e Foto
        document.getElementById('searchRestaurant')?.addEventListener('input', () => this.filter());
        document.getElementById('filterStatus')?.addEventListener('change', () => this.filter());
        document.getElementById('sortBy')?.addEventListener('change', () => this.sort());
        document.getElementById('restaurantPhoto')?.addEventListener('change', (e) => this.previewPhoto(e));

        // Delegação de eventos para elementos dinâmicos (tabela e cards)
        document.addEventListener('click', (e) => {
            const target = e.target.closest('[data-action], tr[data-restaurant-id], .restaurant-card[data-restaurant-id]');
            if (!target) return;

            const id = parseInt(target.getAttribute('data-restaurant-id'));
            const action = target.getAttribute('data-action');

            if (action) {
                e.stopPropagation();
                if (action === 'edit') this.edit(id);
                else if (action === 'delete') this.confirmDelete(id);
                else if (action === 'employees') this.viewEmployees(id);
            } else if (id) {
                this.edit(id);
            }
        });

        // Reset ao fechar modal
        document.getElementById('restaurantModal')?.addEventListener('hidden.bs.modal', () => this.resetModal());
    },

    // --- Lógica de Dados ---
    async loadRestaurants() {
        const loading = document.getElementById('restaurantsLoading');
        if (loading) loading.style.display = 'block';

        try {
            const response = await fetch(`${this.config.apiBase}/restaurants`, { credentials: 'include' });
            if (!response.ok) throw new Error('Falha no carregamento');
            
            const result = await response.json();
            this.data = result.restaurants || result || [];
            this.filter(); // Isto já chama o render e o updateStats
        } catch (error) {
            this.notify('Erro ao carregar restaurantes', 'error');
        } finally {
            if (loading) loading.style.display = 'none';
        }
    },

    // --- Renderização ---
    render() {
        const listContainer = document.getElementById('restaurantsList');
        const gridContainer = document.getElementById('restaurantsGrid');
        const noResults = document.getElementById('noRestaurants');
        
        const hasData = this.filteredData.length > 0;
        if (noResults) noResults.style.display = hasData ? 'none' : 'block';

        if (this.currentView === 'list') {
            if (listContainer) listContainer.style.display = hasData ? 'block' : 'none';
            if (gridContainer) gridContainer.style.display = 'none';
            if (hasData) this.renderListView();
        } else {
            if (listContainer) listContainer.style.display = 'none';
            if (gridContainer) gridContainer.style.display = hasData ? 'block' : 'none';
            if (hasData) this.renderGridView();
        }
        this.updateStats();
    },

    renderListView() {
        const tbody = document.getElementById('restaurantsTableBody');
        if (!tbody) return;

        tbody.innerHTML = this.filteredData.map(rest => `
            <tr data-restaurant-id="${rest.id}" style="cursor: pointer;">
                <td><strong>${rest.name}</strong>${rest.email ? `<br><small>${rest.email}</small>` : ''}</td>
                <td><small>${rest.address || '-'}</small></td>
                <td>${rest.phone || '-'}</td>
                <td><span class="badge bg-info">${Number(rest.employees_count || 0) + Number(rest.workers_count || 0)}</span></td>
                <td><span class="badge bg-${rest.is_active ? 'success' : 'secondary'}">${rest.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td class="text-end">
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" data-action="edit" data-restaurant-id="${rest.id}"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-outline-info" data-action="employees" data-restaurant-id="${rest.id}"><i class="fas fa-users"></i></button>
                        <button class="btn btn-sm btn-outline-danger" data-action="delete" data-restaurant-id="${rest.id}"><i class="fas fa-trash"></i></button>
                    </div>
                </td>
            </tr>`).join('');
    },

    renderGridView() {
        const container = document.getElementById('restaurantsGridContainer');
        if (!container) return;

        container.innerHTML = this.filteredData.map(rest => {
            const photoUrl = rest.photo_filename ? `${this.config.staticBase}/uploads/restaurants/${rest.photo_filename}` : this.config.placeholder;
            const total = Number(rest.employees_count || 0) + Number(rest.workers_count || 0);
            return `
                <div class="col-md-6 col-lg-4">
                    <div class="card restaurant-card h-100" data-restaurant-id="${rest.id}" style="cursor: pointer;">
                        <img src="${photoUrl}" class="card-img-top" style="height: 180px; object-fit: cover;">
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-2">
                                <h6 class="mb-0">${rest.name}</h6>
                                <span class="badge bg-${rest.is_active ? 'success' : 'secondary'}">${rest.is_active ? 'Ativo' : 'Inativo'}</span>
                            </div>
                            <small class="text-muted d-block mb-2"><i class="fas fa-map-marker-alt me-1"></i>${rest.address || 'Sem endereço'}</small>
                            <div class="d-flex justify-content-between small text-muted">
                                <span><i class="fas fa-users me-1"></i>${total}</span>
                                ${rest.capacity ? `<span><i class="fas fa-chair me-1"></i>${rest.capacity}</span>` : ''}
                            </div>
                        </div>
                        <div class="card-footer bg-transparent border-top-0 pb-3 text-center">
                            <div class="btn-group w-100">
                                <button class="btn btn-sm btn-outline-primary" data-action="edit" data-restaurant-id="${rest.id}"><i class="fas fa-edit"></i></button>
                                <button class="btn btn-sm btn-outline-info" data-action="employees" data-restaurant-id="${rest.id}"><i class="fas fa-users"></i></button>
                                <button class="btn btn-sm btn-outline-danger" data-action="delete" data-restaurant-id="${rest.id}"><i class="fas fa-trash"></i></button>
                            </div>
                        </div>
                    </div>
                </div>`;
        }).join('');
    },

    // --- Ações ---
    filter() {
        const search = document.getElementById('searchRestaurant')?.value.toLowerCase() || '';
        const status = document.getElementById('filterStatus')?.value || '';

        this.filteredData = this.data.filter(r => {
            const matchesSearch = r.name.toLowerCase().includes(search) || (r.address?.toLowerCase().includes(search));
            const matchesStatus = status === '' || (status === 'true' ? r.is_active : !r.is_active);
            return matchesSearch && matchesStatus;
        });
        this.sort();
    },

    sort() {
        const sortBy = document.getElementById('sortBy')?.value || 'name';
        this.filteredData.sort((a, b) => {
            if (sortBy === 'name') return a.name.localeCompare(b.name);
            if (sortBy === 'created_at') return new Date(b.created_at) - new Date(a.created_at);
            return 0;
        });
        this.render();
    },

    async save() {
        const form = document.getElementById('restaurantForm');
        if (!form) return;

        const formData = new FormData(form);
        const id = formData.get('restaurantId');
        const photoFile = document.getElementById('restaurantPhoto')?.files[0];

        const payload = Object.fromEntries(formData.entries());
        payload.is_active = document.getElementById('restaurantActive').checked;
        delete payload.restaurantId;

        try {
            const url = id ? `${this.config.apiBase}/restaurants/${id}` : `${this.config.apiBase}/restaurants`;
            const response = await fetch(url, {
                method: id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Erro ao salvar');
            
            const result = await response.json();
            const finalId = id || result.id || result.restaurant?.id;

            if (photoFile && finalId) await this.uploadPhoto(finalId, photoFile);

            this.notify('Salvo com sucesso!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('restaurantModal'))?.hide();
            this.loadRestaurants();
        } catch (e) {
            this.notify(e.message, 'error');
        }
    },

    edit(id) {
        const r = this.data.find(res => res.id === id);
        if (!r) return;
        
        document.getElementById('restaurantModalTitle').textContent = 'Editar Restaurante';
        document.getElementById('restaurantId').value = r.id;
        document.getElementById('restaurantName').value = r.name || '';
        document.getElementById('restaurantEmail').value = r.email || '';
        document.getElementById('restaurantPhone').value = r.phone || '';
        document.getElementById('restaurantAddress').value = r.address || '';
        document.getElementById('restaurantCapacity').value = r.capacity || '';
        document.getElementById('restaurantActive').checked = Boolean(r.is_active);
        
        const preview = document.getElementById('restaurantPhotoPreview');
        if (preview) preview.src = r.photo_filename ? `${this.config.staticBase}/uploads/restaurants/${r.photo_filename}` : this.config.placeholder;

        bootstrap.Modal.getOrCreateInstance(document.getElementById('restaurantModal')).show();
    },

    confirmDelete(id) {
        if (confirm('Deseja realmente eliminar este restaurante?')) {
            this.deleteById(id);
        }
    },

    deleteFromModal() {
        const id = document.getElementById('restaurantId').value;
        if (id) this.confirmDelete(parseInt(id));
    },

    async deleteById(id) {
        try {
            const res = await fetch(`${this.config.apiBase}/restaurants/${id}`, { method: 'DELETE', credentials: 'include' });
            if (res.ok) {
                this.notify('Restaurante eliminado', 'success');
                this.loadRestaurants();
                bootstrap.Modal.getInstance(document.getElementById('restaurantModal'))?.hide();
            }
        } catch (e) { this.notify('Erro ao eliminar', 'error'); }
    },

    // --- Utilitários Auxiliares ---
    updateStats() {
        const stats = {
            total: this.data.length,
            active: this.data.filter(r => r.is_active).length,
            colabs: this.data.reduce((acc, r) => acc + (Number(r.employees_count || 0) + Number(r.workers_count || 0)), 0)
        };

        const map = { 'totalRestaurants': stats.total, 'activeRestaurants': stats.active, 'totalEmployees': stats.colabs };
        Object.entries(map).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        });
    },

    toggleView(view) {
        this.currentView = view;
        const listBtn = document.getElementById('listViewBtn');
        const gridBtn = document.getElementById('gridViewBtn');
        
        if (listBtn) listBtn.className = view === 'list' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-outline-primary';
        if (gridBtn) gridBtn.className = view === 'grid' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-outline-primary';
        
        this.render();
    },

    async uploadPhoto(id, file) {
        const fd = new FormData();
        fd.append('file', file);
        return fetch(`${this.config.apiBase}/restaurants/${id}/upload-photo`, { method: 'POST', body: fd, credentials: 'include' });
    },

    async removePhoto() {
        const id = document.getElementById('restaurantId').value;
        if (!id) return this.resetModal();
        try {
            await fetch(`${this.config.apiBase}/restaurants/${id}/photo`, { method: 'DELETE', credentials: 'include' });
            this.loadRestaurants();
            document.getElementById('restaurantPhotoPreview').src = this.config.placeholder;
        } catch (e) { this.notify('Erro ao remover foto', 'error'); }
    },

    previewPhoto(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (ex) => document.getElementById('restaurantPhotoPreview').src = ex.target.result;
            reader.readAsDataURL(file);
        }
    },

    exportToCSV() {
        if (!this.data.length) return this.notify('Sem dados para exportar', 'warning');
        const headers = "Nome,Email,Telefone,Status,Colaboradores\n";
        const rows = this.data.map(r => `"${r.name}","${r.email || ''}","${r.phone || ''}","${r.is_active ? 'Ativo' : 'Inativo'}","${Number(r.employees_count || 0) + Number(r.workers_count || 0)}"`).join("\n");
        const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'restaurantes.csv';
        link.click();
    },

    viewEmployees(id) {
        window.location.href = `${this.config.appPrefix}/employees?restaurant=${id}`;
    },

    resetModal() {
        document.getElementById('restaurantForm')?.reset();
        document.getElementById('restaurantId').value = '';
        document.getElementById('restaurantModalTitle').textContent = 'Novo Restaurante';
        const preview = document.getElementById('restaurantPhotoPreview');
        if (preview) preview.src = this.config.placeholder;
    },

    clearFilters() {
        document.getElementById('searchRestaurant').value = '';
        document.getElementById('filterStatus').value = '';
        this.filter();
    },

    notify(msg, type = 'info') {
        if (window.App?.notify) window.App.notify(msg, type);
        else if (typeof Utils !== 'undefined' && Utils.showToast) Utils.showToast(msg, type === 'error' ? 'danger' : type);
        else alert(msg);
    }
};

// Inicialização Final
document.addEventListener('DOMContentLoaded', () => RestaurantsModule.init());
