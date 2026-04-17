# MAC Calendar - Documentação Técnica

## Índice Geral

Esta documentação descreve todos os módulos, funções e endpoints da aplicação MAC Calendar.

### 📚 Estrutura da Documentação

1. **[API Endpoints](./01-API-ENDPOINTS.md)** - Documentação de todas as rotas da API
   - Autenticação
   - Colaboradores
   - Restaurantes
   - Calendário
   - Documentos
   - Dashboard
   - Perfil
   - AI/Posts

2. **[Modelos de Dados](./02-MODELOS.md)** - Estrutura dos modelos do banco de dados
   - Employee (Colaborador)
   - Restaurant (Restaurante)
   - CalendarEvent (Evento)
   - Document (Documento)

3. **[Utilitários](./03-UTILS.md)** - Funções auxiliares
   - Email
   - Document Generator
   - Helpers

4. **[Frontend - Módulos JS](./04-FRONTEND-MODULES.md)** - Módulos JavaScript
   - EmployeesModule
   - RestaurantsModule
   - CalendarModule
   - DocumentsModule
   - DashboardModule
   - ProfileModule

5. **[Middleware e Segurança](./05-MIDDLEWARE.md)** - Decorators e validações
   - Autenticação
   - Autorização
   - Validações

6. **[Configuração](./06-CONFIGURACAO.md)** - Settings e deployment
   - Variáveis de ambiente
   - Configurações do Flask
   - Deployment IIS

---

## 🚀 Início Rápido

### Instalação

```bash
# Clonar repositório
cd i:/server_apps/macalendar

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente
.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt

# Criar banco de dados
python run.py
```

### Configuração Básica

1. Copiar `.env.example` para `.env`
2. Configurar variáveis de ambiente (DATABASE_URL, SECRET_KEY, MAIL_*, etc.)
3. Executar: `python run.py`

### Acesso

- **URL Local**: http://localhost:6005/mac
- **URL Produção**: https://www.thecarv.com/mac

---

## 📋 Convenções

### Respostas da API

Todas as rotas da API retornam JSON com estrutura padrão:

**Sucesso:**
```json
{
  "message": "Operação realizada com sucesso",
  "data": { ... }
}
```

**Erro:**
```json
{
  "error": "Mensagem de erro descritiva"
}
```

### Códigos HTTP

- `200 OK` - Sucesso
- `201 Created` - Recurso criado
- `400 Bad Request` - Dados inválidos
- `401 Unauthorized` - Não autenticado
- `403 Forbidden` - Sem permissão
- `404 Not Found` - Recurso não encontrado
- `500 Internal Server Error` - Erro interno

### Autenticação

A aplicação suporta dois métodos de autenticação:

1. **Session-based** (web): Cookie de sessão após login
2. **JWT** (API): Token JWT no header `Authorization: Bearer <token>`

### Roles (Permissões)

- `admin` - Acesso total
- `rh` - Gestão de colaboradores e documentos
- `marketing` - Acesso a dashboards e relatórios
- `manager` - Gestão do próprio restaurante
- `employee` - Acesso básico (visualização)

---

## 🔧 Tecnologias

- **Backend**: Python 3.11, Flask
- **Database**: SQLite (desenvolvimento), SQL Server (produção)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Autenticação**: Flask-Session + JWT
- **Email**: SMTP (Gmail)
- **Deploy**: IIS + wfastcgi

---

## 📞 Suporte

Para dúvidas ou problemas:
- Email: suporte@thecarv.com
- Repositório: Internal GitLab

---

**Última atualização:** 18 de Dezembro de 2025
