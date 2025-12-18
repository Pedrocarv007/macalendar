/**
 * MAC Calendar - Employees Module
 * Gerencia funcionalidades de colaboradores
 */

const EmployeesModule = {
    employees: [],
    restaurants: [],
    currentFilter: '',

    /**
     * Inicializar módulo
     */
    init() {
        console.log('Inicializando Employees Module');
        this.setupHandlers();
        this.loadRestaurants();
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
            if (window.App && window.App.notify) {
                window.App.notify('Erro ao carregar colaboradores', 'danger');
            }
        }
    },

    /**
     * Carregar restaurantes
     */
    async loadRestaurants() {
        try {
            const response = await api.get('/restaurants');
            this.restaurants = response.restaurants || [];
            
            // Preencher o select de restaurantes
            const restaurantSelect = DOM.$('#employeeRestaurant');
            if (restaurantSelect && this.restaurants.length > 0) {
                const currentValue = restaurantSelect.value;
                restaurantSelect.innerHTML = '<option value="">Selecione o restaurante...</option>' + 
                    this.restaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
                restaurantSelect.value = currentValue;
            }
        } catch (error) {
            console.error('Erro ao carregar restaurantes:', error);
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
        const thead = DOM.$('#employeesTableHead');
        const listView = DOM.$('#employeesList');
        const noResults = DOM.$('#noEmployees');
        const currentUser = appState?.user || {};
        const isPrivileged = ['admin', 'rh'].includes((currentUser.role || '').toLowerCase());
        
        if (!tbody) return;

        // Mostrar/ocultar seções
        if (employees.length === 0) {
            if (listView) listView.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            return;
        }

        if (listView) listView.style.display = 'block';
        if (noResults) noResults.style.display = 'none';

        if (thead) {
            if (isPrivileged) {
                thead.innerHTML = `
                    <tr>
                        <th>Foto</th>
                        <th>Nome</th>
                        <th>Cargo</th>
                        <th>Departamento</th>
                        <th>Telefone</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>`;
            } else {
                thead.innerHTML = `
                    <tr>
                        <th>Foto</th>
                        <th>Nome</th>
                        <th>Cargo</th>
                        <th>Departamento</th>
                    </tr>`;
            }
        }

        const prefix = window.APP_PREFIX || '';
        tbody.innerHTML = employees.map(emp => {
            const isOwn = currentUser && emp.id === currentUser.id;
            const canSeeSensitive = isPrivileged || isOwn;
            const photoUrl = emp.photo_url 
                ? `${prefix}${emp.photo_url}` 
                : (emp.photo_filename ? `${prefix}/uploads/employees/${emp.photo_filename}` : `${prefix}/static/images/placeholder-user.jpg`);
            if (isPrivileged) {
                return `
                <tr data-id="${emp.id}">
                    <td>
                        <img src="${photoUrl}" 
                             alt="${emp.name}" class="employee-avatar" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" onerror="this.src='${prefix}/static/images/placeholder-user.jpg'">
                    </td>
                    <td>${emp.name}</td>
                    <td>${emp.position || '-'}</td>
                    <td>${emp.department || '-'}</td>
                    <td>${emp.phone || '-'}</td>
                    <td><span class="badge ${emp.is_active ? 'bg-success' : 'bg-danger'}">${emp.is_active ? 'Ativo' : 'Inativo'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary btn-edit-employee" data-id="${emp.id}" onclick="EmployeesModule.editEmployee(${emp.id})"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-danger btn-delete-employee" data-id="${emp.id}" onclick="EmployeesModule.deleteEmployee(${emp.id})"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `;
            }
            return `
                <tr data-id="${emp.id}">
                    <td>
                        <img src="${photoUrl}" 
                             alt="${emp.name}" class="employee-avatar" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" onerror="this.src='${prefix}/static/images/placeholder-user.jpg'">
                    </td>
                    <td>${emp.name}</td>
                    <td>${emp.position || '-'}</td>
                    <td>${emp.department || '-'}</td>
                </tr>
            `;
        }).join('');
    },

    /**
     * Exibir grid de colaboradores
     */
    displayGrid(employees) {
        const gridContainer = DOM.$('#employeesGridContainer');
        const gridView = DOM.$('#employeesGrid');
        const noResults = DOM.$('#noEmployees');
        const currentUser = appState?.user || {};
        const isPrivileged = ['admin', 'rh'].includes((currentUser.role || '').toLowerCase());
        
        if (!gridContainer) return;

        // Mostrar/ocultar seções
        if (employees.length === 0) {
            if (gridView) gridView.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            return;
        }

        if (gridView) gridView.style.display = 'block';
        if (noResults) noResults.style.display = 'none';

        const prefix = window.APP_PREFIX || '';
        gridContainer.innerHTML = employees.map(emp => {
            const isOwn = currentUser && emp.id === currentUser.id;
            const canSeeSensitive = isPrivileged || isOwn;
            const photoUrl = emp.photo_url 
                ? `${prefix}${emp.photo_url}` 
                : (emp.photo_filename ? `${prefix}/uploads/employees/${emp.photo_filename}` : `${prefix}/static/images/placeholder-user.jpg`);
            if (isPrivileged) {
                return `
                <div class="col-lg-3 col-md-4 col-sm-6">
                    <div class="card h-100 employee-card">
                        <div class="card-body text-center">
                            <img src="${photoUrl}" 
                                 alt="${emp.name}" class="rounded-circle mb-3" style="width: 100px; height: 100px; object-fit: cover;" onerror="this.src='${prefix}/static/images/placeholder-user.jpg'">
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
            `;
            }
            return `
                <div class="col-lg-3 col-md-4 col-sm-6">
                    <div class="card h-100 employee-card">
                        <div class="card-body text-center">
                            <img src="${photoUrl}" 
                                 alt="${emp.name}" class="rounded-circle mb-3" style="width: 100px; height: 100px; object-fit: cover;" onerror="this.src='${prefix}/static/images/placeholder-user.jpg'">
                            <h5 class="card-title">${emp.name}</h5>
                            <p class="text-muted small">${emp.department || '-'}</p>
                            <p class="text-muted small">${emp.role || '-'}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
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
        
        // Recarregar restaurantes antes de abrir modal
        this.loadRestaurants();
        
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
                
                // Recarregar restaurantes antes de preencher
                await this.loadRestaurants();
                
                // Preencher restaurant_id se existir
                const restaurantSelect = DOM.$('#employeeRestaurant');
                if (restaurantSelect && employee.restaurant_id) {
                    restaurantSelect.value = employee.restaurant_id;
                }
                
                // Mostrar foto se existir
                if (employee.photo_url || employee.photo_filename) {
                    const prefix = window.APP_PREFIX || '';
                    const photoUrl = employee.photo_url 
                        ? `${prefix}${employee.photo_url}` 
                        : `${prefix}/uploads/employees/${employee.photo_filename}`;
                    DOM.$('#employeePhotoPreview').src = photoUrl;
                    DOM.$('#removePhotoBtn').style.display = 'inline-block';
                } else {
                    const prefix = window.APP_PREFIX || '';
                    DOM.$('#employeePhotoPreview').src = `${prefix}/static/images/placeholder-user.jpg`;
                    DOM.$('#removePhotoBtn').style.display = 'none';
                }

                // Preencher role se campo existir
                const roleSelect = DOM.$('#employeeRole');
                if (roleSelect) {
                    roleSelect.value = employee.role || '';
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
                if (window.App && window.App.notify) {
                    window.App.notify('Erro ao carregar dados do colaborador', 'danger');
                }
            }
        } catch (error) {
            console.error('Erro ao carregar colaborador:', error);
            if (window.App && window.App.notify) {
                window.App.notify('Erro ao carregar colaborador', 'danger');
            }
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
            if (window.App && window.App.notify) {
                window.App.notify('Colaborador removido com sucesso', 'success');
            }
            this.loadEmployees();
        } catch (error) {
            console.error('Erro ao remover colaborador:', error);
            if (window.App && window.App.notify) {
                window.App.notify('Erro ao remover colaborador', 'danger');
            }
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
        // Normalizar datas
        if (formData.has('hire_date') && !formData.get('hire_date')) formData.delete('hire_date');
        if (formData.has('birth_date') && !formData.get('birth_date')) formData.delete('birth_date');
        
        // Converter is_active para booleano
        if (formData.has('is_active')) {
            formData.set('is_active', formData.get('is_active') === 'on' ? 'true' : 'false');
        } else {
            formData.set('is_active', 'false');
        }
        
        // Remover campos vazios (exceto arquivo de foto e is_active)
        const keysToDelete = [];
        for (let key of formData.keys()) {
            const value = formData.get(key);
            // Se é arquivo vazio, deletar; se é outro campo vazio, deletar
            if (key === 'photo' && value && value instanceof File && value.size === 0) {
                keysToDelete.push(key);
            } else if (key !== 'is_active' && !value) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => formData.delete(key));
        
        // Log dos dados sendo enviados
        console.log('📦 Dados sendo enviados:');
        for (let [key, value] of formData.entries()) {
            if (value instanceof File) {
                console.log(`  ${key}: File(${value.name}, ${value.size} bytes)`);
            } else {
                console.log(`  ${key}: ${value}`);
            }
        }

        let response;
        if (employeeId && employeeId !== '') {
            // Atualizar
            response = await api.put(`/employees/${employeeId}`, formData);
            if (window.App && window.App.notify) {
                window.App.notify('Colaborador atualizado com sucesso', 'success');
            }
        } else {
            // Criar novo
            response = await api.post('/employees', formData);
            if (window.App && window.App.notify) {
                window.App.notify('Colaborador criado com sucesso', 'success');
            }
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
        if (window.App && window.App.notify) {
            window.App.notify(error.message || 'Erro ao salvar colaborador', 'danger');
        }
    }
}

/**
 * Deletar colaborador (versão global para o botão do modal)
 */
function deleteEmployee() {
    const employeeId = DOM.$('#employeeId')?.value;
    if (!employeeId) {
        if (window.App && window.App.notify) {
            window.App.notify('ID do colaborador não encontrado', 'danger');
        }
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
    
    if (status) {
        const isActive = status === 'true';
        filtered = filtered.filter(emp => emp.is_active === isActive);
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

/**
 * Sincroniza Cargo para Departamento
 */
function syncPositionToDepartment() {
    const positionSelect = DOM.$('#employeePosition');
    const departmentSelect = DOM.$('#employeeDepartment');
    
    if (positionSelect && departmentSelect && positionSelect.value) {
        departmentSelect.value = positionSelect.value;
    }
}

/**
 * Sincroniza Departamento para Cargo
 */
function syncDepartmentToPosition() {
    const departmentSelect = DOM.$('#employeeDepartment');
    const positionSelect = DOM.$('#employeePosition');
    
    if (departmentSelect && positionSelect && departmentSelect.value) {
        positionSelect.value = departmentSelect.value;
    }
}
