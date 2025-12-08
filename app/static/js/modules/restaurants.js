/**
 * MAC Calendar - Restaurants Module
 * Módulo para gerenciar restaurantes
 */

const RestaurantsModule = {
    data: [],
    currentFilter: '',
    
    /**
     * Inicializar o módulo
     */
    init() {
        console.log('🏢 Inicializando Restaurants Module...');
        this.setupHandlers();
        this.loadRestaurants();
    },
    
    /**
     * Setup event handlers
     */
    setupHandlers() {
        // Handlers dos botões podem ser configurados aqui
    },
    
    /**
     * Carregar restaurantes
     */
    async loadRestaurants() {
        const loading = document.getElementById('restaurantsLoading');
        if (loading) loading.style.display = 'block';
        
        try {
            const response = await api.get('/restaurants');
            this.data = response.restaurants || [];
            
            // Atualizar variáveis globais para o template inline
            if (typeof window !== 'undefined') {
                window.restaurants = this.data;
                window.filteredRestaurants = [...this.data];
            }
            
            console.log('✓ Restaurantes carregados:', this.data);
            this.filterAndDisplay();
        } catch (error) {
            console.error('❌ Erro ao carregar restaurantes:', error);
            if (typeof appState !== 'undefined' && typeof appState.notify === 'function') {
                appState.notify('Erro ao carregar restaurantes', 'error');
            }
        } finally {
            if (loading) loading.style.display = 'none';
        }
    },
    
    /**
     * Filtrar e exibir restaurantes
     */
    filterAndDisplay() {
        // Aplicar filtros se houver
        const listContainer = document.getElementById('restaurantsList');
        const gridContainer = document.getElementById('restaurantsGrid');
        const noResults = document.getElementById('noRestaurants');
        const tbody = document.getElementById('restaurantsTableBody');
        
        if (!tbody) {
            console.warn('⚠️ Elementos da tabela não encontrados');
            return;
        }
        
        if (!Array.isArray(this.data) || this.data.length === 0) {
            if (listContainer) listContainer.style.display = 'none';
            if (gridContainer) gridContainer.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            return;
        }
        
        // Mostrar lista
        if (listContainer) listContainer.style.display = 'block';
        if (gridContainer) gridContainer.style.display = 'none';
        if (noResults) noResults.style.display = 'none';
        
        // Renderizar tabela
        tbody.innerHTML = this.data.map(rest => `
            <tr onclick="editRestaurant(${rest.id})" style="cursor: pointer;">
                <td>
                    <div>
                        <strong>${rest.name}</strong>
                        ${rest.email ? `<br><small class="text-muted">${rest.email}</small>` : ''}
                    </div>
                </td>
                <td>${rest.type || '-'}</td>
                <td><small>${rest.address || 'Não informado'}</small></td>
                <td>${rest.phone || '-'}</td>
                <td><span class="badge bg-info">${rest.employees_count || 0}</span></td>
                <td><span class="badge bg-${rest.is_active ? 'success' : 'secondary'}">
                    ${rest.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); editRestaurant(${rest.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); viewEmployees(${rest.id})">
                            <i class="fas fa-users"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); confirmDeleteRestaurant(${rest.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        // Atualizar stats
        const totalEl = document.getElementById('totalRestaurants');
        const activeEl = document.getElementById('activeRestaurants');
        const employeesEl = document.getElementById('totalEmployees');
        
        if (totalEl) totalEl.textContent = this.data.length;
        if (activeEl) activeEl.textContent = this.data.filter(r => r.is_active).length;
        if (employeesEl) employeesEl.textContent = this.data.reduce((total, r) => total + (r.employees_count || 0), 0);
        
        console.log('✓ Restaurantes renderizados:', this.data.length);
    },
    
    /**
     * Deletar restaurante
     */
    async deleteRestaurant(id) {
        if (confirm('Tem certeza que deseja deletar este restaurante?')) {
            try {
                await api.delete(`/restaurants/${id}`);
                appState.notify('Restaurante deletado com sucesso', 'success');
                this.loadRestaurants();
            } catch (error) {
                console.error('Erro ao deletar restaurante:', error);
                appState.notify('Erro ao deletar restaurante', 'error');
            }
        }
    },
    
    /**
     * Editar restaurante
     */
    async editRestaurant(id) {
        console.log('Editar restaurante:', id);
        // Será implementado conforme necessário
    }
};

/**
 * Alternar entre vista de lista e grid
 */
function toggleView(view) {
    const listContainer = document.getElementById('restaurantsList');
    const gridContainer = document.getElementById('restaurantsGrid');
    const listBtn = document.getElementById('listViewBtn');
    const gridBtn = document.getElementById('gridViewBtn');
    
    if (view === 'list') {
        if (listContainer) listContainer.style.display = 'block';
        if (gridContainer) gridContainer.style.display = 'none';
        if (listBtn) listBtn.className = 'btn btn-sm btn-primary';
        if (gridBtn) gridBtn.className = 'btn btn-sm btn-outline-primary';
    } else {
        if (listContainer) listContainer.style.display = 'none';
        if (gridContainer) gridContainer.style.display = 'block';
        if (listBtn) listBtn.className = 'btn btn-sm btn-outline-primary';
        if (gridBtn) gridBtn.className = 'btn btn-sm btn-primary';
        
        // Renderizar grid quando mudar para grid view
        renderRestaurantGrid();
    }
}

/**
 * Renderizar restaurantes em grid
 */
function renderRestaurantGrid() {
    const gridContainer = document.getElementById('restaurantsGridContainer');
    if (!gridContainer || !RestaurantsModule.data) return;
    
    gridContainer.innerHTML = RestaurantsModule.data.map(rest => {
        const photoUrl = rest.photo_filename 
            ? `https://www.thecarv.com/mac/static/uploads/restaurants/${rest.photo_filename}`
            : 'https://www.thecarv.com/mac/static/images/user_demo.jpg';
        
        return `
            <div class="col-md-6 col-lg-4">
                <div class="card restaurant-card" onclick="editRestaurant(${rest.id})" style="cursor: pointer;">
                    <img src="${photoUrl}" class="card-img-top" alt="${rest.name}"
                         style="height: 200px; object-fit: cover;">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h6 class="card-title mb-0">${rest.name}</h6>
                            <span class="badge bg-${rest.is_active ? 'success' : 'secondary'}">
                                ${rest.is_active ? 'Ativo' : 'Inativo'}
                            </span>
                        </div>
                        
                        <div class="text-muted small mb-3">
                            ${rest.address ? `<div><i class="fas fa-map-marker-alt me-1"></i>${rest.address.substring(0, 50)}${rest.address.length > 50 ? '...' : ''}</div>` : ''}
                            ${rest.phone ? `<div><i class="fas fa-phone me-1"></i>${rest.phone}</div>` : ''}
                            ${rest.email ? `<div><i class="fas fa-envelope me-1"></i>${rest.email}</div>` : ''}
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                <i class="fas fa-users me-1"></i>${rest.employees_count || 0} funcionários
                            </small>
                            <div class="btn-group btn-group-sm" role="group">
                                <button class="btn btn-outline-primary" onclick="event.stopPropagation(); editRestaurant(${rest.id})" title="Editar">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-info" onclick="event.stopPropagation(); viewEmployees(${rest.id})" title="Ver funcionários">
                                    <i class="fas fa-users"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="event.stopPropagation(); confirmDeleteRestaurant(${rest.id})" title="Deletar">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Editar restaurante (versão global)
 */
function editRestaurant(id) {
    console.log('Editando restaurante:', id);
    // Será implementado conforme necessário
}

/**
 * Ver funcionários do restaurante
 */
function viewEmployees(id) {
    console.log('Ver funcionários do restaurante:', id);
    // Será implementado conforme necessário
}

/**
 * Confirmar e deletar restaurante
 */
function confirmDeleteRestaurant(id) {
    if (confirm('Tem certeza que deseja deletar este restaurante?')) {
        RestaurantsModule.deleteRestaurant(id);
    }
}
