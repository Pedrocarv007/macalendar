# Arquitetura e Fluxos - MAC Calendar

## Sumário

- [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
- [Fluxo de Autenticação](#fluxo-de-autenticação)
- [Fluxo de Gestão de Colaboradores](#fluxo-de-gestão-de-colaboradores)
- [Fluxo de Upload de Arquivos](#fluxo-de-upload-de-arquivos)
- [Matriz de Permissões](#matriz-de-permissões)
- [Diagramas](#diagramas)

---

## Visão Geral da Arquitetura

### Stack Tecnológico

```
Frontend
├── HTML5 + CSS3 (Bootstrap 5)
├── JavaScript (Vanilla ES6+)
│   ├── Módulos (EmployeesModule, RestaurantsModule, etc.)
│   ├── API Client (fetch)
│   └── State Management (appState)
└── Bibliotecas Externas
    ├── FullCalendar.js (Calendário)
    ├── Chart.js (Gráficos)
    └── Bootstrap Icons

Backend
├── Python 3.11
├── Flask (Web Framework)
├── SQLAlchemy (ORM)
├── Flask-Login (Session Management)
├── Flask-JWT-Extended (JWT Tokens)
├── Flask-Session (Server-side Sessions)
└── Flask-Mail (Email)

Database
├── SQLite (Desenvolvimento)
└── SQL Server (Produção)

Deployment
├── IIS + wfastcgi (Produção Windows)
├── Gunicorn + Nginx (Produção Linux)
└── Docker (Opcional)
```

---

### Estrutura de Diretórios

```
macalendar/
├── app/                        # Aplicação Flask
│   ├── __init__.py            # Factory da aplicação
│   ├── api/                   # Endpoints da API REST
│   │   ├── auth.py           # Autenticação
│   │   ├── employees.py      # Colaboradores
│   │   ├── restaurants.py    # Restaurantes
│   │   ├── calendar.py       # Calendário
│   │   ├── documents.py      # Documentos
│   │   ├── dashboard.py      # Dashboard/Stats
│   │   ├── profile.py        # Perfil do usuário
│   │   └── ai.py             # IA/Posts
│   ├── auth/                  # Rotas de autenticação web
│   │   └── routes.py
│   ├── web/                   # Rotas web (páginas HTML)
│   │   └── routes.py
│   ├── models/                # Modelos SQLAlchemy
│   │   ├── employee.py
│   │   ├── restaurant.py
│   │   ├── calendar_event.py
│   │   └── document.py
│   ├── middleware/            # Middleware/Decorators
│   │   └── security.py
│   ├── utils/                 # Utilitários
│   │   ├── email.py
│   │   ├── document_generator.py
│   │   └── helpers.py
│   ├── config/                # Configurações
│   │   ├── settings.py
│   │   └── database.py
│   ├── extensions/            # Extensões Flask
│   │   └── database.py
│   ├── static/                # Arquivos estáticos
│   │   ├── css/
│   │   ├── js/
│   │   │   ├── api-client.js
│   │   │   ├── app-state.js
│   │   │   └── modules/
│   │   ├── images/
│   │   └── uploads/          # Uploads de usuários
│   └── templates/             # Templates Jinja2
│       ├── base.html
│       ├── dashboard.html
│       ├── employees.html
│       └── ...
├── instance/                   # Dados sensíveis (não versionados)
│   └── macalendar.db         # Banco de dados SQLite
├── logs/                       # Logs da aplicação
├── flask_session/             # Sessões (server-side)
├── scripts/                   # Scripts utilitários
│   ├── init_db.py
│   └── backup.ps1
├── test/                      # Testes
│   ├── test_auth.py
│   └── test_restaurants.py
├── documentos/                # Documentação (esta pasta)
├── .env                       # Variáveis de ambiente
├── requirements.txt           # Dependências Python
├── run.py                     # Entry point da aplicação
├── web.config                 # Configuração IIS
├── docker-compose.yml         # Docker (opcional)
└── README.md                  # Readme do projeto
```

---

### Padrão de Arquitetura

**Arquitetura em Camadas:**

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (Templates HTML + JavaScript Modules)  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          API/Web Routes Layer           │
│     (Flask Blueprints + Endpoints)      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Business Logic Layer             │
│   (Models + Utils + Middleware)         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Data Access Layer               │
│      (SQLAlchemy ORM + Database)        │
└─────────────────────────────────────────┘
```

---

## Fluxo de Autenticação

### Fluxo Completo (Web + API)

```
1. Usuário acessa /mac/auth/login
   ↓
2. Preenche formulário (email + senha)
   ↓
3. POST /api/auth/login
   ↓
4. Backend valida credenciais
   ├─ Busca Employee por email
   ├─ Verifica is_active = True
   └─ Verifica senha (bcrypt)
   ↓
5. Se válido:
   ├─ Cria sessão (Flask-Session)
   ├─ Gera JWT token
   └─ Retorna user + token
   ↓
6. Frontend:
   ├─ Armazena token (opcional, para API)
   ├─ Atualiza appState.currentUser
   └─ Redireciona para /mac/dashboard
   ↓
7. Em requisições subsequentes:
   ├─ Web: Cookie de sessão (automático)
   └─ API: Header Authorization: Bearer <token>
```

---

### Diagrama de Sequência

```
Usuário          Frontend         Backend (Flask)      Database
   │                │                   │                  │
   │──login form───→│                   │                  │
   │                │                   │                  │
   │                │──POST /login─────→│                  │
   │                │  {email, pass}    │                  │
   │                │                   │──query Employee─→│
   │                │                   │                  │
   │                │                   │←─employee────────│
   │                │                   │                  │
   │                │                   │──check_password──│
   │                │                   │                  │
   │                │                   │──create session──│
   │                │                   │──generate JWT────│
   │                │                   │                  │
   │                │←─user + token─────│                  │
   │                │  Set-Cookie       │                  │
   │                │                   │                  │
   │←─redirect─────│                   │                  │
   │  /dashboard    │                   │                  │
   │                │                   │                  │
   │                │──GET /dashboard──→│                  │
   │                │  Cookie: session  │                  │
   │                │                   │──verify session──│
   │                │                   │                  │
   │                │←─HTML─────────────│                  │
   │←─render───────│                   │                  │
```

---

### Verificação de Autenticação

**Decorator `@api_login_required`:**

```python
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Tentar JWT
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                decoded = jwt.decode(token, SECRET_KEY)
                user_id = decoded.get('identity')
                user = Employee.query.get(user_id)
                if user and user.is_active:
                    g.current_user = user
                    return f(*args, **kwargs)
            except:
                pass
        
        # 2. Tentar Session
        user_id = session.get('user_id')
        if user_id:
            user = Employee.query.get(user_id)
            if user and user.is_active:
                g.current_user = user
                return f(*args, **kwargs)
        
        # 3. Não autenticado
        return jsonify({'error': 'Não autorizado'}), 401
    
    return decorated_function
```

---

## Fluxo de Gestão de Colaboradores

### Criar Colaborador (POST /api/employees)

```
1. Admin/RH abre modal "Novo Colaborador"
   ↓
2. Preenche formulário:
   ├─ Nome, email, telefone
   ├─ Cargo, departamento
   ├─ Restaurante
   ├─ Data de nascimento/contratação
   └─ Foto (opcional)
   ↓
3. Frontend: FormData → POST /api/employees
   ↓
4. Backend (@api_login_required + @require_roles(['admin', 'rh'])):
   ├─ Valida campos obrigatórios
   ├─ Valida formato de email
   ├─ Verifica email único
   ├─ Gera senha temporária (12 chars)
   ├─ Salva foto (se enviada)
   ├─ Cria Employee no DB
   │  └─ set_password(temp_password) → bcrypt hash
   └─ Envia email de boas-vindas (async)
      └─ Assunto: "Bem-vindo ao MAC Calendar"
      └─ Corpo: credenciais + link de login
   ↓
5. Retorna: {message: "Criado", employee: {...}}
   ↓
6. Frontend:
   ├─ Fecha modal
   ├─ Mostra toast de sucesso
   └─ Recarrega lista (await loadEmployees())
```

---

### Editar Colaborador (PUT /api/employees/<id>)

```
1. Usuário clica "Editar" em um colaborador
   ↓
2. Backend verifica permissões:
   ├─ Admin/RH: pode editar qualquer um
   ├─ Manager: apenas do próprio restaurante
   └─ Employee: apenas próprio perfil (via /profile/me)
   ↓
3. Frontend abre modal com dados preenchidos
   ↓
4. Usuário modifica campos
   ↓
5. Frontend: FormData → PUT /api/employees/{id}
   ↓
6. Backend:
   ├─ Valida campos (se modificados)
   ├─ Atualiza foto (se nova)
   ├─ Atualiza campos permitidos:
   │  ├─ Admin/RH: todos os campos
   │  ├─ Manager: campos básicos (exceto role)
   │  └─ Employee: apenas nome, telefone, endereço
   └─ Salva no DB
   ↓
7. Retorna: {message: "Atualizado", employee: {...}}
   ↓
8. Frontend:
   ├─ Fecha modal
   ├─ Mostra toast
   └─ Atualiza lista/grid
```

---

### Listar Colaboradores (GET /api/employees)

```
1. Usuário acessa /mac/employees
   ↓
2. Frontend: await api.get('/employees')
   ↓
3. Backend (@api_login_required):
   ├─ Identifica role do usuário (g.current_user.role)
   ├─ Aplica filtros por permissão:
   │  ├─ Admin/RH/Marketing: todos os colaboradores
   │  ├─ Manager: apenas do próprio restaurante
   │  └─ Employee: apenas ativos (sem info sensível)
   ├─ Query no banco:
   │  └─ SELECT * FROM employees WHERE ...
   └─ Serializa com to_dict()
   ↓
4. Retorna: {employees: [...]}
   ↓
5. Frontend (EmployeesModule):
   ├─ Armazena em this.employees
   ├─ Aplica filtros locais (busca, departamento, etc.)
   ├─ Verifica permissões para UI:
   │  └─ Oculta colunas sensíveis se role = 'employee'
   └─ Renderiza tabela/grid
```

---

### Matriz de Permissões (Colaboradores)

| Operação | Admin | RH | Manager | Employee |
|----------|-------|----|---------|---------| 
| Listar Todos | ✅ | ✅ | ❌ (só seu rest.) | ❌ (só ativos) |
| Ver Telefone | ✅ | ✅ | ✅ | ❌ |
| Ver Status | ✅ | ✅ | ✅ | ❌ |
| Criar | ✅ | ✅ | ❌ | ❌ |
| Editar Qualquer | ✅ | ✅ | ❌ | ❌ |
| Editar Próprio Rest. | ✅ | ✅ | ✅ | ❌ |
| Editar Próprio Perfil | ✅ | ✅ | ✅ | ✅ (limitado) |
| Alterar Role | ✅ | ❌ | ❌ | ❌ |
| Deletar | ✅ | ❌ | ❌ | ❌ |
| Upload Foto | ✅ | ✅ | ✅ (próprio rest.) | ✅ (própria) |

---

## Fluxo de Upload de Arquivos

### Upload de Foto de Colaborador

```
1. Usuário seleciona arquivo em <input type="file">
   ↓
2. Frontend valida:
   ├─ Arquivo selecionado?
   ├─ Extensão permitida? (jpg, png, gif)
   └─ Tamanho < 5MB?
   ↓
3. FormData.append('file', file)
   ↓
4. POST /api/employees/{id}/upload-photo
   ↓
5. Backend (@api_login_required):
   ├─ Verifica permissões (admin/rh/manager/próprio)
   ├─ Valida arquivo:
   │  ├─ file in request.files?
   │  ├─ Extensão permitida?
   │  └─ Tamanho < MAX_CONTENT_LENGTH?
   ├─ Gera nome único:
   │  └─ employee_{id}_{timestamp}.{ext}
   ├─ Salva em app/static/uploads/employees/
   ├─ Remove foto anterior (se existe)
   ├─ Atualiza employee.photo_filename no DB
   └─ Retorna URL da foto
   ↓
6. Frontend:
   ├─ Atualiza preview da imagem
   └─ Mostra toast de sucesso
```

---

### Estrutura de Uploads

```
app/static/uploads/
├── employees/           # Fotos de colaboradores
│   ├── employee_1_1702834567.jpg
│   ├── employee_2_1702834890.png
│   └── ...
├── restaurants/         # Fotos de restaurantes
│   ├── restaurant_1_1702835123.jpg
│   └── ...
└── documents/           # Documentos uploadados
    ├── report_1702835456.pdf
    ├── contract_1702835789.docx
    └── ...
```

---

## Matriz de Permissões

### Roles do Sistema

| Role | Descrição | Acesso |
|------|-----------|--------|
| `admin` | Administrador | Acesso total |
| `rh` | Recursos Humanos | Gestão de colaboradores e documentos |
| `marketing` | Marketing | Dashboard, relatórios, calendário |
| `manager` | Gerente de Restaurante | Gestão do próprio restaurante |
| `shift_manager` | Gerente de Turno | Visualização e calendário |
| `sub_manager` | Sub-gerente | Visualização e calendário |
| `rp` | RP | Visualização |
| `coucher` | Coucher | Visualização |
| `employee` | Colaborador | Visualização limitada |

---

### Matriz Completa de Permissões

| Recurso | Operação | admin | rh | marketing | manager | employee |
|---------|----------|-------|----|-----------|---------|---------| 
| **Colaboradores** |
| | Listar Todos | ✅ | ✅ | ✅ | ❌ | ❌ |
| | Listar Próprio Rest. | ✅ | ✅ | ✅ | ✅ | ❌ |
| | Ver Detalhes | ✅ | ✅ | ✅ | ✅ (próprio rest.) | ❌ |
| | Criar | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Editar | ✅ | ✅ | ❌ | ✅ (próprio rest.) | ❌ |
| | Deletar | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Upload Foto | ✅ | ✅ | ❌ | ✅ (próprio rest.) | ✅ (própria) |
| **Restaurantes** |
| | Listar | ✅ | ✅ | ✅ | ✅ (próprio) | ✅ (próprio) |
| | Ver Detalhes | ✅ | ✅ | ✅ | ✅ (próprio) | ✅ (próprio) |
| | Criar | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Editar | ✅ | ✅ | ❌ | ✅ (próprio) | ❌ |
| | Deletar | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Calendário** |
| | Ver Eventos | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Criar Evento | ✅ | ✅ | ✅ | ✅ | ❌ |
| | Editar Evento | ✅ | ✅ | ✅ | ✅ (próprio rest.) | ❌ |
| | Deletar Evento | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Documentos** |
| | Listar | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Ver/Download | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Upload | ✅ | ✅ | ❌ | ✅ | ❌ |
| | Deletar | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Dashboard** |
| | Ver Stats | ✅ | ✅ | ✅ | ✅ | ❌ |
| | Ver Relatórios | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Perfil** |
| | Ver Próprio | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Editar Próprio | ✅ | ✅ | ✅ | ✅ | ✅ (limitado) |
| | Alterar Senha | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Editar Cargo/Dept | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## Diagramas

### Diagrama ER (Entity-Relationship)

```
┌─────────────────┐         ┌──────────────────┐
│   Restaurant    │         │    Employee      │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │←────────│ id (PK)          │
│ name            │    1:N  │ name             │
│ address         │         │ email (UK)       │
│ phone           │         │ password_hash    │
│ email           │         │ phone            │
│ capacity        │         │ position         │
│ opening_hours   │         │ department       │
│ photo_filename  │         │ birth_date       │
│ manager_id (FK) │─────┐   │ hire_date        │
│ is_active       │     │   │ restaurant_id(FK)│
│ created_at      │     │   │ role             │
│ updated_at      │     │   │ photo_filename   │
└─────────────────┘     │   │ is_active        │
        │               │   │ created_at       │
        │               │   │ updated_at       │
        │               │   └──────────────────┘
        │               │            │
        │               └────────────┘
        │                   (manager)
        │
        │   1:N
        │
        ↓
┌──────────────────┐
│  CalendarEvent   │
├──────────────────┤
│ id (PK)          │
│ title            │
│ description      │
│ start_date       │
│ end_date         │
│ location         │
│ event_type       │
│ restaurant_id(FK)│───→ Restaurant
│ created_by (FK)  │───→ Employee
│ all_day          │
│ color            │
│ created_at       │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│    Document      │
├──────────────────┤
│ id (PK)          │
│ title            │
│ description      │
│ document_type    │
│ file_path        │
│ file_size        │
│ restaurant_id(FK)│───→ Restaurant
│ created_by (FK)  │───→ Employee
│ created_at       │
│ updated_at       │
└──────────────────┘
```

---

### Fluxo de Request (API)

```
Cliente (Browser/App)
        │
        │ HTTP Request
        │ GET /mac/api/employees
        │ Cookie: session_id=...
        │
        ↓
┌───────────────────────┐
│   IIS / Nginx         │  (Reverse Proxy)
└───────────────────────┘
        │
        ↓
┌───────────────────────┐
│   wfastcgi / Gunicorn │  (WSGI Server)
└───────────────────────┘
        │
        ↓
┌───────────────────────┐
│   Flask Application   │
│                       │
│ 1. Routing            │  (app/api/employees.py)
│ 2. Middleware         │  (@api_login_required)
│ 3. Authorization      │  (@require_roles)
│ 4. Business Logic     │  (get_employees)
│ 5. Database Query     │  (Employee.query.all())
└───────────────────────┘
        │
        ↓
┌───────────────────────┐
│   SQLAlchemy ORM      │
└───────────────────────┘
        │
        ↓
┌───────────────────────┐
│   Database            │  (SQLite / SQL Server)
│   - employees         │
│   - restaurants       │
│   - calendar_events   │
│   - documents         │
└───────────────────────┘
        │
        │ Results
        │
        ↓
┌───────────────────────┐
│   Flask Application   │
│                       │
│ 1. Serialize (to_dict)│
│ 2. JSON Response      │
│ 3. HTTP Headers       │
└───────────────────────┘
        │
        │ HTTP Response
        │ 200 OK
        │ {employees: [...]}
        │
        ↓
Cliente (Browser/App)
        │
        │ JavaScript
        │ api.get('/employees')
        │
        ↓
┌───────────────────────┐
│   EmployeesModule     │
│                       │
│ 1. Store in state     │
│ 2. Apply filters      │
│ 3. Render UI          │
│    - displayTable()   │
│    - displayGrid()    │
└───────────────────────┘
```

---

**Última atualização:** 18 de Dezembro de 2025
