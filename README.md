# MAC Calendar - Sistema de Gestão para Restaurantes

Sistema completo de gestão para restaurantes MAC com calendário integrado, gestão de colaboradores e geração de documentos.

## 🚀 Funcionalidades

### 📅 Sistema de Calendário
- Calendário tipo Google Calendar para cada restaurante
- Visualização por dia, semana e mês
- Eventos personalizáveis (reuniões, feriados, treinamentos)
- Aniversários automáticos dos colaboradores
- Controle de acesso por permissão

### 👥 Gestão de Colaboradores
- Cadastro completo de funcionários
- Upload de fotos dos colaboradores
- Controle de aniversários e datas importantes
- Histórico profissional

### 📄 Sistema de Documentos
- Templates para documentos de aniversário
- Sistema de elogios personalizados
- Geração automática de PDFs
- Biblioteca de templates

### 🔐 Controle de Acesso
- **Admin**: Acesso total ao sistema
- **RH**: Visualiza todos os restaurantes
- **Marketing**: Visualiza todos os restaurantes
- **Gerente**: Acesso apenas ao seu restaurante
- **Funcionário**: Acesso limitado ao seu restaurante

## 🛠️ Tecnologias

- **Backend**: Flask (Python)
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Autenticação**: JWT (Flask-JWT-Extended)
- **Upload**: Pillow para processamento de imagens
- **PDFs**: ReportLab
- **Migrações**: Flask-Migrate
- **Testes**: Pytest

## 📦 Instalação

### Pré-requisitos
- Python 3.8+
- pip

### 1. Clone o repositório
```bash
git clone https://github.com/Pedrocarv007/macalendar.git
cd macalendar
```

### 2. Crie ambiente virtual
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instale dependências
```bash
pip install -r requirements.txt
```

### 4. Configure variáveis de ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 5. Execute a aplicação
```bash
python run.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`

## 📊 API Endpoints

### Autenticação
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Registro (admin/RH)
- `GET /api/auth/profile` - Perfil do usuário
- `PUT /api/auth/profile` - Atualizar perfil
- `POST /api/auth/change-password` - Alterar senha

### Colaboradores
- `GET /api/employees` - Listar colaboradores
- `POST /api/employees` - Criar colaborador
- `PUT /api/employees/{id}` - Atualizar colaborador
- `POST /api/employees/{id}/photo` - Upload foto
- `GET /api/employees/birthdays-this-month` - Aniversariantes

### Calendário
- `GET /api/calendar/events` - Listar eventos
- `POST /api/calendar/events` - Criar evento
- `PUT /api/calendar/events/{id}` - Atualizar evento
- `DELETE /api/calendar/events/{id}` - Deletar evento
- `GET /api/calendar/birthdays` - Aniversários do mês

---

Desenvolvido com ❤️ para MAC Restaurantes
