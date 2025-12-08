/**
 * MAC Calendar - Employees Module
 * Gerencia funcionalidades de colaboradores
 */

const EmployeesModule = {
    employees: [],
    currentFilter: '',

    /**
     * Inicializar módulo
     */
    init() {
        console.log('Inicializando Employees Module');
        this.setupHandlers();
        this.loadEmployees();
    },

    /**
     * Setup event handlers
     */
    setupHandlers() {
        // Buscar colaboradores
        const searchInput = DOM.$('#searchEmployee');
        if (searchInput) {
            DOM.on(searchInput, 'input', (e) => {
                this.currentFilter = e.target.value;
                this.filterAndDisplay();
            });
        }

        // Adicionar novo
        DOM.on('[data-bs-target="#employeeModal"]', 'click', (e) => {
            e.preventDefault();
            this.showAddForm();
        });

        // Os event listeners para editar e deletar agora usam onclick direto nos botões
    },

    /**
     * Carregar colaboradores
     */
    async loadEmployees() {
        try {
            // Mostrar loading
            const loadingDiv = DOM.$('#employeesLoading');
            if (loadingDiv) loadingDiv.style.display = 'block';
            
            const response = await api.get('/employees');
            this.employees = response.employees || [];
            
            // Esconder loading
            if (loadingDiv) loadingDiv.style.display = 'none';
            
            this.display();
        } catch (error) {
            console.error('Erro ao carregar colaboradores:', error);
            const loadingDiv = DOM.$('#employeesLoading');
            if (loadingDiv) loadingDiv.style.display = 'none';
            App.notify('Erro ao carregar colaboradores', 'danger');
        }
    },

    /**
     * Filtrar e exibir
     */
    filterAndDisplay() {
        const filtered = this.employees.filter(emp => {
            const searchTerm = this.currentFilter.toLowerCase();
            return (
                emp.name?.toLowerCase().includes(searchTerm) ||
                emp.email?.toLowerCase().includes(searchTerm) ||
                emp.department?.toLowerCase().includes(searchTerm)
            );
        });
        this.displayTable(filtered);
    },

    /**
     * Exibir colaboradores
     */
    display() {
        this.displayTable(this.employees);
    },

    /**
     * Exibir tabela de colaboradores
     */
    displayTable(employees) {
        const tbody = DOM.$('#employeesTableBody');
        const listView = DOM.$('#employeesList');
        const noResults = DOM.$('#noEmployees');
        
        if (!tbody) return;

        // Mostrar/ocultar seções
        if (employees.length === 0) {
            if (listView) listView.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            return;
        }

        if (listView) listView.style.display = 'block';
        if (noResults) noResults.style.display = 'none';

        tbody.innerHTML = employees.map(emp => `
            <tr data-id="${emp.id}">
                <td>
                    <img src="${emp.photo_url ? emp.photo_url : 'https://www.thecarv.com/mac/static/images/user_demo.jpg'}" 
                         alt="${emp.name}" class="employee-avatar" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" onerror="this.src='https://www.thecarv.com/mac/static/images/user_demo.jpg'">
                </td>
                <td>${emp.name}</td>
                <td>${emp.role || '-'}</td>
                <td>${emp.department || '-'}</td>
                <td>${emp.phone || '-'}</td>
                <td><span class="badge bg-success">Ativo</span></td>
                <td>
                    <button class="btn btn-sm btn-primary btn-edit-employee" data-id="${emp.id}" onclick="EmployeesModule.editEmployee(${emp.id})"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger btn-delete-employee" data-id="${emp.id}" onclick="EmployeesModule.deleteEmployee(${emp.id})"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    },

    /**
     * Exibir grid de colaboradores
     */
    displayGrid(employees) {
        const gridContainer = DOM.$('#employeesGridContainer');
        const gridView = DOM.$('#employeesGrid');
        const noResults = DOM.$('#noEmployees');
        
        if (!gridContainer) return;

        // Mostrar/ocultar seções
        if (employees.length === 0) {
            if (gridView) gridView.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            return;
        }

        if (gridView) gridView.style.display = 'block';
        if (noResults) noResults.style.display = 'none';

        gridContainer.innerHTML = employees.map(emp => `
            <div class="col-lg-3 col-md-4 col-sm-6">
                <div class="card h-100 employee-card">
                    <div class="card-body text-center">
                        <img src="${emp.photo_url ? emp.photo_url : 'https://www.thecarv.com/mac/static/images/user_demo.jpg'}" 
                             alt="${emp.name}" class="rounded-circle mb-3" style="width: 100px; height: 100px; object-fit: cover;" onerror="this.src='https://www.thecarv.com/mac/static/images/user_demo.jpg'">
                        <h5 class="card-title">${emp.name}</h5>
                        <p class="text-muted small">${emp.department || '-'}</p>
                        <p class="text-muted small">${emp.role || '-'}</p>
                        <p class="text-muted small"><i class="fas fa-phone"></i> ${emp.phone || '-'}</p>
                        <div class="mt-3 d-flex gap-2 justify-content-center">
                            <button class="btn btn-sm btn-primary btn-edit-employee" data-id="${emp.id}" onclick="EmployeesModule.editEmployee(${emp.id})"><i class="fas fa-edit"></i></button>
                            <button class="btn btn-sm btn-danger btn-delete-employee" data-id="${emp.id}" onclick="EmployeesModule.deleteEmployee(${emp.id})"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    /**
     * Exibir formulário de adicionar
     */
    showAddForm() {
        const modal = DOM.$('#employeeModal');
        const form = DOM.$('#employeeForm');
        const title = DOM.$('#employeeModalTitle');
        const deleteBtn = DOM.$('#deleteEmployeeBtn');
        
        if (form) {
            form.reset();
            DOM.$('#employeeId').value = '';
            
            // Resetar foto para padrão
            DOM.$('#employeePhotoPreview').src = 'https://www.thecarv.com/mac/static/images/user_demo.jpg';
            DOM.$('#removePhotoBtn').style.display = 'none';
            
            // Esconder botão de deletar
            if (deleteBtn) deleteBtn.style.display = 'none';
        }
        
        if (title) title.textContent = 'Novo Colaborador';
        
        // Mostrar modal via Bootstrap
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    },

    /**
     * Editar colaborador
     */
    async editEmployee(id) {
        try {
            const response = await api.get(`/employees/${id}`);
            const employee = response.employee;
            
            const modal = DOM.$('#employeeModal');
            const form = DOM.$('#employeeForm');
            const title = DOM.$('#employeeModalTitle');
            
            if (form && employee) {
                // Preencher todos os campos que existem
                DOM.$('#employeeId').value = employee.id || '';
                DOM.$('#employeeName').value = employee.name || '';
                DOM.$('#employeeEmail').value = employee.email || '';
                DOM.$('#employeePhone').value = employee.phone || '';
                DOM.$('#employeePosition').value = employee.position || employee.role || '';
                DOM.$('#employeeDepartment').value = employee.department || '';
                DOM.$('#employeeBirthDate').value = employee.birth_date ? employee.birth_date.split('T')[0] : '';
                DOM.$('#employeeActive').checked = employee.is_active !== false;
                DOM.$('#employeeAddress').value = employee.address || '';
                DOM.$('#employeeNotes').value = employee.notes || '';
                
                // Preencher restaurant_id se existir
                const restaurantSelect = DOM.$('#employeeRestaurant');
                if (restaurantSelect && employee.restaurant_id) {
                    restaurantSelect.value = employee.restaurant_id;
                }
                
                // Mostrar foto se existir
                if (employee.photo_url) {
                    DOM.$('#employeePhotoPreview').src = employee.photo_url;
                    DOM.$('#removePhotoBtn').style.display = 'inline-block';
                } else {
                    DOM.$('#employeePhotoPreview').src = 'https://www.thecarv.com/mac/static/images/user_demo.jpg';
                    DOM.$('#removePhotoBtn').style.display = 'none';
                }
                
                // Mostrar botão de deletar
                const deleteBtn = DOM.$('#deleteEmployeeBtn');
                if (deleteBtn) deleteBtn.style.display = 'inline-block';
                
                if (title) title.textContent = `Editar Colaborador - ${employee.name}`;
                
                console.log('📝 Abrindo modal para editar:', employee);
                
                // Mostrar modal via Bootstrap
                if (modal) {
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.show();
                }
            } else {
                console.error('Form ou employee não encontrado:', {form, employee});
                App.notify('Erro ao carregar dados do colaborador', 'danger');
            }
        } catch (error) {
            console.error('Erro ao carregar colaborador:', error);
            App.notify('Erro ao carregar colaborador', 'danger');
        }
    },

    /**
     * Deletar colaborador
     */
    async deleteEmployee(id) {
        if (!confirm('Tem certeza que deseja remover este colaborador?')) {
            return;
        }

        try {
            await api.delete(`/employees/${id}`);
            App.notify('Colaborador removido com sucesso', 'success');
            this.loadEmployees();
        } catch (error) {
            console.error('Erro ao remover colaborador:', error);
            App.notify('Erro ao remover colaborador', 'danger');
        }
    }
};

/**
 * Salvar colaborador (novo ou editado)
 */
async function saveEmployee() {
    const form = DOM.$('#employeeForm');
    const employeeId = DOM.$('#employeeId')?.value;
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    try {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        // Remover campos vazios
        Object.keys(data).forEach(key => {
            if (!data[key] && key !== 'is_active') {
                delete data[key];
            }
        });

        let response;
        if (employeeId && employeeId !== '') {
            // Atualizar
            response = await api.put(`/employees/${employeeId}`, data);
            App.notify('Colaborador atualizado com sucesso', 'success');
        } else {
            // Criar novo
            response = await api.post('/employees', data);
            App.notify('Colaborador criado com sucesso', 'success');
        }

        // Fechar modal
        const modal = DOM.$('#employeeModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        }

        // Recarregar lista
        EmployeesModule.loadEmployees();
        
    } catch (error) {
        console.error('Erro ao salvar colaborador:', error);
        App.notify(error.message || 'Erro ao salvar colaborador', 'danger');
    }
}

/**
 * Deletar colaborador (versão global para o botão do modal)
 */
function deleteEmployee() {
    const employeeId = DOM.$('#employeeId')?.value;
    if (!employeeId) {
        App.notify('ID do colaborador não encontrado', 'danger');
        return;
    }

    if (!confirm('Tem certeza que deseja remover este colaborador?')) {
        return;
    }

    EmployeesModule.deleteEmployee(employeeId);
}

/**
 * Alterna entre view de lista e grid
 */
function toggleView(view) {
    const listView = DOM.$('#employeesList');
    const gridView = DOM.$('#employeesGrid');
    const listBtn = DOM.$('#listViewBtn');
    const gridBtn = DOM.$('#gridViewBtn');
    
    if (view === 'list') {
        if (listView) listView.style.display = 'block';
        if (gridView) gridView.style.display = 'none';
        if (listBtn) listBtn.classList.add('btn-primary');
        if (listBtn) listBtn.classList.remove('btn-outline-primary');
        if (gridBtn) gridBtn.classList.remove('btn-primary');
        if (gridBtn) gridBtn.classList.add('btn-outline-primary');
    } else {
        if (listView) listView.style.display = 'none';
        if (gridView) gridView.style.display = 'block';
        if (listBtn) listBtn.classList.remove('btn-primary');
        if (listBtn) listBtn.classList.add('btn-outline-primary');
        if (gridBtn) gridBtn.classList.add('btn-primary');
        if (gridBtn) gridBtn.classList.remove('btn-outline-primary');
        
        // Renderizar grid quando mudar para grid view
        EmployeesModule.displayGrid(EmployeesModule.employees);
    }
}

/**
 * Filtra colaboradores baseado nos filtros aplicados
 */
function filterEmployees() {
    const searchTerm = DOM.$('#searchEmployee')?.value || '';
    const department = DOM.$('#filterDepartment')?.value || '';
    const status = DOM.$('#filterStatus')?.value || '';
    
    let filtered = EmployeesModule.employees;
    
    if (searchTerm) {
        filtered = filtered.filter(emp =>
            emp.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            emp.email?.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }
    
    if (department) {
        filtered = filtered.filter(emp => emp.department === department);
    }
    
    EmployeesModule.displayTable(filtered);
}

/**
 * Ordena colaboradores
 */
function sortEmployees() {
    const sortBy = DOM.$('#sortBy')?.value || 'name';
    
    const sorted = [...EmployeesModule.employees].sort((a, b) => {
        let aVal = a[sortBy] || '';
        let bVal = b[sortBy] || '';
        
        if (sortBy === 'hire_date' || sortBy === 'birth_date') {
            return new Date(aVal) - new Date(bVal);
        }
        
        return String(aVal).localeCompare(String(bVal));
    });
    
    EmployeesModule.displayTable(sorted);
}

/**
 * Limpa todos os filtros
 */
function clearFilters() {
    DOM.$('#searchEmployee').value = '';
    DOM.$('#filterDepartment').value = '';
    DOM.$('#filterStatus').value = '';
    DOM.$('#sortBy').value = 'name';
    EmployeesModule.displayTable(EmployeesModule.employees);
}

/**
 * Preview da foto antes de upload
 */
function previewPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = DOM.$('#employeePhotoPreview');
            if (preview) {
                preview.src = e.target.result;
                DOM.$('#removePhotoBtn').style.display = 'inline-block';
            }
        };
        reader.readAsDataURL(file);
    }
}

/**
 * Remove foto selecionada
 */
function removePhoto() {
    const input = DOM.$('#employeePhoto');
    if (input) input.value = '';
    
    const preview = DOM.$('#employeePhotoPreview');
    if (preview) preview.src = 'https://www.thecarv.com/mac/static/images/user_demo.jpg';
    
    DOM.$('#removePhotoBtn').style.display = 'none';
}
