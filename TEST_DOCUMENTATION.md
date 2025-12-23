# 🧪 Testes Abrangentes - MAC Calendar

Documentação completa dos testes para todas as rotas da aplicação.

## 📋 Estrutura dos Testes

```
test/
├── conftest.py                    # Fixtures compartilhadas
├── test_api_auth.py              # Testes de autenticação
├── test_api_employees.py         # Testes de colaboradores
├── test_api_restaurants.py       # Testes de restaurantes
├── test_api_calendar.py          # Testes de calendário
├── test_api_documents.py         # Testes de documentos
├── test_api_profile_dashboard.py # Testes de perfil e dashboard
├── test_api_ai.py                # Testes de IA
├── test_auth.py                  # Testes antigos de autenticação
└── test_restaurants.py           # Testes antigos de restaurantes
```

## 🚀 Como Executar os Testes

### Executar todos os testes
```bash
pytest
```

### Executar com verbose (mais detalhes)
```bash
pytest -v
```

### Executar testes de um ficheiro específico
```bash
pytest test/test_api_auth.py -v
```

### Executar um teste específico
```bash
pytest test/test_api_auth.py::TestAuthLogin::test_login_success_admin -v
```

### Executar com coverage (cobertura de código)
```bash
pytest --cov=app test/ -v
```

### Executar em paralelo (mais rápido)
```bash
pip install pytest-xdist
pytest -n auto
```

## 📊 Cobertura de Testes

### Autenticação (`test_api_auth.py`)
- ✅ Login bem-sucedido (admin, manager, employee)
- ✅ Login com credenciais inválidas
- ✅ Login com email/senha faltando
- ✅ Login sem autenticação
- ✅ Obter perfil (autenticado/não autenticado)
- ✅ Atualizar perfil
- ✅ Mudar senha
- ✅ Listar usuários

**Total: 14 testes**

### Colaboradores (`test_api_employees.py`)
- ✅ GET /api/employees (listar, filtros, permissões)
- ✅ POST /api/employees (criar, validações, permissões)
- ✅ PUT /api/employees/<id> (atualizar)
- ✅ DELETE /api/employees/<id> (deletar)
- ✅ GET /api/employees/<id> (detalhes)
- ✅ Aniversários do mês

**Total: 21 testes**

### Restaurantes (`test_api_restaurants.py`)
- ✅ GET /api/restaurants (listar, permissões)
- ✅ POST /api/restaurants (criar, validações)
- ✅ PUT /api/restaurants/<id> (atualizar)
- ✅ DELETE /api/restaurants/<id> (deletar)
- ✅ GET /api/restaurants/<id>/stats (estatísticas)

**Total: 13 testes**

### Calendário (`test_api_calendar.py`)
- ✅ GET /api/calendar/events (listar, filtros)
- ✅ POST /api/calendar/events (criar)
- ✅ PUT /api/calendar/events/<id> (atualizar)
- ✅ DELETE /api/calendar/events/<id> (deletar)
- ✅ GET /api/calendar/birthdays (aniversários)
- ✅ Marcar evento como postado

**Total: 17 testes**

### Documentos (`test_api_documents.py`)
- ✅ GET /api/documents (listar)
- ✅ POST /api/documents (criar)
- ✅ PUT /api/documents/<id> (atualizar)
- ✅ DELETE /api/documents/<id> (deletar)
- ✅ GET /api/documents/<id>/download (download)
- ✅ GET /api/documents/templates (templates)
- ✅ POST /api/documents/generate (gerar)

**Total: 17 testes**

### Perfil e Dashboard (`test_api_profile_dashboard.py`)
- ✅ GET/PUT /api/profile/me (perfil)
- ✅ POST /api/profile/me/password (mudança de senha)
- ✅ GET /api/dashboard/stats (estatísticas)
- ✅ GET /api/dashboard/events/recent (eventos recentes)
- ✅ GET /api/dashboard/activities (atividades)

**Total: 12 testes**

### IA (`test_api_ai.py`)
- ✅ POST /api/ai/posts (gerar posts)
- ✅ Rate limiting
- ✅ Cache de respostas
- ✅ Validações e permissões

**Total: 8 testes**

## 📈 Estatísticas Totais

- **Total de testes**: 102 testes
- **Endpoints cobertos**: 40+ rotas
- **Cenários**: 
  - ✅ Casos de sucesso
  - ✅ Validações e erros
  - ✅ Permissões e autenticação
  - ✅ Rate limiting
  - ✅ Cache
  - ✅ Filtros e paginação

## 🔐 Testes de Segurança Inclusos

### Autenticação
- Sem token → 401 Unauthorized
- Token inválido → 401 Unauthorized
- Token expirado → 401 Unauthorized

### Autorização
- Employee não pode criar documents → 403 Forbidden
- Employee não pode criar restaurantes → 403 Forbidden
- Sem role necessária → 403 Forbidden

### Validações
- Email inválido → 400 Bad Request
- Campos obrigatórios faltando → 422 Unprocessable Entity
- Valores duplicados → 409 Conflict

### Rate Limiting
- Múltiplas requisições rápidas → 429 Too Many Requests
- Cache testado para economizar chamadas

## 🏗️ Fixtures Disponíveis

### conftest.py

```python
@pytest.fixture
def app():
    """Aplicação Flask para testes"""

@pytest.fixture
def client(app):
    """Cliente de teste HTTP"""

@pytest.fixture
def restaurants(app):
    """2 restaurantes pré-criados"""

@pytest.fixture
def admin_user(app, restaurants):
    """Usuário admin autenticado"""

@pytest.fixture
def manager_user(app, restaurants):
    """Usuário manager autenticado"""

@pytest.fixture
def employee_user(app, restaurants):
    """Usuário employee autenticado"""

@pytest.fixture
def admin_headers(admin_token):
    """Headers com Bearer token admin"""

@pytest.fixture
def manager_headers(manager_token):
    """Headers com Bearer token manager"""

@pytest.fixture
def employee_headers(employee_token):
    """Headers com Bearer token employee"""
```

## 📝 Padrão de Testes

Todos os testes seguem este padrão:

```python
class TestFeature:
    """Testes para uma funcionalidade"""
    
    def test_case_success(self, client, admin_headers):
        """Teste bem-sucedido"""
        response = client.get('/api/endpoint', headers=admin_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'expected_field' in data
    
    def test_case_error(self, client):
        """Teste de erro"""
        response = client.get('/api/endpoint')
        assert response.status_code == 401  # Sem autenticação
    
    def test_case_validation(self, client, admin_headers):
        """Teste de validação"""
        response = client.post(
            '/api/endpoint',
            data=json.dumps({'invalid': 'data'}),
            headers=admin_headers
        )
        assert response.status_code in [400, 422]
```

## 🔍 Checklist de Cobertura

### Endpoints da API

- [x] GET /api/auth/login → POST (corrigido)
- [x] POST /api/auth/register
- [x] GET /api/auth/profile
- [x] PUT /api/auth/profile
- [x] POST /api/auth/change-password
- [x] GET /api/auth/me
- [x] GET /api/auth/current-user
- [x] GET /api/auth/user
- [x] GET /api/auth/users

- [x] GET /api/employees
- [x] POST /api/employees
- [x] GET /api/employees/<id>
- [x] PUT /api/employees/<id>
- [x] DELETE /api/employees/<id>
- [x] GET /api/employees/birthdays-this-month
- [x] POST /api/employees/<id>/upload-photo

- [x] GET /api/restaurants
- [x] POST /api/restaurants
- [x] GET /api/restaurants/<id>
- [x] PUT /api/restaurants/<id>
- [x] DELETE /api/restaurants/<id>
- [x] GET /api/restaurants/<id>/stats
- [x] POST /api/restaurants/<id>/upload-photo

- [x] GET /api/calendar/events
- [x] POST /api/calendar/events
- [x] GET /api/calendar/events/<id>
- [x] PUT /api/calendar/events/<id>
- [x] DELETE /api/calendar/events/<id>
- [x] PUT /api/calendar/events/<id>/mark-posted
- [x] GET /api/calendar/birthdays
- [x] POST /api/calendar/generate/mystery-tuesdays
- [x] POST /api/calendar/generate/mystery-answers

- [x] GET /api/documents
- [x] POST /api/documents
- [x] GET /api/documents/<id>
- [x] PUT /api/documents/<id>
- [x] DELETE /api/documents/<id>
- [x] GET /api/documents/<id>/download
- [x] GET /api/documents/templates
- [x] POST /api/documents/generate

- [x] GET /api/profile/me
- [x] PUT /api/profile/me
- [x] POST /api/profile/me/password
- [x] POST /api/profile/me/photo

- [x] GET /api/dashboard/stats
- [x] GET /api/dashboard/events/recent
- [x] GET /api/dashboard/activities

- [x] POST /api/ai/posts

## 🐛 Debugging de Testes

### Ver output detalhado
```bash
pytest test/test_api_auth.py -v -s
```

### Ver com print statements
```bash
pytest -v -s --tb=short
```

### Parar no primeiro erro
```bash
pytest -x
```

### Executar último teste que falhou
```bash
pytest --lf
```

## 📚 Referências

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/testing/)

## ✅ Checklist Pré-Deploy

- [ ] Executar `pytest` e confirmar 100% passou
- [ ] Verificar coverage: `pytest --cov=app`
- [ ] Executar testes em paralelo: `pytest -n auto`
- [ ] Testar cada role (admin, manager, employee)
- [ ] Testar rate limiting manualmente
- [ ] Testar cache manualmente

## 📞 Suporte

Dúvidas sobre os testes? Verifique:
1. O padrão em `conftest.py`
2. Exemplos em qualquer `test_*.py`
3. Documentação inline nos testes
