# Frontend - Módulos JavaScript - MAC Calendar

## Sumário

- [Arquitetura](#arquitetura)
- [API Client (api-client.js)](#api-client)
- [App State (app-state.js)](#app-state)
- [EmployeesModule (modules/employees.js)](#employeesmodule)
- [RestaurantsModule (modules/restaurants.js)](#restaurantsmodule)
- [CalendarModule (modules/calendar.js)](#calendarmodule)
- [DocumentsModule (modules/documents.js)](#documentsmodule)
- [DashboardModule (modules/dashboard.js)](#dashboardmodule)
- [ProfileModule (modules/profile.js)](#profilemodule)
- [DOM Utilities (dom.js)](#dom-utilities)

---

## Arquitetura

### Estrutura de Pastas
```
app/static/js/
├── api-client.js         # Cliente HTTP para API
├── app-state.js          # Gerenciamento de estado global
├── app.js                # Inicialização e roteamento
├── dom.js                # Utilitários DOM
├── utils.js              # Funções auxiliares
├── main.js               # Entry point
└── modules/
    ├── calendar.js       # Módulo de calendário
    ├── dashboard.js      # Módulo de dashboard
    ├── documents.js      # Módulo de documentos
    ├── employees.js      # Módulo de colaboradores
    ├── profile.js        # Módulo de perfil
    └── restaurants.js    # Módulo de restaurantes
```

### Padrão de Módulos

Todos os módulos seguem a estrutura:

```javascript
class ModuleName {
    constructor() {
        this.data = [];
        this.filters = {};
        this.init();
    }

    async init() {
        // Inicialização
        await this.loadData();
        this.setupEventListeners();
        this.render();
    }

    async loadData() {
        // Carregar dados da API
    }

    setupEventListeners() {
        // Configurar listeners de eventos
    }

    render() {
        // Renderizar UI
    }
}
```

---

## API Client

### Descrição
Cliente HTTP centralizado para todas as chamadas à API. Gerencia autenticação, headers e tratamento de erros.

### Arquivo: `app/static/js/api-client.js`

---

### Propriedades

```javascript
api = {
    baseURL: '/mac/api',  // Base URL da API
    token: null,          // JWT token (se usando)
}
```

---

### Métodos

#### `api.get(endpoint, options = {})`
Realiza requisição GET.

**Parâmetros:**
- `endpoint`: Caminho do endpoint (ex: '/employees')
- `options`: Objeto com opções adicionais

**Retorno:** Promise com resposta JSON

**Exemplo:**
```javascript
// Listar colaboradores
const response = await api.get('/employees');
console.log(response.employees);

// Com query params
const response = await api.get('/employees', {
    params: { restaurant_id: 1, is_active: true }
});

// Com headers customizados
const response = await api.get('/employees', {
    headers: { 'X-Custom-Header': 'value' }
});
```

---

#### `api.post(endpoint, data, options = {})`
Realiza requisição POST.

**Parâmetros:**
- `endpoint`: Caminho do endpoint
- `data`: Objeto ou FormData a enviar
- `options`: Opções adicionais

**Retorno:** Promise com resposta JSON

**Exemplo:**
```javascript
// Criar colaborador (JSON)
const newEmployee = await api.post('/employees', {
    name: 'Maria Santos',
    email: 'maria@example.com',
    position: 'colaborador',
    restaurant_id: 1
});

// Com FormData (upload de arquivo)
const formData = new FormData();
formData.append('name', 'João Silva');
formData.append('photo', fileInput.files[0]);

const employee = await api.post('/employees', formData);
```

---

#### `api.put(endpoint, data, options = {})`
Realiza requisição PUT (atualização).

**Exemplo:**
```javascript
// Atualizar colaborador
const updated = await api.put('/employees/1', {
    name: 'Maria Santos Silva',
    phone: '+351 912 345 678'
});
```

---

#### `api.delete(endpoint, options = {})`
Realiza requisição DELETE.

**Exemplo:**
```javascript
// Deletar colaborador
await api.delete('/employees/1');
console.log('Colaborador removido');
```

---

### Tratamento de Erros

O API client automaticamente trata erros:

```javascript
try {
    const data = await api.get('/employees');
} catch (error) {
    if (error.status === 401) {
        // Redirecionar para login
        window.location.href = '/mac/auth/login';
    } else if (error.status === 403) {
        alert('Sem permissão para esta operação');
    } else {
        alert(error.message || 'Erro ao carregar dados');
    }
}
```

---

### Autenticação

```javascript
// Definir token JWT (se usando)
api.token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';

// Token é automaticamente incluído nos headers:
// Authorization: Bearer <token>

// Session-based (padrão)
// Cookies são enviados automaticamente com credentials: 'include'
```

---

## App State

### Descrição
Gerenciamento de estado global da aplicação (usuário, configurações, dados compartilhados).

### Arquivo: `app/static/js/app-state.js`

---

### Estrutura

```javascript
const appState = {
    currentUser: null,          // Usuário logado
    restaurants: [],            // Lista de restaurantes
    employees: [],              // Lista de colaboradores
    currentRestaurant: null,    // Restaurante selecionado
    filters: {},                // Filtros ativos
    viewMode: 'list',           // Modo de visualização ('list' ou 'grid')
};
```

---

### Métodos

#### `appState.setCurrentUser(user)`
Define usuário logado.

**Exemplo:**
```javascript
const user = await api.get('/auth/user');
appState.setCurrentUser(user);

console.log(appState.currentUser.name);  // "João Silva"
console.log(appState.currentUser.role);  // "admin"
```

---

#### `appState.hasPermission(permission)`
Verifica se usuário tem permissão.

**Parâmetros:**
- `permission`: String ou array de roles permitidas

**Retorno:** Boolean

**Exemplo:**
```javascript
// Verificar role específico
if (appState.hasPermission('admin')) {
    showAdminButtons();
}

// Verificar múltiplos roles
if (appState.hasPermission(['admin', 'rh'])) {
    showEmployeeManagement();
}

// No código
function canEditEmployee(employee) {
    const currentUser = appState.currentUser;
    
    if (appState.hasPermission(['admin', 'rh'])) {
        return true;
    }
    
    if (appState.hasPermission('manager')) {
        return employee.restaurant_id === currentUser.restaurant_id;
    }
    
    return false;
}
```

---

#### `appState.updateRestaurants(restaurants)`
Atualiza lista de restaurantes no estado.

**Exemplo:**
```javascript
const data = await api.get('/restaurants');
appState.updateRestaurants(data.restaurants);
```

---

## EmployeesModule

### Descrição
Módulo para gestão de colaboradores (listagem, criação, edição, upload de fotos).

### Arquivo: `app/static/js/modules/employees.js`

---

### Propriedades

```javascript
class EmployeesModule {
    constructor() {
        this.employees = [];            // Lista de colaboradores
        this.filteredEmployees = [];    // Lista filtrada
        this.viewMode = 'list';         // 'list' ou 'grid'
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.filters = {
            search: '',
            restaurant: '',
            department: '',
            isActive: true
        };
    }
}
```

---

### Métodos Principais

#### `async loadEmployees()`
Carrega colaboradores da API.

**Exemplo:**
```javascript
const module = new EmployeesModule();
await module.loadEmployees();
console.log(module.employees.length);
```

---

#### `filterEmployees()`
Aplica filtros à lista de colaboradores.

**Exemplo:**
```javascript
// Filtrar por texto
module.filters.search = 'maria';
module.filterEmployees();

// Filtrar por restaurante
module.filters.restaurant = '1';
module.filterEmployees();

// Filtrar por departamento
module.filters.department = 'Gerente_loja';
module.filterEmployees();
```

---

#### `displayTable()`
Renderiza tabela de colaboradores.

**Comportamento:**
- Verifica permissões do usuário
- Oculta colunas sensíveis (telefone, status, ações) para role `employee`
- Mostra todas as colunas para `admin` e `rh`

**Exemplo de HTML gerado:**
```html
<table class="table">
    <thead id="employeesTableHead">
        <tr>
            <th>Nome</th>
            <th>Email</th>
            <th>Cargo</th>
            <th>Departamento</th>
            <th>Restaurante</th>
            <!-- Apenas admin/rh -->
            <th>Telefone</th>
            <th>Status</th>
            <th>Ações</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>
                <img src="/uploads/employees/photo.jpg" class="rounded-circle" width="30">
                João Silva
            </td>
            <td>joao@example.com</td>
            <td>Gerente_loja</td>
            <td>Gerente_loja</td>
            <td>Restaurante Central</td>
            <td>+351 912 345 678</td>
            <td><span class="badge bg-success">Ativo</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editEmployee(1)">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteEmployee(1)">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    </tbody>
</table>
```

---

#### `displayGrid()`
Renderiza grid de cards de colaboradores.

**Exemplo de HTML gerado:**
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <div class="card employee-card">
            <img src="/uploads/employees/photo.jpg" class="card-img-top">
            <div class="card-body">
                <h5 class="card-title">João Silva</h5>
                <p class="card-text">
                    <strong>Cargo:</strong> Gerente_loja<br>
                    <strong>Restaurante:</strong> Restaurante Central
                </p>
                <!-- Botões de ação (apenas admin/rh) -->
                <div class="btn-group">
                    <button class="btn btn-primary">Editar</button>
                    <button class="btn btn-danger">Remover</button>
                </div>
            </div>
        </div>
    </div>
</div>
```

---

#### `async saveEmployee(formData)`
Salva colaborador (criar ou editar).

**Parâmetros:**
- `formData`: FormData com dados do colaborador

**Exemplo:**
```javascript
// Capturar formulário
const form = document.getElementById('employeeForm');
const formData = new FormData(form);

// Adicionar campos extras
formData.append('restaurant_id', '1');

// Salvar
try {
    await module.saveEmployee(formData);
    alert('Colaborador salvo com sucesso');
    $('#employeeModal').modal('hide');
    await module.loadEmployees();
} catch (error) {
    alert('Erro ao salvar: ' + error.message);
}
```

---

#### `async uploadPhoto(employeeId, file)`
Faz upload de foto do colaborador.

**Parâmetros:**
- `employeeId`: ID do colaborador
- `file`: Objeto File da foto

**Exemplo:**
```javascript
// Input de arquivo
const photoInput = document.getElementById('employeePhoto');
photoInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        try {
            await module.uploadPhoto(currentEmployeeId, file);
            alert('Foto enviada com sucesso');
            await module.loadEmployees();
        } catch (error) {
            alert('Erro ao enviar foto');
        }
    }
});
```

---

#### `async deleteEmployee(employeeId)`
Remove colaborador.

**Exemplo:**
```javascript
async function deleteEmployee(id) {
    if (confirm('Tem certeza que deseja remover este colaborador?')) {
        try {
            await module.deleteEmployee(id);
            alert('Colaborador removido');
            await module.loadEmployees();
        } catch (error) {
            alert('Erro ao remover');
        }
    }
}
```

---

### Event Listeners

```javascript
setupEventListeners() {
    // Botão "Novo Colaborador"
    document.getElementById('btnNewEmployee')
        .addEventListener('click', () => this.openEmployeeModal());
    
    // Filtro de busca
    document.getElementById('searchInput')
        .addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.filterEmployees();
        });
    
    // Filtro de restaurante
    document.getElementById('restaurantFilter')
        .addEventListener('change', (e) => {
            this.filters.restaurant = e.target.value;
            this.filterEmployees();
        });
    
    // Toggle view mode
    document.getElementById('viewModeList')
        .addEventListener('click', () => {
            this.viewMode = 'list';
            this.render();
        });
    
    document.getElementById('viewModeGrid')
        .addEventListener('click', () => {
            this.viewMode = 'grid';
            this.render();
        });
    
    // Formulário de colaborador
    document.getElementById('employeeForm')
        .addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await this.saveEmployee(formData);
        });
}
```

---

### Permissões

```javascript
// Verificar se pode editar
function canEditEmployee(employee) {
    const currentUser = appState.currentUser;
    
    if (['admin', 'rh'].includes(currentUser.role)) {
        return true;
    }
    
    if (currentUser.role === 'manager') {
        return employee.restaurant_id === currentUser.restaurant_id;
    }
    
    return false;
}

// Verificar se pode ver telefone/status
function canViewSensitiveData() {
    const currentUser = appState.currentUser;
    return ['admin', 'rh'].includes(currentUser.role);
}
```

---

## RestaurantsModule

### Descrição
Módulo para gestão de restaurantes.

### Arquivo: `app/static/js/modules/restaurants.js`

---

### Métodos Principais

#### `async loadRestaurants()`
Carrega restaurantes da API.

#### `async saveRestaurant(data)`
Salva restaurante (criar ou editar).

**Exemplo:**
```javascript
const restaurantData = {
    name: 'Novo Restaurante',
    address: 'Rua XYZ, 456',
    phone: '+351 913 456 789',
    email: 'novo@example.com',
    capacity: 80,
    opening_hours: '09:00 - 23:00',
    manager_id: 3
};

await module.saveRestaurant(restaurantData);
```

#### `displayTable()` / `displayGrid()`
Renderiza lista/grid de restaurantes.

---

## CalendarModule

### Descrição
Módulo para gestão de eventos do calendário (usa FullCalendar.js).

### Arquivo: `app/static/js/modules/calendar.js`

---

### Dependências

```html
<!-- FullCalendar CSS -->
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/main.min.css" rel="stylesheet">

<!-- FullCalendar JS -->
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js"></script>
```

---

### Métodos Principais

#### `async initCalendar()`
Inicializa o calendário.

**Exemplo:**
```javascript
const module = new CalendarModule();
await module.initCalendar();

// Configuração do FullCalendar
const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'pt',
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    events: async (info, successCallback) => {
        const events = await module.loadEvents(info.start, info.end);
        successCallback(events);
    },
    eventClick: (info) => {
        module.openEventModal(info.event);
    },
    dateClick: (info) => {
        module.openEventModal(null, info.date);
    }
});

calendar.render();
```

---

#### `async loadEvents(startDate, endDate)`
Carrega eventos de um período.

**Exemplo:**
```javascript
const events = await module.loadEvents(
    new Date('2024-12-01'),
    new Date('2024-12-31')
);

// Formato de eventos FullCalendar:
/*
[
    {
        id: 1,
        title: 'Reunião de Equipe',
        start: '2024-12-20T10:00:00',
        end: '2024-12-20T12:00:00',
        color: '#007bff',
        extendedProps: {
            description: 'Reunião mensal',
            location: 'Sala 1',
            restaurant_id: 1
        }
    }
]
*/
```

---

#### `async saveEvent(eventData)`
Salva evento (criar ou editar).

**Exemplo:**
```javascript
const eventData = {
    title: 'Nova Reunião',
    start_date: '2024-12-25T14:00:00',
    end_date: '2024-12-25T16:00:00',
    description: 'Reunião de fim de ano',
    location: 'Restaurante Central',
    event_type: 'meeting',
    restaurant_id: 1,
    all_day: false
};

await module.saveEvent(eventData);
```

---

## DocumentsModule

### Descrição
Módulo para gestão de documentos (upload, listagem, download).

### Arquivo: `app/static/js/modules/documents.js`

---

### Métodos Principais

#### `async loadDocuments()`
Carrega documentos da API.

#### `async uploadDocument(formData)`
Faz upload de documento.

**Exemplo:**
```javascript
const formData = new FormData();
formData.append('title', 'Relatório Mensal');
formData.append('description', 'Relatório de vendas');
formData.append('document_type', 'report');
formData.append('restaurant_id', '1');
formData.append('file', fileInput.files[0]);

await module.uploadDocument(formData);
```

---

## DashboardModule

### Descrição
Módulo para dashboard com estatísticas e gráficos (usa Chart.js).

### Arquivo: `app/static/js/modules/dashboard.js`

---

### Dependências

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

---

### Métodos Principais

#### `async loadStats()`
Carrega estatísticas do dashboard.

#### `renderCharts()`
Renderiza gráficos.

**Exemplo:**
```javascript
// Gráfico de colaboradores por restaurante
const ctx = document.getElementById('employeesChart').getContext('2d');
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Rest. 1', 'Rest. 2', 'Rest. 3'],
        datasets: [{
            label: 'Colaboradores',
            data: [15, 22, 18],
            backgroundColor: 'rgba(54, 162, 235, 0.5)'
        }]
    }
});
```

---

## ProfileModule

### Descrição
Módulo para perfil do usuário (visualização, edição, alteração de senha).

### Arquivo: `app/static/js/modules/profile.js`

---

### Métodos Principais

#### `async loadProfile()`
Carrega dados do perfil.

#### `async updateProfile(data)`
Atualiza perfil.

**Exemplo:**
```javascript
const profileData = {
    name: 'João Silva',
    phone: '+351 912 345 678',
    address: 'Novo endereço'
};

await module.updateProfile(profileData);
```

#### `async changePassword(currentPassword, newPassword)`
Altera senha.

**Exemplo:**
```javascript
try {
    await module.changePassword('senhaAtual', 'novaSenha123!');
    alert('Senha alterada com sucesso');
} catch (error) {
    alert('Senha atual incorreta');
}
```

---

## DOM Utilities

### Descrição
Funções auxiliares para manipulação do DOM.

### Arquivo: `app/static/js/dom.js`

---

### Funções

#### `showLoading()`
Mostra indicador de carregamento.

```javascript
showLoading();
await api.get('/employees');
hideLoading();
```

#### `showToast(message, type)`
Mostra notificação toast.

```javascript
showToast('Colaborador salvo com sucesso', 'success');
showToast('Erro ao salvar', 'error');
```

#### `confirmDialog(message)`
Mostra diálogo de confirmação.

```javascript
const confirmed = await confirmDialog('Tem certeza?');
if (confirmed) {
    await deleteEmployee(id);
}
```

---

**Última atualização:** 18 de Dezembro de 2025
