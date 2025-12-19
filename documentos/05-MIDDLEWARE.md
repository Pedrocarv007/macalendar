# Middleware e Segurança - MAC Calendar

## Sumário

- [Autenticação](#autenticação)
- [Decorators de Autorização](#decorators-de-autorização)
- [Validações](#validações)
- [Segurança CSRF](#segurança-csrf)
- [Rate Limiting](#rate-limiting)
- [CORS](#cors)

---

## Autenticação

### Descrição
Sistema de autenticação híbrido que suporta Session-based (web) e JWT (API).

### Arquivo: `app/middleware/security.py`

---

### Decorator: `@api_login_required`

Protege rotas de API, aceitando tanto Session quanto JWT.

**Uso:**
```python
from app.middleware.security import api_login_required

@app.route('/api/employees')
@api_login_required
def get_employees():
    # current_user estará disponível via g.current_user
    from flask import g
    user = g.current_user
    return jsonify({'employees': [...]})
```

**Comportamento:**
1. Verifica se existe JWT no header `Authorization: Bearer <token>`
2. Se JWT válido, decodifica e carrega usuário
3. Se não, verifica se existe sessão ativa (Flask-Session)
4. Se ambos falharem, retorna `401 Unauthorized`

**Exemplo de Requisição:**

```bash
# Com JWT
curl -H "Authorization: Bearer eyJhbGc..." https://www.thecarv.com/mac/api/employees

# Com Session (browser)
# Cookie de sessão enviado automaticamente
fetch('/mac/api/employees')
```

---

### Decorator: `@login_required` (Web)

Protege rotas web (páginas HTML), requer sessão ativa.

**Uso:**
```python
from flask_login import login_required

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
```

**Comportamento:**
- Se não autenticado, redireciona para `/auth/login`
- Usa Flask-Login para gerenciar sessão

---

### Login

**Endpoint:** `POST /api/auth/login`

**Código:**
```python
from flask import request, jsonify, session
from flask_jwt_extended import create_access_token
from app.models.employee import Employee

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email e senha obrigatórios'}), 400
    
    # Buscar usuário
    employee = Employee.query.filter_by(email=email, is_active=True).first()
    
    if not employee or not employee.check_password(password):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Criar sessão
    session['user_id'] = employee.id
    session.permanent = True  # Usar PERMANENT_SESSION_LIFETIME
    
    # Criar JWT token
    access_token = create_access_token(identity=employee.id)
    
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': employee.to_dict(),
        'access_token': access_token
    }), 200
```

---

### Logout

**Endpoint:** `GET /api/auth/logout`

**Código:**
```python
from flask import session, jsonify

@app.route('/api/auth/logout')
def logout():
    session.clear()
    return jsonify({'message': 'Logout realizado com sucesso'}), 200
```

---

### Verificar Usuário Atual

**Endpoint:** `GET /api/auth/user`

**Código:**
```python
from app.middleware.security import api_login_required
from flask import g, jsonify

@app.route('/api/auth/user')
@api_login_required
def get_current_user():
    user = g.current_user
    return jsonify(user.to_dict()), 200
```

---

## Decorators de Autorização

### `@require_roles(roles)`

Requer que usuário tenha um dos roles especificados.

**Uso:**
```python
from app.middleware.security import api_login_required, require_roles

@app.route('/api/employees', methods=['POST'])
@api_login_required
@require_roles(['admin', 'rh'])
def create_employee():
    # Apenas admin e rh podem criar colaboradores
    data = request.get_json()
    # ...
    return jsonify({'message': 'Colaborador criado'}), 201
```

**Código:**
```python
from functools import wraps
from flask import g, jsonify

def require_roles(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.current_user
            if user.role not in allowed_roles:
                return jsonify({'error': 'Permissão negada'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

### `@require_own_resource(resource_type)`

Permite acesso apenas ao próprio recurso (ou admin/rh).

**Uso:**
```python
@app.route('/api/employees/<int:id>', methods=['PUT'])
@api_login_required
@require_own_resource('employee')
def update_employee(id):
    # Usuário só pode editar próprio perfil
    # Exceto admin/rh que podem editar qualquer um
    # Manager pode editar colaboradores do próprio restaurante
    data = request.get_json()
    # ...
    return jsonify({'message': 'Atualizado'}), 200
```

**Código:**
```python
def require_own_resource(resource_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.current_user
            resource_id = kwargs.get('id')
            
            # Admin e RH sempre podem
            if user.role in ['admin', 'rh']:
                return f(*args, **kwargs)
            
            # Verificar se é próprio recurso
            if resource_type == 'employee':
                if user.id != resource_id:
                    return jsonify({'error': 'Permissão negada'}), 403
            
            elif resource_type == 'restaurant':
                # Manager pode editar próprio restaurante
                restaurant = Restaurant.query.get(resource_id)
                if user.role == 'manager' and user.restaurant_id == restaurant.id:
                    return f(*args, **kwargs)
                return jsonify({'error': 'Permissão negada'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

### `@require_restaurant_access()`

Garante acesso apenas a recursos do próprio restaurante.

**Uso:**
```python
@app.route('/api/restaurants/<int:id>/employees')
@api_login_required
@require_restaurant_access()
def get_restaurant_employees(id):
    # Manager só vê colaboradores do próprio restaurante
    # Admin/RH veem de qualquer restaurante
    employees = Employee.query.filter_by(restaurant_id=id).all()
    return jsonify({'employees': [e.to_dict() for e in employees]}), 200
```

---

## Validações

### Validação de Senha

**Função:** `validate_password_strength(password)`

**Regras:**
- Mínimo 8 caracteres
- Pelo menos 1 letra maiúscula
- Pelo menos 1 letra minúscula
- Pelo menos 1 número
- Pelo menos 1 caractere especial

**Código:**
```python
import re

def validate_password_strength(password):
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
    
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter pelo menos um caractere especial"
    
    return True, ""
```

**Uso:**
```python
@app.route('/api/profile/change-password', methods=['PUT'])
@api_login_required
def change_password():
    data = request.get_json()
    new_password = data.get('new_password')
    
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Atualizar senha
    user = g.current_user
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Senha alterada'}), 200
```

---

### Validação de Email

**Função:** `validate_email(email)`

**Código:**
```python
import re

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return False, "Email inválido"
    return True, ""
```

**Uso:**
```python
@app.route('/api/employees', methods=['POST'])
@api_login_required
@require_roles(['admin', 'rh'])
def create_employee():
    data = request.get_json()
    email = data.get('email')
    
    is_valid, message = validate_email(email)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Verificar se email já existe
    existing = Employee.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    # Criar colaborador
    # ...
```

---

### Validação de Telefone

**Função:** `validate_phone(phone)`

**Código:**
```python
import re

def validate_phone(phone):
    # Aceita formatos: +351 912 345 678, 912345678, +351912345678
    pattern = r'^\+?[\d\s\-\(\)]+$'
    if not re.match(pattern, phone):
        return False, "Telefone inválido"
    
    # Remover caracteres não numéricos
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 9:
        return False, "Telefone deve ter pelo menos 9 dígitos"
    
    return True, ""
```

---

### Validação de Upload de Arquivo

**Função:** `validate_file_upload(file, allowed_extensions, max_size_mb)`

**Código:**
```python
import os

def validate_file_upload(file, allowed_extensions, max_size_mb=5):
    if not file or file.filename == '':
        return False, "Nenhum arquivo selecionado"
    
    # Verificar extensão
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed_extensions:
        return False, f"Extensão não permitida. Use: {', '.join(allowed_extensions)}"
    
    # Verificar tamanho (move cursor para o final)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset cursor
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"Arquivo muito grande. Máximo: {max_size_mb}MB"
    
    return True, ""
```

**Uso:**
```python
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/api/employees/<int:id>/upload-photo', methods=['POST'])
@api_login_required
def upload_employee_photo(id):
    if 'file' not in request.files:
        return jsonify({'error': 'Arquivo não fornecido'}), 400
    
    file = request.files['file']
    
    is_valid, message = validate_file_upload(file, ALLOWED_IMAGE_EXTENSIONS, max_size_mb=5)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Salvar arquivo
    # ...
```

---

## Segurança CSRF

### Descrição
Proteção contra Cross-Site Request Forgery usando Flask-WTF.

### Configuração

```python
# app/config/settings.py
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

# Em app/__init__.py
from app.config.settings import csrf

def create_app():
    app = Flask(__name__)
    csrf.init_app(app)
    
    # Excluir rotas da API (usar JWT)
    csrf.exempt('/api/*')
    
    return app
```

---

### Uso em Formulários HTML

```html
<form method="POST" action="/auth/login">
    {{ csrf_token() }}
    <input type="email" name="email" required>
    <input type="password" name="password" required>
    <button type="submit">Login</button>
</form>
```

---

### Uso em JavaScript

```javascript
// Obter token CSRF do meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

// Incluir em requisições
fetch('/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ email, password })
});
```

---

## Rate Limiting

### Descrição
Limitação de requisições para prevenir abuso (usando Flask-Limiter).

### Configuração

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
```

---

### Uso

```python
# Limite específico para login
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # ...
```

---

## CORS

### Descrição
Configuração de Cross-Origin Resource Sharing para aceitar requisições de outros domínios.

### Configuração

```python
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    # Permitir apenas domínios específicos
    CORS(app, resources={
        r"/api/*": {
            "origins": ["https://www.thecarv.com", "https://app.thecarv.com"],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    return app
```

---

## Headers de Segurança

### Configuração de Headers HTTP

```python
@app.after_request
def set_security_headers(response):
    # Prevenir XSS
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HSTS (produção)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net"
    
    return response
```

---

## Exemplo Completo de Rota Segura

```python
from flask import Flask, request, jsonify, g
from app.middleware.security import api_login_required, require_roles
from app.utils.helpers import validate_email, validate_password_strength, validate_file_upload
from app.models.employee import Employee
from app.extensions.database import db

@app.route('/api/employees', methods=['POST'])
@api_login_required
@require_roles(['admin', 'rh'])
def create_employee():
    """
    Cria novo colaborador com validações de segurança.
    """
    data = request.get_json()
    
    # Validar campos obrigatórios
    required_fields = ['name', 'email', 'position', 'restaurant_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} obrigatório'}), 400
    
    # Validar email
    is_valid, message = validate_email(data['email'])
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Verificar email único
    existing = Employee.query.filter_by(email=data['email']).first()
    if existing:
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    # Gerar senha temporária
    from app.utils.helpers import generate_temp_password
    temp_password = generate_temp_password()
    
    # Validar senha gerada
    is_valid, message = validate_password_strength(temp_password)
    if not is_valid:
        return jsonify({'error': 'Erro ao gerar senha'}), 500
    
    # Criar colaborador
    try:
        employee = Employee(
            name=data['name'],
            email=data['email'],
            position=data['position'],
            department=data.get('department'),
            phone=data.get('phone'),
            restaurant_id=data['restaurant_id'],
            role=data.get('role', 'employee'),
            is_active=True
        )
        employee.set_password(temp_password)
        
        db.session.add(employee)
        db.session.commit()
        
        # Enviar email de boas-vindas
        from app.utils.email import send_welcome_email
        from flask import current_app
        send_welcome_email(
            employee.email,
            employee.name,
            temp_password,
            current_app._get_current_object()
        )
        
        return jsonify({
            'message': 'Colaborador criado com sucesso',
            'employee': employee.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar colaborador'}), 500
```

---

**Última atualização:** 18 de Dezembro de 2025
