# API Endpoints - MAC Calendar

## Sumário

- [Autenticação](#autenticação)
- [Colaboradores](#colaboradores)
- [Restaurantes](#restaurantes)
- [Calendário](#calendário)
- [Documentos](#documentos)
- [Dashboard](#dashboard)
- [Perfil](#perfil)
- [AI/Posts](#aiposts)

---

## Autenticação

### POST `/api/auth/login`
Realiza login e cria sessão/token.

**Parâmetros (JSON):**
```json
{
  "email": "user@example.com",
  "password": "senha123"
}
```

**Resposta (200):**
```json
{
  "message": "Login realizado com sucesso",
  "user": {
    "id": 1,
    "name": "João Silva",
    "email": "user@example.com",
    "role": "admin",
    "restaurant_id": 1
  },
  "access_token": "eyJ..."
}
```

**Erros:**
- `401` - Credenciais inválidas
- `400` - Email/senha não fornecidos

---

### GET `/api/auth/user`
Retorna dados do usuário autenticado.

**Headers:** Requer autenticação (Session ou JWT)

**Resposta (200):**
```json
{
  "id": 1,
  "name": "João Silva",
  "email": "user@example.com",
  "role": "admin",
  "restaurant_id": 1,
  "photo_filename": "photo_123.jpg"
}
```

---

### GET `/api/auth/logout`
Encerra sessão do usuário.

**Resposta (200):**
```json
{
  "message": "Logout realizado com sucesso"
}
```

---

## Colaboradores

### GET `/api/employees`
Lista todos os colaboradores (com filtros de permissão).

**Permissões:** Login obrigatório
- `admin`, `rh`, `marketing`: Veem todos
- `manager`: Veem apenas do próprio restaurante
- `employee`: Veem apenas colaboradores ativos

**Query Params (opcional):**
- `restaurant_id` - Filtrar por restaurante
- `is_active` - Filtrar por status (true/false)
- `department` - Filtrar por departamento

**Resposta (200):**
```json
{
  "employees": [
    {
      "id": 1,
      "name": "João Silva",
      "email": "joao@example.com",
      "position": "Gerente_loja",
      "department": "Gerente_loja",
      "phone": "+351 912 345 678",
      "birth_date": "1990-05-15",
      "hire_date": "2020-01-10",
      "restaurant_id": 1,
      "restaurant_name": "Restaurante Central",
      "is_active": true,
      "photo_filename": "employee_1.jpg",
      "photo_url": "/uploads/employees/employee_1.jpg"
    }
  ]
}
```

---

### POST `/api/employees`
Cria novo colaborador.

**Permissões:** `admin`, `rh`

**Body (FormData ou JSON):**
```json
{
  "name": "Maria Santos",
  "email": "maria@example.com",
  "phone": "+351 911 222 333",
  "position": "colaborador",
  "department": "colaborador",
  "birth_date": "1995-08-20",
  "hire_date": "2024-01-15",
  "restaurant_id": 1,
  "address": "Rua X, 123",
  "notes": "Observações",
  "is_active": true
}
```

**Com foto (FormData):**
- Campo `photo`: arquivo de imagem (JPG/PNG/GIF)

**Resposta (201):**
```json
{
  "message": "Colaborador criado com sucesso",
  "employee": { ... }
}
```

**Comportamento:**
- Gera senha temporária automática
- Envia email de boas-vindas com credenciais
- Valida email único
- Valida formato de telefone

**Erros:**
- `400` - Dados inválidos
- `409` - Email já existe
- `403` - Sem permissão

---

### PUT `/api/employees/<id>`
Atualiza colaborador existente.

**Permissões:** 
- `admin`, `rh`: Podem editar qualquer campo
- `manager`: Apenas do próprio restaurante

**Body (FormData ou JSON):** Mesmos campos do POST (todos opcionais)

**Resposta (200):**
```json
{
  "message": "Colaborador atualizado com sucesso",
  "employee": { ... }
}
```

---

### DELETE `/api/employees/<id>`
Remove colaborador (soft delete - marca como inativo).

**Permissões:** `admin`

**Resposta (200):**
```json
{
  "message": "Colaborador removido com sucesso"
}
```

---

### POST `/api/employees/<id>/upload-photo`
Faz upload da foto do colaborador.

**Permissões:** `admin`, `rh`, `manager` (próprio restaurante)

**Body (multipart/form-data):**
- `file`: Imagem (JPG/PNG/GIF, máx 5MB)

**Resposta (200):**
```json
{
  "message": "Foto enviada com sucesso",
  "photo_filename": "employee_1_xyz.jpg",
  "photo_url": "/uploads/employees/employee_1_xyz.jpg"
}
```

---

### DELETE `/api/employees/<id>/photo`
Remove foto do colaborador.

**Permissões:** `admin`, `rh`, `manager` (próprio restaurante)

**Resposta (200):**
```json
{
  "message": "Foto deletada com sucesso"
}
```

---

## Restaurantes

### GET `/api/restaurants`
Lista todos os restaurantes.

**Permissões:** Login obrigatório
- `admin`, `rh`, `marketing`: Veem todos (ativos e inativos)
- Outros: Apenas o próprio restaurante

**Resposta (200):**
```json
{
  "restaurants": [
    {
      "id": 1,
      "name": "Restaurante Central",
      "address": "Rua ABC, 123",
      "phone": "+351 912 345 678",
      "email": "central@example.com",
      "capacity": 50,
      "opening_hours": "08:00 - 22:00",
      "description": "Descrição do restaurante",
      "photo_filename": "rest_1.jpg",
      "manager_id": 5,
      "manager_name": "João Silva",
      "is_active": true,
      "employees_count": 15,
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-12-18T14:30:00"
    }
  ]
}
```

---

### POST `/api/restaurants`
Cria novo restaurante.

**Permissões:** `admin`, `rh`

**Body (JSON):**
```json
{
  "name": "Novo Restaurante",
  "address": "Rua XYZ, 456",
  "phone": "+351 913 456 789",
  "email": "novo@example.com",
  "capacity": 80,
  "opening_hours": "09:00 - 23:00",
  "description": "Descrição",
  "manager_id": 3
}
```

**Resposta (201):**
```json
{
  "message": "Restaurante criado com sucesso",
  "restaurant": { ... }
}
```

**Erros:**
- `400` - Nome obrigatório
- `409` - Nome já existe
- `404` - Gerente não encontrado

---

### PUT `/api/restaurants/<id>`
Atualiza restaurante.

**Permissões:** 
- `admin`, `rh`: Todos os campos
- `manager`: Apenas do próprio restaurante (campos limitados)

**Body (JSON):** Mesmos campos do POST (todos opcionais)

**Resposta (200):**
```json
{
  "message": "Restaurante atualizado com sucesso",
  "restaurant": { ... }
}
```

---

### DELETE `/api/restaurants/<id>`
Remove restaurante (soft delete).

**Permissões:** `admin`

**Resposta (200):**
```json
{
  "message": "Restaurante removido com sucesso"
}
```

---

### GET `/api/restaurants/<id>/stats`
Retorna estatísticas do restaurante.

**Permissões:** Login obrigatório (mesmo controle de acesso dos GETs)

**Resposta (200):**
```json
{
  "restaurant": { ... },
  "stats": {
    "total_employees": 15,
    "birthdays_this_month": 3,
    "events_this_month": 8
  }
}
```

---

### POST `/api/restaurants/<id>/upload-photo`
Faz upload da foto do restaurante.

**Permissões:** `admin`, `rh`, `manager` (próprio restaurante)

**Body (multipart/form-data):**
- `file`: Imagem

**Resposta (200):**
```json
{
  "message": "Foto enviada com sucesso",
  "photo_filename": "restaurant_1.jpg",
  "photo_url": "/static/uploads/restaurants/restaurant_1.jpg"
}
```

---

## Calendário

### GET `/api/calendar/events`
Lista eventos do calendário.

**Permissões:** Login obrigatório

**Query Params:**
- `start_date` - Data inicial (ISO format)
- `end_date` - Data final (ISO format)
- `restaurant_id` - Filtrar por restaurante
- `event_type` - Tipo do evento

**Resposta (200):**
```json
{
  "events": [
    {
      "id": 1,
      "title": "Reunião de Equipe",
      "description": "Reunião mensal",
      "start_date": "2024-12-20T10:00:00",
      "end_date": "2024-12-20T12:00:00",
      "location": "Sala 1",
      "event_type": "meeting",
      "restaurant_id": 1,
      "restaurant_name": "Restaurante Central",
      "created_by": 1,
      "created_by_name": "Admin",
      "all_day": false,
      "color": "#007bff"
    }
  ]
}
```

---

### POST `/api/calendar/events`
Cria novo evento.

**Permissões:** `admin`, `rh`, `marketing`, `manager`

**Body (JSON):**
```json
{
  "title": "Novo Evento",
  "description": "Descrição",
  "start_date": "2024-12-25T14:00:00",
  "end_date": "2024-12-25T16:00:00",
  "location": "Restaurante Central",
  "event_type": "meeting",
  "restaurant_id": 1,
  "all_day": false
}
```

**Resposta (201):**
```json
{
  "message": "Evento criado com sucesso",
  "event": { ... }
}
```

---

### PUT `/api/calendar/events/<id>`
Atualiza evento.

**Permissões:** `admin`, `rh`, `marketing`, `manager` (próprio restaurante)

**Resposta (200):**
```json
{
  "message": "Evento atualizado com sucesso",
  "event": { ... }
}
```

---

### DELETE `/api/calendar/events/<id>`
Remove evento.

**Permissões:** `admin`, `rh`

**Resposta (200):**
```json
{
  "message": "Evento deletado com sucesso"
}
```

---

## Documentos

### GET `/api/documents`
Lista documentos.

**Permissões:** Login obrigatório

**Query Params:**
- `restaurant_id` - Filtrar por restaurante
- `document_type` - Tipo do documento

**Resposta (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "title": "Relatório Mensal",
      "description": "Relatório de vendas",
      "document_type": "report",
      "file_path": "/uploads/documents/relatorio_xyz.pdf",
      "restaurant_id": 1,
      "restaurant_name": "Restaurante Central",
      "created_by": 1,
      "created_by_name": "Admin",
      "created_at": "2024-12-01T10:00:00"
    }
  ]
}
```

---

### POST `/api/documents`
Cria/upload de documento.

**Permissões:** `admin`, `rh`, `manager`

**Body (multipart/form-data):**
- `title`: Título
- `description`: Descrição
- `document_type`: Tipo
- `restaurant_id`: ID do restaurante
- `file`: Arquivo (PDF/DOC/DOCX)

**Resposta (201):**
```json
{
  "message": "Documento criado com sucesso",
  "document": { ... }
}
```

---

### DELETE `/api/documents/<id>`
Remove documento.

**Permissões:** `admin`, `rh`

**Resposta (200):**
```json
{
  "message": "Documento deletado com sucesso"
}
```

---

## Dashboard

### GET `/api/dashboard/stats`
Retorna estatísticas gerais do dashboard.

**Permissões:** Login obrigatório

**Resposta (200):**
```json
{
  "total_employees": 50,
  "total_restaurants": 3,
  "active_employees": 48,
  "birthdays_this_month": 5,
  "events_today": 2,
  "recent_hires": 3
}
```

---

### GET `/api/dashboard/birthdays`
Lista aniversariantes do mês.

**Permissões:** Login obrigatório

**Resposta (200):**
```json
{
  "birthdays": [
    {
      "id": 5,
      "name": "Maria Santos",
      "birth_date": "1995-12-25",
      "days_until": 7,
      "restaurant_name": "Restaurante Central"
    }
  ]
}
```

---

## Perfil

### GET `/api/profile/me`
Retorna dados do perfil do usuário autenticado.

**Permissões:** Login obrigatório

**Resposta (200):**
```json
{
  "id": 1,
  "name": "João Silva",
  "email": "joao@example.com",
  "phone": "+351 912 345 678",
  "position": "Gerente_loja",
  "department": "Gerente_loja",
  "birth_date": "1990-05-15",
  "hire_date": "2020-01-10",
  "address": "Rua X, 123",
  "notes": "Observações",
  "restaurant_id": 1,
  "role": "manager",
  "photo_filename": "employee_1.jpg",
  "is_active": true,
  "work_years": 4,
  "days_until_birthday": 148
}
```

---

### PUT `/api/profile/me`
Atualiza perfil do usuário.

**Permissões:** Login obrigatório

**Body (JSON):**
```json
{
  "name": "João Silva",
  "phone": "+351 912 345 678",
  "address": "Novo endereço",
  "notes": "Novas observações"
}
```

**Restrições:**
- Email não pode ser alterado
- `position`, `department`: Apenas `admin` ou `rh`
- `birth_date`, `hire_date`: Apenas `admin`

**Resposta (200):**
```json
{
  "message": "Perfil atualizado com sucesso",
  "user": { ... }
}
```

---

### POST `/api/profile/me/photo`
Upload de foto de perfil.

**Permissões:** Login obrigatório

**Body (multipart/form-data):**
- `file`: Imagem

**Resposta (200):**
```json
{
  "message": "Foto atualizada com sucesso",
  "photo_filename": "employee_1_abc.jpg",
  "photo_url": "/uploads/employees/employee_1_abc.jpg"
}
```

---

### DELETE `/api/profile/me/photo`
Remove foto de perfil.

**Permissões:** Login obrigatório

**Resposta (200):**
```json
{
  "message": "Foto removida com sucesso"
}
```

---

### PUT `/api/profile/change-password`
Altera senha do usuário.

**Permissões:** Login obrigatório

**Body (JSON):**
```json
{
  "current_password": "senhaAtual123",
  "new_password": "NovaSenha456!",
  "confirm_password": "NovaSenha456!"
}
```

**Validações:**
- Senha atual correta
- Nova senha ≠ atual
- Nova senha = confirmação
- Senha forte (≥8 chars, maiúsc., minúsc., número, especial)

**Resposta (200):**
```json
{
  "message": "Senha alterada com sucesso"
}
```

---

## AI/Posts

### POST `/api/ai/posts`
Gera posts de redes sociais usando IA (ChatGPT).

**Permissões:** `admin`, `marketing`

**Body (JSON):**
```json
{
  "prompt": "Crie um post sobre aniversariantes do mês",
  "platform": "instagram",
  "tone": "profissional"
}
```

**Resposta (200):**
```json
{
  "post": "🎉 Feliz aniversário aos nossos colaboradores...",
  "hashtags": ["#Aniversario", "#Equipe", "#MacCalendar"]
}
```

---

## Notas Importantes

### Autenticação
- Todos os endpoints (exceto `/auth/login`) requerem autenticação
- Usar Session (web) ou JWT token (API)

### Rate Limiting
- Não implementado atualmente
- Considerar para produção

### Paginação
- Não implementada atualmente
- Retorna todos os registros filtrados

### CORS
- Configurado para aceitar requisições do mesmo domínio
- Ajustar para APIs externas se necessário

---

**Última atualização:** 18 de Dezembro de 2025
