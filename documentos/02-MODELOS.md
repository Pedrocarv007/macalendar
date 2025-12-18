# Modelos de Dados - MAC Calendar

## Sumário

- [Employee (Colaborador)](#employee-colaborador)
- [Restaurant (Restaurante)](#restaurant-restaurante)
- [CalendarEvent (Evento)](#calendarevent-evento)
- [Document (Documento)](#document-documento)

---

## Employee (Colaborador)

### Descrição
Modelo que representa os colaboradores da empresa, incluindo dados pessoais, profissionais e de autenticação.

### Tabela: `employees`

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | Integer | Sim (PK) | ID único do colaborador |
| `name` | String(100) | Sim | Nome completo |
| `email` | String(120) | Sim (único) | Email (usado para login) |
| `password_hash` | String(200) | Sim | Senha criptografada (bcrypt) |
| `phone` | String(20) | Não | Telefone de contato |
| `position` | String(50) | Não | Cargo (função) |
| `department` | String(50) | Não | Departamento |
| `birth_date` | Date | Não | Data de nascimento |
| `hire_date` | Date | Não | Data de contratação |
| `address` | Text | Não | Endereço completo |
| `notes` | Text | Não | Observações internas |
| `restaurant_id` | Integer | Não (FK) | ID do restaurante vinculado |
| `role` | String(20) | Sim | Papel/permissão do usuário |
| `photo_filename` | String(200) | Não | Nome do arquivo da foto |
| `is_active` | Boolean | Sim | Status ativo/inativo (padrão: True) |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data da última atualização |

### Roles Disponíveis

- `admin` - Administrador total
- `rh` - Recursos Humanos
- `marketing` - Marketing
- `manager` - Gerente de Restaurante
- `employee` - Colaborador comum
- `shift_manager` - Gerente de turno
- `sub_manager` - Sub-gerente
- `rp` - RP
- `coucher` - Coucher

### Relacionamentos

```python
# Relacionamento com Restaurant (Many-to-One)
restaurant = db.relationship('Restaurant', back_populates='employees')

# Relacionamento com CalendarEvent (One-to-Many)
events = db.relationship('CalendarEvent', back_populates='creator', cascade='all, delete-orphan')

# Relacionamento com Document (One-to-Many)
documents = db.relationship('Document', back_populates='creator', cascade='all, delete-orphan')
```

### Métodos

#### `set_password(password: str) -> None`
Define uma nova senha para o colaborador (criptografa com bcrypt).

**Parâmetros:**
- `password`: Senha em texto plano

**Exemplo:**
```python
employee = Employee(name="João", email="joao@example.com")
employee.set_password("senha123")
db.session.add(employee)
db.session.commit()
```

---

#### `check_password(password: str) -> bool`
Verifica se a senha fornecida está correta.

**Parâmetros:**
- `password`: Senha em texto plano

**Retorno:**
- `True` se senha correta, `False` caso contrário

**Exemplo:**
```python
employee = Employee.query.filter_by(email="joao@example.com").first()
if employee and employee.check_password("senha123"):
    print("Login válido")
```

---

#### `to_dict() -> dict`
Converte o objeto Employee para dicionário (serialização para JSON).

**Retorno:**
```python
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
    "restaurant_name": "Restaurante Central",
    "role": "manager",
    "photo_filename": "employee_1.jpg",
    "photo_url": "/uploads/employees/employee_1.jpg",
    "is_active": True,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-12-18T14:30:00"
}
```

---

### Queries Comuns

**Buscar por email:**
```python
employee = Employee.query.filter_by(email="joao@example.com").first()
```

**Listar colaboradores ativos de um restaurante:**
```python
employees = Employee.query.filter_by(
    restaurant_id=1,
    is_active=True
).order_by(Employee.name).all()
```

**Buscar aniversariantes do mês:**
```python
from sqlalchemy import extract
from datetime import datetime

month = datetime.now().month
birthdays = Employee.query.filter(
    extract('month', Employee.birth_date) == month
).order_by(extract('day', Employee.birth_date)).all()
```

**Buscar por role:**
```python
admins = Employee.query.filter_by(role='admin', is_active=True).all()
```

---

## Restaurant (Restaurante)

### Descrição
Modelo que representa os restaurantes da empresa.

### Tabela: `restaurants`

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | Integer | Sim (PK) | ID único do restaurante |
| `name` | String(100) | Sim (único) | Nome do restaurante |
| `address` | String(200) | Não | Endereço completo |
| `phone` | String(20) | Não | Telefone de contato |
| `email` | String(120) | Não | Email de contato |
| `capacity` | Integer | Não | Capacidade de pessoas |
| `opening_hours` | String(100) | Não | Horário de funcionamento |
| `description` | Text | Não | Descrição do restaurante |
| `photo_filename` | String(200) | Não | Nome do arquivo da foto |
| `manager_id` | Integer | Não (FK) | ID do gerente responsável |
| `is_active` | Boolean | Sim | Status ativo/inativo (padrão: True) |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data da última atualização |

### Relacionamentos

```python
# Relacionamento com Employee (One-to-Many)
employees = db.relationship('Employee', back_populates='restaurant')

# Relacionamento com CalendarEvent (One-to-Many)
events = db.relationship('CalendarEvent', back_populates='restaurant', cascade='all, delete-orphan')

# Relacionamento com Document (One-to-Many)
documents = db.relationship('Document', back_populates='restaurant')

# Relacionamento com Manager (Many-to-One)
manager = db.relationship('Employee', foreign_keys=[manager_id])
```

### Métodos

#### `to_dict(include_stats: bool = False) -> dict`
Converte o objeto Restaurant para dicionário.

**Parâmetros:**
- `include_stats`: Se True, inclui contagem de colaboradores

**Retorno:**
```python
{
    "id": 1,
    "name": "Restaurante Central",
    "address": "Rua ABC, 123",
    "phone": "+351 912 345 678",
    "email": "central@example.com",
    "capacity": 50,
    "opening_hours": "08:00 - 22:00",
    "description": "Descrição",
    "photo_filename": "rest_1.jpg",
    "manager_id": 5,
    "manager_name": "João Silva",
    "is_active": True,
    "employees_count": 15,  # se include_stats=True
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-12-18T14:30:00"
}
```

---

### Queries Comuns

**Listar restaurantes ativos:**
```python
restaurants = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.name).all()
```

**Buscar por nome:**
```python
restaurant = Restaurant.query.filter_by(name="Restaurante Central").first()
```

**Buscar restaurantes de um gerente:**
```python
restaurants = Restaurant.query.filter_by(manager_id=5).all()
```

**Buscar com contagem de colaboradores:**
```python
from sqlalchemy import func

restaurants = db.session.query(
    Restaurant,
    func.count(Employee.id).label('employees_count')
).outerjoin(Employee).group_by(Restaurant.id).all()
```

---

## CalendarEvent (Evento)

### Descrição
Modelo que representa eventos do calendário (reuniões, aniversários, etc.).

### Tabela: `calendar_events`

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | Integer | Sim (PK) | ID único do evento |
| `title` | String(200) | Sim | Título do evento |
| `description` | Text | Não | Descrição detalhada |
| `start_date` | DateTime | Sim | Data/hora de início |
| `end_date` | DateTime | Não | Data/hora de fim |
| `location` | String(200) | Não | Local do evento |
| `event_type` | String(50) | Não | Tipo de evento |
| `restaurant_id` | Integer | Não (FK) | ID do restaurante vinculado |
| `created_by` | Integer | Sim (FK) | ID do criador do evento |
| `all_day` | Boolean | Sim | Evento de dia inteiro (padrão: False) |
| `color` | String(20) | Não | Cor no calendário |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data da última atualização |

### Tipos de Eventos

- `meeting` - Reunião
- `birthday` - Aniversário
- `holiday` - Feriado
- `training` - Treinamento
- `other` - Outro

### Relacionamentos

```python
# Relacionamento com Restaurant (Many-to-One)
restaurant = db.relationship('Restaurant', back_populates='events')

# Relacionamento com Employee (criador) (Many-to-One)
creator = db.relationship('Employee', back_populates='events')
```

### Métodos

#### `to_dict() -> dict`
Converte o objeto CalendarEvent para dicionário.

**Retorno:**
```python
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
    "all_day": False,
    "color": "#007bff",
    "created_at": "2024-12-01T10:00:00",
    "updated_at": "2024-12-18T14:30:00"
}
```

---

### Queries Comuns

**Buscar eventos de um período:**
```python
from datetime import datetime

start = datetime(2024, 12, 1)
end = datetime(2024, 12, 31)

events = CalendarEvent.query.filter(
    CalendarEvent.start_date >= start,
    CalendarEvent.start_date <= end
).order_by(CalendarEvent.start_date).all()
```

**Buscar eventos de um restaurante:**
```python
events = CalendarEvent.query.filter_by(restaurant_id=1).all()
```

**Buscar eventos criados por um usuário:**
```python
events = CalendarEvent.query.filter_by(created_by=1).all()
```

**Buscar eventos de hoje:**
```python
from datetime import datetime, timedelta

today = datetime.now().date()
tomorrow = today + timedelta(days=1)

events = CalendarEvent.query.filter(
    CalendarEvent.start_date >= today,
    CalendarEvent.start_date < tomorrow
).all()
```

---

## Document (Documento)

### Descrição
Modelo que representa documentos uploadados (relatórios, contratos, etc.).

### Tabela: `documents`

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | Integer | Sim (PK) | ID único do documento |
| `title` | String(200) | Sim | Título do documento |
| `description` | Text | Não | Descrição |
| `document_type` | String(50) | Não | Tipo de documento |
| `file_path` | String(500) | Sim | Caminho do arquivo |
| `file_size` | Integer | Não | Tamanho do arquivo (bytes) |
| `restaurant_id` | Integer | Não (FK) | ID do restaurante vinculado |
| `created_by` | Integer | Sim (FK) | ID do criador |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data da última atualização |

### Tipos de Documentos

- `report` - Relatório
- `contract` - Contrato
- `invoice` - Fatura
- `manual` - Manual
- `policy` - Política/Procedimento
- `other` - Outro

### Relacionamentos

```python
# Relacionamento com Restaurant (Many-to-One)
restaurant = db.relationship('Restaurant', back_populates='documents')

# Relacionamento com Employee (criador) (Many-to-One)
creator = db.relationship('Employee', back_populates='documents')
```

### Métodos

#### `to_dict() -> dict`
Converte o objeto Document para dicionário.

**Retorno:**
```python
{
    "id": 1,
    "title": "Relatório Mensal",
    "description": "Relatório de vendas",
    "document_type": "report",
    "file_path": "/uploads/documents/relatorio_xyz.pdf",
    "file_size": 2048576,
    "restaurant_id": 1,
    "restaurant_name": "Restaurante Central",
    "created_by": 1,
    "created_by_name": "Admin",
    "created_at": "2024-12-01T10:00:00",
    "updated_at": "2024-12-18T14:30:00"
}
```

---

### Queries Comuns

**Listar documentos de um restaurante:**
```python
documents = Document.query.filter_by(restaurant_id=1).order_by(Document.created_at.desc()).all()
```

**Buscar por tipo:**
```python
reports = Document.query.filter_by(document_type='report').all()
```

**Buscar documentos criados por um usuário:**
```python
documents = Document.query.filter_by(created_by=1).all()
```

**Buscar documentos recentes (últimos 30 dias):**
```python
from datetime import datetime, timedelta

thirty_days_ago = datetime.now() - timedelta(days=30)
documents = Document.query.filter(
    Document.created_at >= thirty_days_ago
).order_by(Document.created_at.desc()).all()
```

---

## Validações Comuns

### Validação de Email (Employee)
```python
from sqlalchemy.orm import validates
import re

@validates('email')
def validate_email(self, key, email):
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise ValueError('Email inválido')
    return email.lower()
```

### Validação de Telefone (Employee, Restaurant)
```python
@validates('phone')
def validate_phone(self, key, phone):
    if phone and not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
        raise ValueError('Telefone inválido')
    return phone
```

### Validação de Datas (Employee)
```python
from datetime import datetime

@validates('birth_date', 'hire_date')
def validate_dates(self, key, date):
    if date and date > datetime.now().date():
        raise ValueError(f'{key} não pode ser no futuro')
    return date
```

---

## Migrations

### Criar nova migration:
```bash
flask db migrate -m "Descrição da mudança"
```

### Aplicar migrations:
```bash
flask db upgrade
```

### Reverter migration:
```bash
flask db downgrade
```

---

## Notas Importantes

### Soft Delete
Todos os modelos principais usam `is_active` em vez de deletar fisicamente:
```python
# Não usar:
db.session.delete(employee)

# Usar:
employee.is_active = False
db.session.commit()
```

### Timestamps Automáticos
Os campos `created_at` e `updated_at` são atualizados automaticamente:
- `created_at`: Definido na criação (`default=datetime.utcnow`)
- `updated_at`: Atualizado em cada `commit` (`onupdate=datetime.utcnow`)

### Fotos/Uploads
- Armazenadas em `app/static/uploads/{tipo}/`
- Apenas nome do arquivo no banco (`photo_filename`)
- URLs construídas dinamicamente no `to_dict()`

---

**Última atualização:** 18 de Dezembro de 2025
